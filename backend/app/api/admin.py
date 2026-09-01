from __future__ import annotations

import time
import threading

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.providers import get_provider
from ..config import get_settings
from ..database import get_db
from ..dependencies import require_admin
from ..models import AdminAuditLog, ResourceSyncJob, User
from ..resource_sync import PACKAGES, package_status, resource_counts, start_worker
from ..runtime_settings import masked_settings, update_runtime_settings
from ..schemas import AISettingsUpdate, ResourceSyncRequest, TutorDecision

router = APIRouter(prefix="/admin", tags=["admin"])
_schedule_lock = threading.Lock()


@router.get("/settings/ai")
def get_ai_settings(_: User = Depends(require_admin)):
    return masked_settings()


@router.put("/settings/ai")
def put_ai_settings(payload: AISettingsUpdate, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not payload.base_url.startswith("https://") or not payload.tts_url.startswith("https://"):
        raise HTTPException(status_code=422, detail="Provider URLs must use HTTPS")
    current = get_settings()
    if payload.provider == "dashscope" and (payload.clear_api_key or not (payload.api_key or current.dashscope_api_key)):
        raise HTTPException(status_code=422, detail="DashScope API Key is required")
    values = payload.model_dump(exclude={"api_key", "clear_api_key"})
    try:
        changed = update_runtime_settings(values, payload.api_key, payload.clear_api_key)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Unable to save runtime AI settings") from exc
    db.add(AdminAuditLog(user_id=user.id, action="ai_settings_updated", changed_fields=changed))
    db.commit()
    return masked_settings()


@router.post("/settings/ai/test")
async def test_ai_settings(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    results = {}
    started = time.perf_counter()
    audio = None
    try:
        provider = get_provider()
    except Exception:
        results = {
            "chat": {"ok": False, "message": "AI provider is not configured"},
            "tts": {"ok": False, "message": "AI provider is not configured"},
            "asr": {"ok": False, "message": "AI provider is not configured"},
            "latency_ms": round((time.perf_counter() - started) * 1000),
        }
        db.add(AdminAuditLog(user_id=user.id, action="ai_settings_tested", changed_fields=[]))
        db.commit()
        return results
    try:
        await provider.complete([{"role": "user", "content": "Return a short friendly English greeting as valid JSON."}], "light", TutorDecision.model_json_schema())
        results["chat"] = {"ok": True}
    except Exception:
        results["chat"] = {"ok": False, "message": "Chat model test failed"}
    try:
        audio = await provider.synthesize("Hello!", "", "wav")
        results["tts"] = {"ok": bool(audio)}
    except Exception:
        results["tts"] = {"ok": False, "message": "TTS model test failed"}
    if audio:
        try:
            transcript = await provider.transcribe(audio, "audio/wav", "en")
            results["asr"] = {"ok": bool(transcript)}
        except Exception:
            results["asr"] = {"ok": False, "message": "ASR model test failed"}
    else:
        results["asr"] = {"ok": False, "message": "ASR skipped because TTS failed"}
    results["latency_ms"] = round((time.perf_counter() - started) * 1000)
    db.add(AdminAuditLog(user_id=user.id, action="ai_settings_tested", changed_fields=[]))
    db.commit()
    return results


def job_out(job: ResourceSyncJob) -> dict:
    return {"id": job.id, "status": job.status, "stage": job.stage, "current_package": job.current_package, "downloaded_bytes": job.downloaded_bytes, "total_bytes": job.total_bytes, "packages": job.packages_json, "result": job.result_json, "error": job.error, "cancel_requested": job.cancel_requested, "created_at": job.created_at, "started_at": job.started_at, "finished_at": job.finished_at}


@router.get("/resources")
def resources(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    latest = db.scalar(select(ResourceSyncJob).order_by(ResourceSyncJob.created_at.desc()).limit(1))
    return {"release": "v1.1.0-assets", "packages": package_status(), "counts": resource_counts(db), "latest_job": job_out(latest) if latest else None}


@router.post("/resources/sync", status_code=202)
def sync_resources(payload: ResourceSyncRequest, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not payload.acknowledge_copyright:
        raise HTTPException(status_code=422, detail="Copyright acknowledgement is required")
    packages = list(dict.fromkeys(payload.packages))
    if not packages:
        raise HTTPException(status_code=422, detail="Select at least one package")
    with _schedule_lock:
        active = db.scalar(select(ResourceSyncJob).where(ResourceSyncJob.status.in_(["queued", "running"])))
        if active:
            raise HTTPException(status_code=409, detail="A resource sync job is already active")
        job = ResourceSyncJob(requested_by_id=user.id, status="queued", stage="queued", downloaded_bytes=0, total_bytes=sum(PACKAGES[key]["size"] for key in packages), packages_json=packages, result_json={}, error="", cancel_requested=False)
        db.add(job); db.add(AdminAuditLog(user_id=user.id, action="resource_sync_started", changed_fields=packages)); db.commit()
    start_worker(job.id)
    return job_out(job)


@router.get("/resources/jobs/{job_id}")
def resource_job(job_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    job = db.get(ResourceSyncJob, job_id)
    if not job: raise HTTPException(status_code=404, detail="Resource job not found")
    return job_out(job)


@router.post("/resources/jobs/{job_id}/cancel")
def cancel_resource_job(job_id: str, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    job = db.get(ResourceSyncJob, job_id)
    if not job: raise HTTPException(status_code=404, detail="Resource job not found")
    if job.status not in {"queued", "running"}: raise HTTPException(status_code=409, detail="Resource job is not active")
    job.cancel_requested = True; db.add(AdminAuditLog(user_id=user.id, action="resource_sync_cancel_requested", changed_fields=[])); db.commit()
    return job_out(job)


@router.post("/resources/jobs/{job_id}/retry", status_code=202)
def retry_resource_job(job_id: str, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    source = db.get(ResourceSyncJob, job_id)
    if not source: raise HTTPException(status_code=404, detail="Resource job not found")
    if source.status not in {"failed", "canceled", "interrupted"}: raise HTTPException(status_code=409, detail="Only stopped jobs can be retried")
    with _schedule_lock:
        active = db.scalar(select(ResourceSyncJob).where(ResourceSyncJob.status.in_(["queued", "running"])))
        if active: raise HTTPException(status_code=409, detail="A resource sync job is already active")
        job = ResourceSyncJob(requested_by_id=user.id, status="queued", stage="queued", downloaded_bytes=0, total_bytes=source.total_bytes, packages_json=source.packages_json, result_json={}, error="", cancel_requested=False)
        db.add(job); db.add(AdminAuditLog(user_id=user.id, action="resource_sync_retried", changed_fields=[])); db.commit()
    start_worker(job.id)
    return job_out(job)
