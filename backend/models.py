from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional, Literal
from pydantic import EmailStr

# --- AUTH MODELS ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    is_admin: bool
    created_at: str | datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
# -------------------

class ClockInRequest(BaseModel):
    user_id: str
    timestamp: datetime

class ManualEntryRequest(BaseModel):
    user_id: str
    date: date
    clock_in: Optional[datetime] = None
    clock_out: Optional[datetime] = None
    day_type: Literal['working', 'half-day', 'leave', 'holiday'] = 'working'

class UserSettings(BaseModel):
    user_id: str
    min_daily_hours: float = 8.0
    office_start_time: str = "09:00"
    last_allowed_entry: str = "10:00"
    first_half_min_hours: float = 4.0
    effective_date: str
    work_days: str = "0,1,2,3,4" # CSV defaults to Mon-Fri

class AttendanceLog(BaseModel):
    id: Optional[str] = None
    user_id: str
    date: date
    clock_in: Optional[datetime]
    clock_out: Optional[datetime]
    day_type: str
    late_status: Optional[str]
    worked_minutes: Optional[int]
    required_minutes: Optional[int]
    entry_method: str
    
    model_config = ConfigDict(from_attributes=True)
