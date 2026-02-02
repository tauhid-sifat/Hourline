from fastapi import FastAPI, HTTPException
from datetime import datetime, date, timedelta
from typing import List, Optional
from .models import ClockInRequest, AttendanceLog, ManualEntryRequest, UserSettings
from .models import UserCreate, UserLogin, UserResponse, Token, ForgotPasswordRequest, ResetPasswordRequest
from .db import get_supabase_client
from .calculations import calculate_worked_minutes
import uuid
from passlib.context import CryptContext
import jwt
import os

# Auth Config
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-please-change-in-prod")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain, hashed):
    # Bcrypt has a 72-byte limit
    return pwd_context.verify(plain[:72], hashed)

def get_password_hash(password):
    # Bcrypt has a 72-byte limit  
    return pwd_context.hash(password[:72])

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=60) # 1 hr session
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

app = FastAPI(title="Hourline API")

# --- Helpers ---

def validate_same_day(t1: datetime, t2: datetime) -> bool:
    return t1.date() == t2.date()

def validate_no_future_date(d: date) -> bool:
    return d <= date.today()

# --- Config Logic ---
def get_user_settings(user_id: str):
    supabase = get_supabase_client()
    response = supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
    
    if response.data:
        return response.data[0]
    # Default Fallback
    return {
        "min_daily_hours": 8.0, 
        "office_start_time": "09:00",
        "last_allowed_entry": "10:00",
        "first_half_min_hours": 4.0,
        "work_days": "0,1,2,3,4"
    }

def calculate_late_status_dynamic(clock_in_dt: datetime, settings: dict) -> str:
    entry_time_str = clock_in_dt.strftime("%H:%M")
    if entry_time_str <= settings['office_start_time']:
        return 'on-time'
    elif entry_time_str <= settings['last_allowed_entry']:
        return 'late'
    else:
        return 'violation'

def calculate_required_dynamic(day_type: str, settings: dict) -> int:
    if day_type == 'working':
        return int(settings['min_daily_hours'] * 60)
    elif day_type == 'half-day':
        return int(settings['first_half_min_hours'] * 60)
    else:
        return 0

# --- AUTH ENDPOINTS ---

@app.post("/auth/register", response_model=UserResponse)
def register(user: UserCreate):
    supabase = get_supabase_client()
    
    try:
        # Check existing
        existing = supabase.table("users").select("*").eq("email", user.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Truncate password to 72 chars to ensure bcrypt compatibility
        safe_password = user.password[:72]
        
        # Hash
        hashed = get_password_hash(safe_password)
        uid = str(uuid.uuid4())
        is_admin = user.email == "tauhidur.sifat@gmail.com"
        
        # Insert
        supabase.table("users").insert({
            "id": uid,
            "email": user.email,
            "name": user.name,
            "password_hash": hashed,
            "is_admin": is_admin
        }).execute()
        
        return {
            "id": uid, 
            "email": user.email, 
            "name": user.name, 
            "is_admin": is_admin, 
            "created_at": datetime.now()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/login", response_model=Token)
def login(creds: UserLogin):
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("users").select("*").eq("email", creds.email).execute()
        
        if not response.data:
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        
        row = response.data[0]
        
        if not verify_password(creds.password, row['password_hash']):
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        
        token = create_access_token({
            "sub": row['id'], 
            "email": row['email'], 
            "name": row['name'], 
            "is_admin": row['is_admin']
        })
        
        user_data = {
            "id": row['id'], 
            "email": row['email'], 
            "name": row['name'], 
            "is_admin": bool(row['is_admin']), 
            "created_at": row['created_at']
        }
        return {"access_token": token, "token_type": "bearer", "user": user_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("users").select("*").eq("email", req.email).execute()
        if not response.data:
            return {"message": "If email exists, reset link sent."}
        
        row = response.data[0]
        token = str(uuid.uuid4())
        expires = datetime.now() + timedelta(hours=1)
        uid = str(uuid.uuid4())
        
        supabase.table("password_reset_tokens").insert({
            "id": uid,
            "user_id": row['id'],
            "token": token,
            "expires_at": expires.isoformat()
        }).execute()
        
        print(f"\n========================================\n[MOCK EMAIL] Password Reset Link: http://localhost:8501/?reset_token={token}\n========================================\n")
        return {"message": "Reset link sent (check console)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/reset-password")
def reset_password(req: ResetPasswordRequest):
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("password_reset_tokens").select("*").eq("token", req.token).eq("used", False).execute()
        
        if not response.data:
            raise HTTPException(status_code=400, detail="Invalid token")
        
        row = response.data[0]
        expires = datetime.fromisoformat(row['expires_at'].replace('Z', '+00:00').replace('+00:00', ''))
        
        if datetime.now() > expires:
            raise HTTPException(status_code=400, detail="Token expired")
        
        hashed = get_password_hash(req.new_password)
        supabase.table("users").update({"password_hash": hashed}).eq("id", row['user_id']).execute()
        supabase.table("password_reset_tokens").update({"used": True}).eq("id", row['id']).execute()
        
        return {"message": "Password updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ATTENDANCE ENDPOINTS ---

@app.post("/clock-in")
def clock_in(req: ClockInRequest):
    supabase = get_supabase_client()
    today = req.timestamp.date()
    
    try:
        # Future date check
        if req.timestamp.date() > date.today():
            raise HTTPException(status_code=400, detail="Cannot clock-in for a future date.")
        
        # Check existing entry
        response = supabase.table("attendance_logs").select("*").eq("user_id", req.user_id).eq("date", str(today)).execute()
        
        settings = get_user_settings(req.user_id)
        late_status = calculate_late_status_dynamic(req.timestamp, settings)
        required = calculate_required_dynamic("working", settings)
        
        if response.data:
            exists = response.data[0]
            # Edge case: convert leave/holiday to working
            if not exists['clock_in']:
                supabase.table("attendance_logs").update({
                    "clock_in": req.timestamp.isoformat(),
                    "day_type": "working",
                    "late_status": late_status,
                    "required_minutes": required,
                    "entry_method": "auto"
                }).eq("id", exists['id']).execute()
                
                updated = supabase.table("attendance_logs").select("*").eq("id", exists['id']).execute()
                return updated.data[0]
            else:
                raise HTTPException(status_code=400, detail="You already clocked in today.")
        
        # Check previous day
        yesterday = today - timedelta(days=1)
        yest_response = supabase.table("attendance_logs").select("*").eq("user_id", req.user_id).eq("date", str(yesterday)).execute()
        
        if yest_response.data:
            yest_log = yest_response.data[0]
            if yest_log.get('clock_in') and not yest_log.get('clock_out') and yest_log['day_type'] in ['working', 'half-day']:
                raise HTTPException(status_code=403, detail="Cannot clock-in: Previous day missing clock-out. Please fix manually.")
        
        # Insert new
        result = supabase.table("attendance_logs").insert({
            "user_id": req.user_id,
            "date": str(today),
            "clock_in": req.timestamp.isoformat(),
            "day_type": "working",
            "late_status": late_status,
            "required_minutes": required,
            "entry_method": "auto"
        }).execute()
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clock-out")
def clock_out(req: ClockInRequest):
    supabase = get_supabase_client()
    today = req.timestamp.date()
    
    try:
        response = supabase.table("attendance_logs").select("*").eq("user_id", req.user_id).eq("date", str(today)).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="No clock-in record found for today.")
        
        current = response.data[0]
        
        if current.get('clock_out'):
            raise HTTPException(status_code=400, detail="Already clocked out.")
        
        clock_in_time = datetime.fromisoformat(current['clock_in'])
        
        if req.timestamp <= clock_in_time:
            raise HTTPException(status_code=400, detail="Clock-out must be after clock-in.")
        
        if not validate_same_day(clock_in_time, req.timestamp):
            raise HTTPException(status_code=400, detail="Clock-out cannot extend past 23:59:59 of the clock-in day.")
        
        worked = calculate_worked_minutes(clock_in_time, req.timestamp)
        
        supabase.table("attendance_logs").update({
            "clock_out": req.timestamp.isoformat(),
            "worked_minutes": worked
        }).eq("id", current['id']).execute()
        
        updated = supabase.table("attendance_logs").select("*").eq("id", current['id']).execute()
        return updated.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/manual-entry")
def manual_entry(req: ManualEntryRequest):
    supabase = get_supabase_client()
    
    try:
        # No future dates
        if req.date > date.today():
            raise HTTPException(status_code=400, detail="Manual entry cannot be set for a future date.")
        
        # Time logic
        if req.clock_in and req.clock_out:
            if req.clock_out <= req.clock_in:
                raise HTTPException(status_code=400, detail="Manual entry invalid: Clock-out must be after clock-in.")
        
        # No hours on leave/holiday
        if req.day_type in ['leave', 'holiday']:
            if req.clock_in or req.clock_out:
                raise HTTPException(status_code=400, detail="Cannot log working hours on a Leave or Holiday. Change type to 'Working' or clear times.")
        
        response = supabase.table("attendance_logs").select("*").eq("user_id", req.user_id).eq("date", str(req.date)).execute()
        
        entry_method = "manual"
        edited_at = datetime.now().isoformat()
        
        clock_in_val = req.clock_in.isoformat() if req.clock_in else None
        clock_out_val = req.clock_out.isoformat() if req.clock_out else None
        
        settings = get_user_settings(req.user_id)
        
        late_status = None
        if req.clock_in:
            late_status = calculate_late_status_dynamic(req.clock_in, settings)
        
        worked_mins = None
        if req.clock_in and req.clock_out:
            worked_mins = calculate_worked_minutes(req.clock_in, req.clock_out)
        elif req.day_type in ['leave', 'holiday']:
            worked_mins = 0
        
        required_mins = calculate_required_dynamic(req.day_type, settings)
        
        if response.data:
            # Update
            supabase.table("attendance_logs").update({
                "day_type": req.day_type,
                "entry_method": entry_method,
                "edited_at": edited_at,
                "required_minutes": required_mins,
                "clock_in": clock_in_val,
                "clock_out": clock_out_val,
                "late_status": late_status,
                "worked_minutes": worked_mins
            }).eq("user_id", req.user_id).eq("date", str(req.date)).execute()
        else:
            # Insert
            supabase.table("attendance_logs").insert({
                "user_id": req.user_id,
                "date": str(req.date),
                "day_type": req.day_type,
                "entry_method": entry_method,
                "edited_at": edited_at,
                "clock_in": clock_in_val,
                "clock_out": clock_out_val,
                "late_status": late_status,
                "worked_minutes": worked_mins,
                "required_minutes": required_mins
            }).execute()
        
        result = supabase.table("attendance_logs").select("*").eq("user_id", req.user_id).eq("date", str(req.date)).execute()
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
def get_stats(user_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None):
    supabase = get_supabase_client()
    
    try:
        query = supabase.table("attendance_logs").select("*").eq("user_id", user_id)
        
        if start_date:
            query = query.gte("date", str(start_date))
        if end_date:
            query = query.lte("date", str(end_date))
        
        response = query.execute()
        return response.data
    except Exception as e:
      raise HTTPException(status_code=500, detail=str(e))

@app.get("/settings")
def get_settings(user_id: str):
    try:
        settings = get_user_settings(user_id)
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/settings")
def update_settings(req: UserSettings):
    supabase = get_supabase_client()
    
    try:
        # Check if exists
        response = supabase.table("user_settings").select("*").eq("user_id", req.user_id).execute()
        
        data = {
            "min_daily_hours": req.min_daily_hours,
            "office_start_time": req.office_start_time,
            "last_allowed_entry": req.last_allowed_entry,
            "first_half_min_hours": req.first_half_min_hours,
            "effective_date": req.effective_date,
            "work_days": req.work_days
        }
        
        if response.data:
            # Update
            supabase.table("user_settings").update(data).eq("user_id", req.user_id).execute()
        else:
            # Insert
            data["user_id"] = req.user_id
            supabase.table("user_settings").insert(data).execute()
        
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
