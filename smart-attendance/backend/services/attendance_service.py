from datetime import datetime, date, timezone
from sqlalchemy.orm import Session, joinedload
from models import Attendance, Employee


def record_entry(db: Session, employee: Employee) -> Attendance:
    today = date.today()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Only skip if they are already actively inside right now
    active = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee.id, Attendance.date == today, Attendance.status == "entered")
        .first()
    )
    if active:
        return active  # cooldown in camera_worker should prevent this, but guard anyway

    # Create a fresh record — supports re-entry after exit
    record = Attendance(employee_id=employee.id, date=today, entry_time=now, status="entered")
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def record_exit(db: Session, employee: Employee) -> Attendance:
    today = date.today()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    record = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee.id, Attendance.date == today, Attendance.status == "entered")
        .first()
    )

    if not record:
        # Guard: already exited this cycle — don't create a duplicate row
        completed = (
            db.query(Attendance)
            .filter(Attendance.employee_id == employee.id, Attendance.date == today, Attendance.status == "completed")
            .order_by(Attendance.id.desc())
            .first()
        )
        if completed:
            return completed

        # No entry on record at all — create a standalone exit row
        record = Attendance(employee_id=employee.id, date=today, entry_time=None)
        db.add(record)

    record.exit_time = now
    record.status = "completed"
    if record.entry_time:
        delta = now - record.entry_time
        record.total_minutes = int(delta.total_seconds() // 60)
    db.commit()
    db.refresh(record)
    return record


def get_today_records(db: Session) -> list[dict]:
    today = date.today()
    records = (
        db.query(Attendance)
        .options(joinedload(Attendance.employee))
        .filter(Attendance.date == today)
        .order_by(Attendance.created_at.desc())
        .all()
    )
    return [_to_dict(r) for r in records]


def get_history(db: Session, filter_date: date | None = None, employee_id: int | None = None) -> list[dict]:
    q = db.query(Attendance).options(joinedload(Attendance.employee))
    if filter_date:
        q = q.filter(Attendance.date == filter_date)
    if employee_id:
        q = q.filter(Attendance.employee_id == employee_id)
    records = q.order_by(Attendance.date.desc(), Attendance.created_at.desc()).all()
    return [_to_dict(r) for r in records]


def _to_dict(r: Attendance) -> dict:
    return {
        "id": r.id,
        "employee_id": r.employee_id,
        "employee_name": r.employee.name,
        "employee_code": r.employee.employee_id,
        "date": r.date.isoformat(),
        "entry_time": r.entry_time.isoformat() if r.entry_time else None,
        "exit_time": r.exit_time.isoformat() if r.exit_time else None,
        "total_minutes": r.total_minutes,
        "status": r.status,
    }
