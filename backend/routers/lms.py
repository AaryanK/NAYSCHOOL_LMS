import json
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.deps import get_current_user
from backend.models import User, LMSConnection, LMSSyncLog, ExternalCourseMap, Course, Assignment
from backend.config import settings
from backend.lms.connector_registry import get_lms_connector
from backend.services.token_service import encrypt_token

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
    external_user_id: Optional[str] = None
    status: str
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class ConnectRequest(BaseModel):
    school_domain: str

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

@router.get("/providers", response_model=ProvidersResponse)
def get_lms_providers(current_user: User = Depends(get_current_user)):
    providers = []
    
    # Blackboard status
    bb_configured = bool(
        settings.BLACKBOARD_BASE_URL and
        settings.BLACKBOARD_CLIENT_ID and
        settings.BLACKBOARD_CLIENT_SECRET
    )
    providers.append(ProviderInfo(
        name="blackboard",
        enabled=settings.BLACKBOARD_ENABLED,
        configured=bb_configured
    ))
    
    # Canvas status
    canvas_configured = bool(
        settings.CANVAS_BASE_URL and
        settings.CANVAS_CLIENT_ID and
        settings.CANVAS_CLIENT_SECRET
    )
    providers.append(ProviderInfo(
        name="canvas",
        enabled=settings.CANVAS_ENABLED,
        configured=canvas_configured
    ))
    
    return ProvidersResponse(providers=providers)

@router.get("/connections", response_model=List[LMSConnectionResponse])
def get_lms_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conns = db.query(LMSConnection).filter(LMSConnection.user_id == current_user.id).all()
    return conns

@router.post("/{provider}/connect")
async def connect_lms_provider(
    provider: str,
    request: ConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        connector = get_lms_connector(provider)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Check if configured
    is_configured = False
    if provider == "blackboard":
        is_configured = bool(
            settings.BLACKBOARD_ENABLED and
            settings.BLACKBOARD_BASE_URL and
            settings.BLACKBOARD_CLIENT_ID and
            settings.BLACKBOARD_CLIENT_SECRET
        )
    elif provider == "canvas":
        is_configured = bool(
            settings.CANVAS_ENABLED and
            settings.CANVAS_BASE_URL and
            settings.CANVAS_CLIENT_ID and
            settings.CANVAS_CLIENT_SECRET
        )
        
    if not is_configured:
        setup_instructions = [
            f"Set {provider.upper()}_ENABLED=true in your environment/.env",
            f"Provide configuration values: URL, Client ID, Client Secret",
            f"For Blackboard, ensure App ID is authorized by the system administrator."
        ]
        return {
            "status": "not_configured",
            "message": f"{provider.capitalize()} is not fully configured on this server.",
            "next_steps": setup_instructions
        }
        
    try:
        auth_url = await connector.build_authorization_url(current_user.id)
        
        # Check for existing connection or build fresh one in disconnected status
        conn_record = db.query(LMSConnection).filter(
            LMSConnection.user_id == current_user.id,
            LMSConnection.provider == provider
        ).first()
        
        if not conn_record:
            conn_record = LMSConnection(
                user_id=current_user.id,
                provider=provider,
                school_domain=request.school_domain,
                status="disconnected"
            )
            db.add(conn_record)
        else:
            conn_record.school_domain = request.school_domain
            conn_record.status = "disconnected"
            conn_record.updated_at = datetime.utcnow()
            
        db.commit()
        
        return {
            "status": "configured",
            "authorization_url": auth_url
        }
    except Exception as e:
        logger.exception("Failed to build authorization redirect url.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection setup failed: {str(e)}"
        )

@router.get("/{provider}/oauth/callback", response_class=HTMLResponse)
async def lms_oauth_callback(
    provider: str,
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    try:
        # Extract user_id from state (format: {user_id}:...)
        parts = state.split(":")
        user_id = int(parts[0])
    except Exception:
        return "<html><body><h1>Authorization Failed</h1><p>Invalid state parameter returned.</p></body></html>"

    try:
        connector = get_lms_connector(provider)
        token_data = await connector.exchange_code_for_token(code, state)
        
        # Extract properties safely
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        external_user_id = token_data.get("user_id") or token_data.get("user")
        expires_in = token_data.get("expires_in", 3600)
        
        # Encrypt tokens
        access_token_encrypted = encrypt_token(access_token) if access_token else None
        refresh_token_encrypted = encrypt_token(refresh_token) if refresh_token else None
        
        expires_at = datetime.utcnow() + datetime.timedelta(seconds=int(expires_in)) if expires_in else None
        
        # Update/Create Connection row
        conn_record = db.query(LMSConnection).filter(
            LMSConnection.user_id == user_id,
            LMSConnection.provider == provider
        ).first()
        
        if not conn_record:
            conn_record = LMSConnection(
                user_id=user_id,
                provider=provider,
                status="connected",
                external_user_id=str(external_user_id) if external_user_id else None,
                access_token_encrypted=access_token_encrypted,
                refresh_token_encrypted=refresh_token_encrypted,
                token_expires_at=expires_at,
                scopes=token_data.get("scope")
            )
            db.add(conn_record)
        else:
            conn_record.status = "connected"
            conn_record.external_user_id = str(external_user_id) if external_user_id else conn_record.external_user_id
            conn_record.access_token_encrypted = access_token_encrypted
            conn_record.refresh_token_encrypted = refresh_token_encrypted
            conn_record.token_expires_at = expires_at
            conn_record.scopes = token_data.get("scope") or conn_record.scopes
            conn_record.updated_at = datetime.utcnow()
            
        db.commit()
        
        return "<html><body><h1>Authentication Successful</h1><p>You can close this window now and return to NaySchool.</p></body></html>"
    except Exception as e:
        logger.exception("Failure in OAuth callback authentication sequence.")
        return f"<html><body><h1>Authorization Failed</h1><p>{str(e)}</p></body></html>"

@router.post("/{connection_id}/sync")
async def sync_lms_connection(
    connection_id: int,
    request: SyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conn_record = db.query(LMSConnection).filter(
        LMSConnection.id == connection_id,
        LMSConnection.user_id == current_user.id
    ).first()
    
    if not conn_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LMS connection not found."
        )

    # Initialize sync log
    sync_log = LMSSyncLog(
        connection_id=conn_record.id,
        user_id=current_user.id,
        provider=conn_record.provider,
        sync_type="all",
        status="running",
        started_at=datetime.utcnow()
    )
    db.add(sync_log)
    db.commit()
    db.refresh(sync_log)

    # If provider is not enabled in backend config, return not_configured summary
    if conn_record.provider == "blackboard" and not settings.BLACKBOARD_ENABLED:
        sync_log.status = "not_configured"
        sync_log.message = (
            "Blackboard is scaffolded but not configured. "
            "Add BLACKBOARD_BASE_URL, BLACKBOARD_CLIENT_ID, BLACKBOARD_CLIENT_SECRET, and obtain admin approval."
        )
        sync_log.finished_at = datetime.utcnow()
        db.commit()
        
        return {
            "status": "not_configured",
            "message": "Blackboard is scaffolded but not configured. Add BLACKBOARD_BASE_URL, BLACKBOARD_CLIENT_ID, BLACKBOARD_CLIENT_SECRET, and obtain admin approval.",
            "next_steps": [
                "Register developer application on Anthology Developer portal (developer.anthology.com)",
                "Add your Client ID under REST API Integrations in Blackboard administrator panel",
                "Ensure BLACKBOARD_ENABLED=true is set in your environment / .env"
            ]
        }

    try:
        connector = get_lms_connector(conn_record.provider)
    except ValueError as e:
        sync_log.status = "failed"
        sync_log.message = str(e)
        sync_log.finished_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))

    try:
        courses_synced = 0
        assignments_synced = 0
        
        # 1. Sync Courses
        if request.sync_courses:
            lms_courses = await connector.get_courses(conn_record)
            for lms_course in lms_courses:
                # Find if course map already exists
                map_record = db.query(ExternalCourseMap).filter(
                    ExternalCourseMap.user_id == current_user.id,
                    ExternalCourseMap.provider == conn_record.provider,
                    ExternalCourseMap.external_course_id == lms_course.external_id
                ).first()
                
                if not map_record:
                    # Create internal Course
                    new_course = Course(
                        user_id=current_user.id,
                        name=lms_course.name,
                        code=lms_course.code or "LMS",
                        instructor=lms_course.instructor or "LMS Instructor",
                        description=lms_course.description or "Synchronized from LMS"
                    )
                    db.add(new_course)
                    db.flush()
                    
                    # Create external mapping
                    map_record = ExternalCourseMap(
                        user_id=current_user.id,
                        provider=conn_record.provider,
                        lms_connection_id=conn_record.id,
                        external_course_id=lms_course.external_id,
                        internal_course_id=new_course.id
                    )
                    db.add(map_record)
                    db.flush()
                    courses_synced += 1
                else:
                    map_record.last_synced_at = datetime.utcnow()
                    db.flush()
                
                internal_course_id = map_record.internal_course_id
                
                # 2. Sync Assignments (per course)
                if request.sync_assignments:
                    lms_assignments = await connector.get_assignments(conn_record, lms_course.external_id)
                    for lms_assign in lms_assignments:
                        existing_assign = db.query(Assignment).filter(
                            Assignment.course_id == internal_course_id,
                            Assignment.external_provider == conn_record.provider,
                            Assignment.external_id == lms_assign.external_id
                        ).first()
                        
                        if not existing_assign:
                            new_assign = Assignment(
                                course_id=internal_course_id,
                                title=lms_assign.title,
                                description=lms_assign.description or "Synchronized assignment",
                                due_date=lms_assign.due_date.isoformat() if lms_assign.due_date else None,
                                status="todo",
                                external_provider=conn_record.provider,
                                external_id=lms_assign.external_id,
                                external_course_id=lms_assign.course_external_id
                            )
                            db.add(new_assign)
                            assignments_synced += 1
            
        conn_record.last_synced_at = datetime.utcnow()
        conn_record.status = "connected"
        
        sync_log.status = "success"
        sync_log.finished_at = datetime.utcnow()
        sync_log.raw_summary_json = json.dumps({
            "courses_synced": courses_synced,
            "assignments_synced": assignments_synced
        })
        db.commit()
        
        return {
            "status": "success",
            "message": "LMS synchronization completed successfully.",
            "synced_courses_count": courses_synced,
            "synced_assignments_count": assignments_synced
        }
    except Exception as e:
        logger.exception("LMS synchronization routine encountered critical error.")
        sync_log.status = "failed"
        sync_log.message = f"Sync failed: {str(e)}"
        sync_log.finished_at = datetime.utcnow()
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LMS synchronization failed: {str(e)}"
        )

@router.get("/{connection_id}/sync-logs", response_model=List[LMSSyncLogResponse])
def get_lms_sync_logs(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify ownership
    conn = db.query(LMSConnection).filter(
        LMSConnection.id == connection_id,
        LMSConnection.user_id == current_user.id
    ).first()
    
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LMS Connection not found."
        )
        
    logs = db.query(LMSSyncLog).filter(
        LMSSyncLog.connection_id == connection_id,
        LMSSyncLog.user_id == current_user.id
    ).order_by(LMSSyncLog.started_at.desc()).all()
    
    return logs
