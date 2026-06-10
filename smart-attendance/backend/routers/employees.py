import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from database import get_db
from models import Employee
from schemas import EmployeeCreate, EmployeeRead
from services import compreface
from services.camera_worker import get_camera_state

PHOTOS_DIR = "/data/photos"

router = APIRouter(prefix="/api/employees", tags=["employees"])


def _employee_to_read(emp: Employee) -> EmployeeRead:
    return EmployeeRead(
        id=emp.id,
        name=emp.name,
        employee_id=emp.employee_id,
        compreface_subject=emp.compreface_subject,
        photo_path=emp.photo_path,
        created_at=emp.created_at,
        enrolled=emp.photo_path is not None,
    )


@router.get("", response_model=list[EmployeeRead])
def list_employees(db: Session = Depends(get_db)):
    return [_employee_to_read(e) for e in db.query(Employee).order_by(Employee.name).all()]


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(body: EmployeeCreate, db: Session = Depends(get_db)):
    if db.query(Employee).filter(Employee.employee_id == body.employee_id).first():
        raise HTTPException(status_code=409, detail="Employee ID already exists")
    emp = Employee(
        name=body.name,
        employee_id=body.employee_id,
        compreface_subject=str(uuid.uuid4()),
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return _employee_to_read(emp)


@router.delete("/{emp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(emp_id: int, db: Session = Depends(get_db)):
    emp = db.get(Employee, emp_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    try:
        await compreface.delete_subject(emp.compreface_subject)
    except Exception:
        pass  # best-effort
    if emp.photo_path and os.path.exists(emp.photo_path):
        os.remove(emp.photo_path)
    db.delete(emp)
    db.commit()


@router.post("/{emp_id}/enroll", response_model=dict)
async def enroll_upload(emp_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    emp = db.get(Employee, emp_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    image_bytes = await file.read()
    try:
        result = await compreface.enroll_face(image_bytes, emp.compreface_subject)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"CompreFace error: {exc}")
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    photo_path = os.path.join(PHOTOS_DIR, f"{emp.compreface_subject}.jpg")
    with open(photo_path, "wb") as f:
        f.write(image_bytes)
    emp.photo_path = photo_path
    db.commit()
    return {"enrolled": True, "image_id": result.get("image_id")}


@router.post("/{emp_id}/enroll/capture", response_model=dict)
async def enroll_capture(emp_id: int, db: Session = Depends(get_db)):
    emp = db.get(Employee, emp_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    frame = get_camera_state("entrance").latest_frame
    if not frame:
        raise HTTPException(status_code=503, detail="Entrance camera not ready")
    try:
        result = await compreface.enroll_face(frame, emp.compreface_subject)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"CompreFace error: {exc}")
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    photo_path = os.path.join(PHOTOS_DIR, f"{emp.compreface_subject}.jpg")
    with open(photo_path, "wb") as f:
        f.write(frame)
    emp.photo_path = photo_path
    db.commit()
    return {"enrolled": True, "image_id": result.get("image_id")}
