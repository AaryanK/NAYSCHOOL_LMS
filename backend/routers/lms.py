import base64
import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.deps import get_current_user
from backend.lms.blackboard_client import BlackboardAPIError, BlackboardClient, normalize_blackboard_origin
from backend.lms.connector_registry import get_lms_connector
from backend.models import (
    Assignment,
    Course,
    ExternalCourseMap,
    LMSConnection,
    LMSOAuthState,
    LMSSyncLog,
    User,
)
from backend.services.token_service import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lms", tags=["lms"])


class ProviderInfo(BaseModel):
    name: str
    enabled: bool
    configured: bool


class ProvidersResponse(BaseModel):
    providers: List[ProviderInfo]


class LMSConnectionResponse(BaseModel):
    id: int
    provider: str
    school_domain: Optional[str] = None
    base_url: Optional[str] = None
    external_user_id: Optional[str] = None
    status: str
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ConnectRequest(BaseModel):
    school_domain: str
    return_path: str = "/lms"


class SyncRequest(BaseModel):
    sync_courses: bool = True
    sync_assignments: bool = True
    sync_content: bool = False
    sync_announcements: bool = True
    sync_grades: bool = False


class LMSSyncLogResponse(BaseModel):
    id: int
    connection_id: int
    provider: str
    sync_type: str
    status: str
    message: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    raw_summary_json: Optional[str] = None


def _state_hash(state: str) -> str:
    return hashlib.sha256(state.encode("ascii")).hexdigest()


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _lms_redirect(result: str, connection_id: Optional[int] = None, reason: Optional[str] = None):
    params = {"oauth": result}
    if connection_id is not None:
        params["connection_id"] = str(connection_id)
    if reason:
        params["reason"] = reason
    return RedirectResponse(url=f"/lms?{urlencode(params)}", status_code=303)


@router.get("/providers", response_model=ProvidersResponse)
def get_lms_providers(current_user: User = Depends(get_current_user)):
    return ProvidersResponse(providers=[
        ProviderInfo(
            name="blackboard",
            enabled=settings.BLACKBOARD_ENABLED,
            configured=bool(settings.BLACKBOARD_CLIENT_ID and settings.BLACKBOARD_CLIENT_SECRET),
        ),
        ProviderInfo(
            name="canvas",
            enabled=settings.CANVAS_ENABLED,
            configured=bool(settings.CANVAS_BASE_URL and settings.CANVAS_CLIENT_ID and settings.CANVAS_CLIENT_SECRET),
        ),
    ])


@router.get("/connections", response_model=List[LMSConnectionResponse])
def get_lms_connections(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(LMSConnection).filter(LMSConnection.user_id == current_user.id).all()


@router.post("/{provider}/connect")
async def connect_lms_provider(
    provider: str,
    request: ConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        connector = get_lms_connector(provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if provider != "blackboard":
        raise HTTPException(status_code=501, detail="This provider's OAuth flow is not implemented yet.")
    if not settings.BLACKBOARD_ENABLED or not settings.BLACKBOARD_CLIENT_ID or not settings.BLACKBOARD_CLIENT_SECRET:
        return {
            "status": "not_configured",
            "message": "Blackboard OAuth is not fully configured on this server.",
            "next_steps": [
                "Set BLACKBOARD_ENABLED=true.",
                "Set BLACKBOARD_CLIENT_ID to the Developer Portal OAuth Key, not the Application ID.",
                "Set BLACKBOARD_CLIENT_SECRET and BLACKBOARD_REDIRECT_URI.",
            ],
        }
    try:
        origin = normalize_blackboard_origin(request.school_domain)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return_path = request.return_path if request.return_path.startswith("/") and not request.return_path.startswith("//") else "/lms"

    connection = db.query(LMSConnection).filter(
        LMSConnection.user_id == current_user.id,
        LMSConnection.provider == provider,
        LMSConnection.base_url == origin,
    ).first()
    if not connection:
        connection = LMSConnection(
            user_id=current_user.id,
            provider=provider,
            school_domain=origin.split("://", 1)[1],
            base_url=origin,
            status="authorization_pending",
        )
        db.add(connection)
        db.flush()
    else:
        connection.status = "authorization_pending"
        connection.updated_at = datetime.utcnow()

    state = secrets.token_urlsafe(48)
    verifier = secrets.token_urlsafe(64)
    transaction = LMSOAuthState(
        state_hash=_state_hash(state),
        user_id=current_user.id,
        provider=provider,
        lms_connection_id=connection.id,
        code_verifier_encrypted=encrypt_token(verifier),
        return_path=return_path,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.BLACKBOARD_OAUTH_STATE_TTL_MINUTES),
    )
    db.add(transaction)
    db.commit()
    authorization_url = await connector.build_authorization_url(origin, state, _pkce_challenge(verifier))
    return {"status": "configured", "authorization_url": authorization_url, "connection_id": connection.id}


@router.get("/{provider}/oauth/callback")
async def lms_oauth_callback(
    provider: str,
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    error_description: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    if error:
        logger.warning("Blackboard OAuth returned an authorization error: %s", error)
        return _lms_redirect("error", reason="authorization_denied")
    if not state or not code:
        return _lms_redirect("error", reason="missing_callback_parameters")
    transaction = db.query(LMSOAuthState).filter(LMSOAuthState.state_hash == _state_hash(state)).first()
    if not transaction:
        return _lms_redirect("error", reason="invalid_state")
    if transaction.provider != provider:
        return _lms_redirect("error", reason="provider_mismatch")
    if transaction.consumed_at is not None:
        return _lms_redirect("error", reason="state_already_used")
    if transaction.expires_at <= datetime.utcnow():
        return _lms_redirect("error", reason="state_expired")
    connection = db.query(LMSConnection).filter(
        LMSConnection.id == transaction.lms_connection_id,
        LMSConnection.user_id == transaction.user_id,
        LMSConnection.provider == provider,
    ).first()
    if not connection:
        return _lms_redirect("error", reason="connection_not_found")

    try:
        verifier = decrypt_token(transaction.code_verifier_encrypted)
        if not verifier:
            raise BlackboardAPIError("OAuth transaction could not be decrypted.", 400)
        connector = get_lms_connector(provider)
        token_data = await connector.exchange_code_for_token(connection.base_url, code, verifier)
        expires_in = max(0, int(token_data.get("expires_in", 3600)))
        connection.access_token_encrypted = encrypt_token(token_data["access_token"])
        if token_data.get("refresh_token"):
            connection.refresh_token_encrypted = encrypt_token(token_data["refresh_token"])
        connection.external_user_id = str(token_data.get("user_id") or token_data.get("user") or "") or None
        connection.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        connection.scopes = token_data.get("scope") or settings.BLACKBOARD_SCOPES
        connection.status = "connected"
        connection.updated_at = datetime.utcnow()
        transaction.consumed_at = datetime.utcnow()
        db.commit()
        return _lms_redirect("success", connection.id)
    except (BlackboardAPIError, ValueError, TypeError, KeyError):
        db.rollback()
        logger.warning("Blackboard OAuth callback failed for connection %s", connection.id)
        return _lms_redirect("error", connection.id, "token_exchange_failed")


@router.get("/{connection_id}/probe")
async def probe_lms_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connection = db.query(LMSConnection).filter(
        LMSConnection.id == connection_id,
        LMSConnection.user_id == current_user.id,
    ).first()
    if not connection:
        raise HTTPException(status_code=404, detail="LMS connection not found.")
    if connection.provider != "blackboard":
        raise HTTPException(status_code=400, detail="Connection probe is not supported for this provider.")
    try:
        return await BlackboardClient(connection, db).probe()
    except BlackboardAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{connection_id}/sync")
async def sync_lms_connection(
    connection_id: int,
    request: SyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connection = db.query(LMSConnection).filter(
        LMSConnection.id == connection_id, LMSConnection.user_id == current_user.id
    ).first()
    if not connection:
        raise HTTPException(status_code=404, detail="LMS connection not found.")
    sync_log = LMSSyncLog(
        connection_id=connection.id, user_id=current_user.id, provider=connection.provider,
        sync_type="all", status="running", started_at=datetime.utcnow(),
    )
    db.add(sync_log)
    db.commit()
    try:
        connector = get_lms_connector(connection.provider)
        courses = await connector.get_courses(connection) if request.sync_courses else []
        created_courses = updated_courses = created_assignments = updated_assignments = 0
        for item in courses:
            mapping = db.query(ExternalCourseMap).filter(
                ExternalCourseMap.user_id == current_user.id,
                ExternalCourseMap.lms_connection_id == connection.id,
                ExternalCourseMap.external_course_id == item.external_id,
            ).first()
            if mapping:
                course = db.query(Course).filter(Course.id == mapping.internal_course_id, Course.user_id == current_user.id).first()
                if course:
                    course.name, course.code = item.name, item.code
                    course.instructor, course.description = item.instructor, item.description
                    updated_courses += 1
                mapping.last_synced_at = datetime.utcnow()
            else:
                course = Course(user_id=current_user.id, name=item.name, code=item.code, instructor=item.instructor, description=item.description)
                db.add(course)
                db.flush()
                mapping = ExternalCourseMap(
                    user_id=current_user.id, provider=connection.provider, lms_connection_id=connection.id,
                    external_course_id=item.external_id, internal_course_id=course.id, last_synced_at=datetime.utcnow(),
                )
                db.add(mapping)
                created_courses += 1
            if request.sync_assignments:
                for assignment in await connector.get_assignments(connection, item.external_id):
                    existing = db.query(Assignment).filter(
                        Assignment.course_id == course.id,
                        Assignment.external_provider == connection.provider,
                        Assignment.external_id == assignment.external_id,
                    ).first()
                    due = assignment.due_date.isoformat() if assignment.due_date else None
                    if existing:
                        existing.title, existing.description, existing.due_date = assignment.title, assignment.description, due
                        updated_assignments += 1
                    else:
                        db.add(Assignment(
                            course_id=course.id, title=assignment.title, description=assignment.description,
                            due_date=due, status="todo", external_provider=connection.provider,
                            external_id=assignment.external_id, external_course_id=assignment.course_external_id,
                        ))
                        created_assignments += 1
        summary = {
            "courses_discovered": len(courses), "courses_created": created_courses,
            "courses_updated": updated_courses, "assignments_created": created_assignments,
            "assignments_updated": updated_assignments,
        }
        connection.last_synced_at = datetime.utcnow()
        sync_log.status, sync_log.finished_at = "success", datetime.utcnow()
        sync_log.raw_summary_json = json.dumps(summary)
        db.commit()
        return {"status": "success", **summary}
    except BlackboardAPIError as exc:
        db.rollback()
        sync_log = db.query(LMSSyncLog).filter(LMSSyncLog.id == sync_log.id).first()
        sync_log.status, sync_log.message, sync_log.finished_at = "failed", str(exc), datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/{connection_id}/sync-logs", response_model=List[LMSSyncLogResponse])
def get_lms_sync_logs(connection_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    connection = db.query(LMSConnection).filter(
        LMSConnection.id == connection_id, LMSConnection.user_id == current_user.id
    ).first()
    if not connection:
        raise HTTPException(status_code=404, detail="LMS connection not found.")
    return db.query(LMSSyncLog).filter(
        LMSSyncLog.connection_id == connection_id, LMSSyncLog.user_id == current_user.id
    ).order_by(LMSSyncLog.started_at.desc()).all()
