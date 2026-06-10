from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from services import attendance_service

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


@router.get("/today")
def today(db: Session = Depends(get_db)):
    return attendance_service.get_today_records(db)


@router.get("/history")
def history(
    filter_date: Optional[date] = Query(None, alias="date"),
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    return attendance_service.get_history(db, filter_date, employee_id)
