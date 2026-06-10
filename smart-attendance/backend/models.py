from datetime import datetime, date
from sqlalchemy import Integer, String, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    employee_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    compreface_subject: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    photo_path: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    attendance_records: Mapped[list["Attendance"]] = relationship(
        "Attendance", back_populates="employee", cascade="all, delete-orphan"
    )


class Attendance(Base):
    __tablename__ = "attendance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    entry_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, default="entered")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    employee: Mapped["Employee"] = relationship("Employee", back_populates="attendance_records")
