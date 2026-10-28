from datetime import date, datetime

from pydantic import BaseModel, Field


class CalibrationCreate(BaseModel):
    certificate_no: str = Field(..., min_length=3, max_length=80)
    verification_date: date | None = None
    next_due_date: date | None = None
    officer_name: str | None = Field(default=None, max_length=150)
    officer_title: str | None = Field(default=None, max_length=150)
    make_model: str | None = Field(default=None, max_length=150)
    max_capacity_kg: float | None = None
    min_capacity_kg: float | None = None
    accuracy_class: str | None = Field(default=None, max_length=40)
    e_value_kg: float | None = None
    d_value_kg: float | None = None
    seals_count: int | None = None
    seals_note: str | None = Field(default=None, max_length=200)
    location_label: str | None = Field(default=None, max_length=150)
    notes: str | None = None
    is_active: bool = True


class CalibrationUpdate(BaseModel):
    verification_date: date | None = None
    next_due_date: date | None = None
    officer_name: str | None = None
    officer_title: str | None = None
    make_model: str | None = None
    max_capacity_kg: float | None = None
    min_capacity_kg: float | None = None
    accuracy_class: str | None = None
    e_value_kg: float | None = None
    d_value_kg: float | None = None
    seals_count: int | None = None
    seals_note: str | None = None
    location_label: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class CalibrationOut(BaseModel):
    id: str
    certificate_no: str
    verification_date: date | None
    next_due_date: date | None
    officer_name: str | None
    officer_title: str | None
    make_model: str | None
    max_capacity_kg: float | None
    min_capacity_kg: float | None
    accuracy_class: str | None
    e_value_kg: float | None
    d_value_kg: float | None
    seals_count: int | None
    seals_note: str | None
    location_label: str | None
    notes: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
