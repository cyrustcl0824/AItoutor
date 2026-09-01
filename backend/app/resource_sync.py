from __future__ import annotations

import hashlib
import shutil
import tarfile
import threading
import zipfile
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy import select

from .config import get_settings
from .database import SessionLocal
from .models import AudioAsset, Exercise, Passage, PassageSentence, ResourceSyncJob, Story, StorySentence, TextbookEdition, TextbookPage

RELEASE = "v1.1.0-assets"
BASE_URL = f"https://github.com/wuwangzhang1216/ChinaTextbookStudyFree/releases/download/{RELEASE}"
PACKAGES = {
    "audio": {"file": "audio.tar.gz", "size": 912220706, "sha256": "bf940a734108cc3a15280d548ee2d43a2eb9ce4bd623da8afd6334d126ce7ead"},
    "data_source": {"file": "data-source.zip", "size": 829942, "sha256": "fb04e05d856bf7235e60779c7b0dac42e021df8e98896b7d277e47e0ab831eb5"},
    "data": {"file": "data.zip", "size": 4471790, "sha256": "a63a940099c1d2f2b2b8270b99e3360ab77d066fc25a7f8c90a99d526f163213"},
    "story_images": {"file": "story-images.zip", "size": 385463735, "sha256": "54a2838047d77d1615a12a40423846cdabbb32c5c0a2ef157d6459830cdd9d4b"},
    "textbook_pages": {"file": "textbook-pages.zip", "size": 200693837, "sha256": "77746840085e767d45975e29ab009bf03b8f89d0bdcac355a2a07527fe096a5f"},
}
_worker_lock = threading.Lock()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def _verified_marker(path: Path) -> Path:
    return path.with_name(path.name + ".verified")


def _is_verified(path: Path, item: dict) -> bool:
    if not path.is_file() or path.stat().st_size != item["size"] or not _verified_marker(path).is_file():
        return False
    expected = f"{item['sha256']} {item['size']} {path.stat().st_mtime_ns}"
    return _verified_marker(path).read_text(encoding="ascii").strip() == expected


def _mark_verified(path: Path, item: dict) -> None:
    _verified_marker(path).write_text(f"{item['sha256']} {item['size']} {path.stat().st_mtime_ns}", encoding="ascii")


def package_status() -> list[dict]:
    root = get_settings().resource_root / RELEASE / "packages"
    result = []
    for key, item in PACKAGES.items():
        path = root / item["file"]
        result.append({"id": key, "filename": item["file"], "size": item["size"], "downloaded": _is_verified(path, item)})
    return result


def resource_counts(db) -> dict:
    from sqlalchemy import func
    return {
        "editions": db.scalar(select(func.count(TextbookEdition.id))) or 0,
        "pages": db.scalar(select(func.count(TextbookPage.id))) or 0,
        "stories": db.scalar(select(func.count(Story.id))) or 0,
        "story_sentences": db.scalar(select(func.count(StorySentence.id))) or 0,
        "passages": db.scalar(select(func.count(Passage.id))) or 0,
        "passage_sentences": db.scalar(select(func.count(PassageSentence.id))) or 0,
        "exercises": db.scalar(select(func.count(Exercise.id))) or 0,
        "audio_assets": db.scalar(select(func.count(AudioAsset.id))) or 0,
        "story_images": sum(1 for _ in (get_settings().resource_root / RELEASE / "extracted" / "story_images").rglob("*.jpg")) if (get_settings().resource_root / RELEASE / "extracted" / "story_images").is_dir() else 0,
        "audio_files": sum(1 for _ in (get_settings().resource_root / RELEASE / "extracted" / "audio").rglob("*.opus")) if (get_settings().resource_root / RELEASE / "extracted" / "audio").is_dir() else 0,
    }


def _job_canceled(db, job: ResourceSyncJob) -> bool:
    db.refresh(job)
    return job.cancel_requested


def _safe_destination(root: Path, name: str) -> Path:
    target = (root / name).resolve()
    if root.resolve() != target and root.resolve() not in target.parents:
        raise ValueError("Archive contains an unsafe path")
    return target


def _extract(archive: Path, destination: Path, db, job: ResourceSyncJob) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                if _job_canceled(db, job): raise InterruptedError()
                _safe_destination(destination, member.filename)
                bundle.extract(member, destination)
    else:
        with tarfile.open(archive, "r:gz") as bundle:
            for member in bundle.getmembers():
                if _job_canceled(db, job): raise InterruptedError()
                _safe_destination(destination, member.name)
                bundle.extract(member, destination, filter="data")


def _download(key: str, target: Path, db, job: ResourceSyncJob, completed_bytes: int) -> None:
    item = PACKAGES[key]
    if _is_verified(target, item):
        job.downloaded_bytes = completed_bytes + item["size"]; db.commit(); return
    if target.is_file() and target.stat().st_size == item["size"] and _sha256(target) == item["sha256"]:
        _mark_verified(target, item)
        job.downloaded_bytes = completed_bytes + item["size"]; db.commit(); return
    part = target.with_suffix(target.suffix + ".part")
    if part.is_file() and part.stat().st_size >= item["size"]:
        if part.stat().st_size == item["size"] and _sha256(part) == item["sha256"]:
            part.replace(target); _mark_verified(target, item)
            job.downloaded_bytes = completed_bytes + item["size"]; db.commit(); return
        part.unlink()
    offset = part.stat().st_size if part.is_file() else 0
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    with httpx.stream("GET", f"{BASE_URL}/{item['file']}", headers=headers, follow_redirects=True, timeout=60) as response:
        response.raise_for_status()
        if offset and response.status_code != 206:
            offset = 0
        mode = "ab" if offset else "wb"
        with part.open(mode) as output:
            for chunk in response.iter_bytes(1024 * 1024):
                if _job_canceled(db, job): raise InterruptedError()
                output.write(chunk); offset += len(chunk)
                job.downloaded_bytes = completed_bytes + offset; db.commit()
    if offset != item["size"] or _sha256(part) != item["sha256"]:
        raise ValueError(f"Checksum or size mismatch for {item['file']}")
    part.replace(target)
    _mark_verified(target, item)


def _find_source_root(root: Path) -> Path:
    if (root / "passages").is_dir() or (root / "stories").is_dir(): return root
    for child in root.rglob("passages"):
        if child.is_dir(): return child.parent
    return root


def run_job(job_id: str) -> None:
    with _worker_lock, SessionLocal() as db:
        job = db.get(ResourceSyncJob, job_id)
        if not job: return
        settings = get_settings(); release_root = settings.resource_root / RELEASE
        package_root, extracted_root = release_root / "packages", release_root / "extracted"
        package_root.mkdir(parents=True, exist_ok=True); extracted_root.mkdir(parents=True, exist_ok=True)
        job.status = "running"; job.stage = "downloading"; job.started_at = datetime.utcnow(); job.error = ""
        job.total_bytes = sum(PACKAGES[key]["size"] for key in job.packages_json); db.commit()
        try:
            required = sum(PACKAGES[key]["size"] for key in job.packages_json if not _is_verified(package_root / PACKAGES[key]["file"], PACKAGES[key])) * 2
            if shutil.disk_usage(settings.resource_root).free < required:
                raise OSError(f"Insufficient disk space; at least {required} bytes free required")
            completed = 0
            for key in job.packages_json:
                if _job_canceled(db, job): raise InterruptedError()
                job.current_package = key; db.commit()
                _download(key, package_root / PACKAGES[key]["file"], db, job, completed)
                completed += PACKAGES[key]["size"]
            job.stage = "extracting"; db.commit()
            for key in job.packages_json:
                if _job_canceled(db, job): raise InterruptedError()
                job.current_package = key; db.commit()
                _extract(package_root / PACKAGES[key]["file"], extracted_root / key, db, job)
            job.stage = "importing"; db.commit()
            from curriculum.import_textbooks import import_pages, import_passages, import_release_data, import_stories
            from .models import Subject
            subjects = {item.code: item for item in db.scalars(select(Subject)).all()}
            stats = {"courses_created": 0, "units_created": 0, "knowledge_points_created": 0, "exercises_created": 0, "exercises_updated": 0, "unmatched_quizzes": 0, "pages_created": 0, "pages_skipped": 0, "unclassified_pages": 0, "damaged_pages": [], "sentences_created": 0, "unmatched_passages": 0, "damaged_passages": [], "stories_created": 0, "story_sentences_created": 0, "damaged_stories": []}
            if (extracted_root / "textbook_pages").is_dir() and ("textbook_pages" in job.packages_json or "data" in job.packages_json):
                import_pages(db, extracted_root / "textbook_pages", settings.textbook_root, subjects, stats)
            if (extracted_root / "data").is_dir() and any(key in job.packages_json for key in ("data", "data_source", "audio", "textbook_pages", "story_images")):
                import_release_data(db, extracted_root / "data", subjects, stats, extracted_root / "audio" if (extracted_root / "audio").is_dir() else None, extracted_root / "story_images" if (extracted_root / "story_images").is_dir() else None)
            elif "data_source" in job.packages_json:
                source = _find_source_root(extracted_root / "data_source")
                import_passages(db, source, stats); import_stories(db, source, subjects["english"], stats)
            db.commit()
            job.result_json = stats
            job.status = "completed"; job.stage = "completed"; job.finished_at = datetime.utcnow(); job.current_package = None; db.commit()
        except InterruptedError:
            if job.current_package:
                item = PACKAGES[job.current_package]
                part = package_root / f"{item['file']}.part"
                if part.is_file(): part.unlink()
            job.status = "canceled"; job.stage = "canceled"; job.finished_at = datetime.utcnow(); db.commit()
        except Exception as exc:
            db.rollback(); job = db.get(ResourceSyncJob, job_id)
            job.status = "failed"; job.stage = "failed"; job.error = str(exc)[:500]; job.finished_at = datetime.utcnow(); db.commit()


def start_worker(job_id: str) -> None:
    threading.Thread(target=run_job, args=(job_id,), daemon=True, name=f"resource-sync-{job_id[:8]}").start()
