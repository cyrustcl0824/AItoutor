"""Idempotent curriculum and textbook-page importer.

Expected inputs are an upstream checkout (for output/*/outlines) and the extracted
v1.1.0-assets archives. Every source file is retained outside Git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from PIL import Image
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import (Course, KnowledgePoint, Lesson, Passage, PassageSentence,
                        Subject, TextbookEdition, TextbookPage, Unit)  # noqa: E402

PINNED_COMMIT = "7824f0b4cd2ff8cac24ecca80864019b37ed7ba6"


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or hashlib.sha1(value.encode()).hexdigest()[:12]


def infer_grade_semester(name: str) -> tuple[int, str]:
    chinese = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}
    match = re.search(r"([一二三四五六])年级", name)
    return (chinese.get(match.group(1), 0) if match else 0, "上册" if "上册" in name else "下册" if "下册" in name else "未知")


def upsert_outline(db, subject: Subject, path: Path, stats: dict) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    grade, semester = infer_grade_semester(path.stem)
    external = f"upstream:english:{slug(path.stem)}"
    course = db.scalar(select(Course).where(Course.external_id == external))
    if not course:
        course = Course(subject_id=subject.id, external_id=external, name=payload.get("textbook", path.stem), grade=grade, semester=semester, metadata_json={"source": path.name})
        db.add(course)
        db.flush()
        stats["courses_created"] += 1
    for unit_data in payload.get("units", []):
        unit_external = f"{external}:unit:{unit_data['unit_number']}"
        unit = db.scalar(select(Unit).where(Unit.external_id == unit_external))
        if not unit:
            unit = Unit(course_id=course.id, external_id=unit_external, title=unit_data["title"], position=unit_data["unit_number"])
            db.add(unit)
            db.flush()
            db.add(Lesson(unit_id=unit.id, external_id=f"{unit_external}:lesson:1", title=unit_data["title"], position=1))
            stats["units_created"] += 1
        for point in unit_data.get("knowledge_points", []):
            code = f"pep_{grade}_{semester}_{unit_data['unit_number']}_{slug(point['name'])}"
            if not db.scalar(select(KnowledgePoint).where(KnowledgePoint.code == code)):
                db.add(KnowledgePoint(subject_id=subject.id, code=code, name=point["name"], difficulty=point.get("difficulty", 1), metadata_json={"description": point.get("description", ""), "question_types": point.get("question_types", [])}))
                stats["knowledge_points_created"] += 1


def import_pages(db, assets: Path, output_root: Path, subjects: dict[str, Subject], stats: dict) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    for source in sorted(assets.rglob("*.jpg")):
        relative = source.relative_to(assets)
        context = "/".join(relative.parts).lower()
        code = "english" if "english" in context or "英语" in context else "chinese" if "chinese" in context or "语文" in context else "math" if "math" in context or "数学" in context else None
        if not code:
            stats["unclassified_pages"] += 1
            continue
        edition_name = relative.parent.name
        grade, semester = infer_grade_semester(edition_name)
        edition_external = f"upstream:{code}:{slug(edition_name)}"
        edition = db.scalar(select(TextbookEdition).where(TextbookEdition.external_id == edition_external))
        if not edition:
            edition = TextbookEdition(subject_id=subjects[code].id, external_id=edition_external, title=edition_name, publisher="人民教育出版社" if code == "english" else "", grade=grade, semester=semester, source_commit=PINNED_COMMIT)
            db.add(edition)
            db.flush()
        match = re.search(r"(\d+)", source.stem)
        position = int(match.group(1)) if match else len(list(db.scalars(select(TextbookPage).where(TextbookPage.edition_id == edition.id)))) + 1
        if db.scalar(select(TextbookPage).where(TextbookPage.edition_id == edition.id, TextbookPage.position == position)):
            stats["pages_skipped"] += 1
            continue
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target_dir = output_root / edition_external.replace(":", "_")
        target_dir.mkdir(parents=True, exist_ok=True)
        web = target_dir / f"{position:04d}.webp"
        thumb = target_dir / f"{position:04d}.thumb.webp"
        try:
            with Image.open(source) as image:
                width, height = image.size
                image.save(web, "WEBP", quality=84, method=6)
                copy = image.copy()
                copy.thumbnail((360, 480))
                copy.save(thumb, "WEBP", quality=76, method=6)
        except Exception as exc:
            stats["damaged_pages"].append({"path": str(relative), "error": str(exc)})
            continue
        db.add(TextbookPage(edition_id=edition.id, position=position, printed_page=str(position), original_path=str(source.resolve()), web_path=str(web.resolve()), thumbnail_path=str(thumb.resolve()), sha256=digest, width=width, height=height))
        stats["pages_created"] += 1


def import_passages(db, source_root: Path, stats: dict) -> None:
    passages_root = source_root / "passages"
    if not passages_root.is_dir():
        return
    for path in passages_root.rglob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            stats["damaged_passages"].append({"path": str(path), "error": str(exc)})
            continue
        records = payload if isinstance(payload, list) else payload.get("passages") or payload.get("texts") or [payload]
        grade, semester = infer_grade_semester("/".join(path.parts))
        course = db.scalar(select(Course).where(Course.grade == grade, Course.semester == semester))
        if not course:
            stats["unmatched_passages"] += len(records)
            continue
        for index, record in enumerate(records):
            unit_number = int(record.get("unit_number") or record.get("unit") or 1)
            unit = db.scalar(select(Unit).where(Unit.course_id == course.id, Unit.position == unit_number))
            lesson = db.scalar(select(Lesson).where(Lesson.unit_id == unit.id).order_by(Lesson.position)) if unit else None
            if not lesson:
                stats["unmatched_passages"] += 1
                continue
            external = f"passage:{slug(str(path.relative_to(passages_root)))}:{index}"
            passage = db.scalar(select(Passage).where(Passage.external_id == external))
            if not passage:
                passage = Passage(lesson_id=lesson.id, external_id=external, title=record.get("title") or lesson.title)
                db.add(passage)
                db.flush()
            lines = record.get("sentences") or record.get("lines") or record.get("content") or []
            if isinstance(lines, str):
                lines = [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", lines) if part.strip()]
            for position, line in enumerate(lines):
                text_value = line.get("text", "") if isinstance(line, dict) else str(line)
                if text_value and not db.scalar(select(PassageSentence).where(PassageSentence.passage_id == passage.id, PassageSentence.position == position)):
                    db.add(PassageSentence(passage_id=passage.id, position=position, text=text_value, duration_ms=line.get("duration_ms") if isinstance(line, dict) else None))
                    stats["sentences_created"] += 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, help="ChinaTextbookStudyFree checkout")
    parser.add_argument("--assets", type=Path, required=True, help="Extracted textbook-pages directory")
    parser.add_argument("--source-data", type=Path, help="Extracted data-source directory containing passages/")
    parser.add_argument("--output", type=Path, default=ROOT / "backend" / "data" / "textbook-pages")
    parser.add_argument("--report", type=Path, default=ROOT / "curriculum" / "import-report.json")
    args = parser.parse_args()
    stats = {"pinned_commit": PINNED_COMMIT, "courses_created": 0, "units_created": 0, "knowledge_points_created": 0, "pages_created": 0, "pages_skipped": 0, "unclassified_pages": 0, "damaged_pages": [], "sentences_created": 0, "unmatched_passages": 0, "damaged_passages": []}
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        subjects = {s.code: s for s in db.scalars(select(Subject)).all()}
        for code, name, enabled in [("english", "英语", True), ("chinese", "语文", False), ("math", "数学", False)]:
            if code not in subjects:
                item = Subject(code=code, name=name, enabled=enabled)
                db.add(item)
                db.flush()
                subjects[code] = item
        if args.upstream:
            for path in sorted((args.upstream / "output" / "english" / "outlines").glob("*.json")):
                upsert_outline(db, subjects["english"], path, stats)
        import_pages(db, args.assets, args.output, subjects, stats)
        if args.source_data:
            import_passages(db, args.source_data, stats)
        db.commit()
    args.report.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
