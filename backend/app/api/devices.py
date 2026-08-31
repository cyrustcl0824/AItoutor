from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import Device, User
from ..schemas import DeviceHeartbeat

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("", status_code=201)
def register_device(name: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    device = Device(family_id=user.family_id, name=name)
    db.add(device)
    db.commit()
    return {"id": device.id, "name": device.name, "state": device.state}


@router.get("/{device_id}/bootstrap")
def bootstrap(device_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if not device or device.family_id != user.family_id:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"device_id": device.id, "state": device.state, "capabilities": ["microphone", "speaker", "touch"], "audio": {"upload_url": "/api/v1/audio/transcribe", "format": "wav"}}


@router.post("/heartbeat")
def heartbeat(payload: DeviceHeartbeat, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    device = db.get(Device, payload.device_id)
    if not device or device.family_id != user.family_id:
        raise HTTPException(status_code=404, detail="Device not found")
    device.state = payload.state
    device.metadata_json = payload.metadata
    device.last_seen_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "server_time": datetime.utcnow()}


@router.post("/{device_id}/events", status_code=202)
def event(device_id: str, event_type: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if not device or device.family_id != user.family_id:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"accepted": True, "event_type": event_type}

