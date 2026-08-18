from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

class LMSCourse(BaseModel):
    external_id: str
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    instructor: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

class LMSAssignment(BaseModel):
    external_id: str
    course_external_id: str
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    points_possible: Optional[float] = None
    raw: Optional[Dict[str, Any]] = None

class LMSContentItem(BaseModel):
    external_id: str
    course_external_id: str
    title: str
    content_type: str
    url: Optional[str] = None
    file_name: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

class LMSAnnouncement(BaseModel):
    external_id: str
    course_external_id: str
    title: str
    body: Optional[str] = None
    posted_at: Optional[datetime] = None
    raw: Optional[Dict[str, Any]] = None

class LMSGradeItem(BaseModel):
    external_id: str
    course_external_id: str
    title: str
    score: Optional[float] = None
    points_possible: Optional[float] = None
    raw: Optional[Dict[str, Any]] = None

class LMSCalendarEvent(BaseModel):
    external_id: str
    course_external_id: Optional[str] = None
    title: str
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    raw: Optional[Dict[str, Any]] = None
