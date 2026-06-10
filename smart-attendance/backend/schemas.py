from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class EmployeeCreate(BaseModel):
    name: str
    employee_id: str


class EmployeeRead(BaseModel):
    id: int
    name: str
    employee_id: str
    compreface_subject: str
    photo_path: Optional[str]
    created_at: datetime
    enrolled: bool = False

    model_config = {"from_attributes": True}


class AttendanceRead(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    employee_code: str
    date: date
    entry_time: Optional[datetime]
    exit_time: Optional[datetime]
    total_minutes: Optional[int]
    status: str

    model_config = {"from_attributes": True}


class AttendanceEvent(BaseModel):
    type: str = "attendance"
    camera: str
    employee_id: int
    employee_name: str
    employee_code: str
    timestamp: datetime
    status: str


class SystemStatus(BaseModel):
    compreface_ready: bool
    compreface_url: str
    cameras: dict[str, bool]


class ConfigUpdate(BaseModel):
    compreface_api_key: str


class CameraAssignment(BaseModel):
    entrance_source: str
    exit_source: str
