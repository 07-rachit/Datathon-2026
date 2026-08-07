import json
import logging
from typing import Dict, List, Optional
from fastapi import WebSocket
from sqlalchemy.orm import Session
from app import models

logger = logging.getLogger("crimeintel.websocket")


class ConnectionManager:
    def __init__(self):
        # Maps user_id -> List of active WebSocket connections (multi-tab support)
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected for user {user_id}. Active tabs: {len(self.active_connections[user_id])}")

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_personal_notification(self, user_id: str, data: dict):
        """Send live notification payload to all open tabs of a specific user."""
        if user_id in self.active_connections:
            dead_connections = []
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_text(json.dumps(data))
                except Exception as e:
                    logger.warning(f"Error sending WS message to user {user_id}: {e}")
                    dead_connections.append(ws)
            for ws in dead_connections:
                self.disconnect(user_id, ws)


manager = ConnectionManager()


# ── Notification Persistence & Dispatcher Helpers ─────────────────────────────

async def create_and_dispatch_notification(
    db: Session,
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    related_case_id: Optional[str] = None,
) -> models.Notification:
    """Create a persistent notification row and push live via WebSocket if user is connected."""
    notif = models.Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        related_case_id=related_case_id,
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    payload = {
        "id": notif.id,
        "user_id": notif.user_id,
        "type": notif.type,
        "title": notif.title,
        "message": notif.message,
        "related_case_id": notif.related_case_id,
        "is_read": notif.is_read,
        "created_at": notif.created_at.isoformat(),
    }

    await manager.send_personal_notification(user_id, payload)
    return notif


async def broadcast_notification_to_roles(
    db: Session,
    roles: List[models.RoleEnum],
    notification_type: str,
    title: str,
    message: str,
    related_case_id: Optional[str] = None,
    exclude_user_id: Optional[str] = None,
):
    """Persist notification for all users in target roles and broadcast live."""
    users = db.query(models.User).filter(
        models.User.is_active == True,
        models.User.role.in_(roles)
    ).all()

    notif_map = {}
    for user in users:
        if exclude_user_id and user.id == exclude_user_id:
            continue

        notif = models.Notification(
            user_id=user.id,
            type=notification_type,
            title=title,
            message=message,
            related_case_id=related_case_id,
            is_read=False,
        )
        db.add(notif)
        notif_map[user.id] = notif

    db.commit()

    for user_id, notif in notif_map.items():
        db.refresh(notif)
        payload = {
            "id": notif.id,
            "user_id": notif.user_id,
            "type": notif.type,
            "title": notif.title,
            "message": notif.message,
            "related_case_id": notif.related_case_id,
            "is_read": notif.is_read,
            "created_at": notif.created_at.isoformat(),
        }
        await manager.send_personal_notification(user_id, payload)
