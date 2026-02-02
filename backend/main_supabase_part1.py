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
    return pwd_context.verify(plain, hashed)

def get_password_hash(password):
    return pwd_context.hash(password)

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
    # Compare entry time vs settings
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

# --- Endpoints ---

@app.post("/auth/register", response_model=UserResponse)
def register(user: UserCreate):
    supabase = get_supabase_client()
    
    try:
        print(f"[DEBUG] Registering {user.email}...")
        
        # Check existing
        existing = supabase.table("users").select("*").eq("email", user.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash
        print("[DEBUG] Hashing password...")
        hashed = get_password_hash(user.password)
        print("[DEBUG] Hashing complete.")
        uid = str(uuid.uuid4())
        is_admin = user.email == "tauhidur.sifat@gmail.com"
        
        # Insert
        result = supabase.table("users").insert({
            "id": uid,
            "email": user.email,
            "name": user.name,
            "password_hash": hashed,
            "is_admin": is_admin
        }).execute()
        
        print("[DEBUG] User committed to DB.")
        
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
        # Fetch user
        response = supabase.table("users").select("*").eq("email", creds.email).execute()
        
        if not response.data:
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        
        row = response.data[0]
        
        if not verify_password(creds.password, row['password_hash']):
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        
        # Generate Token
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
        # Check if user exists
        response = supabase.table("users").select("*").eq("email", req.email).execute()
        if not response.data:
            return {"message": "If email exists, reset link sent."} # Security: don't leak existence
        
        row = response.data[0]
        
        # Generate Token
        token = str(uuid.uuid4())
        expires = datetime.now() + timedelta(hours=1)
        uid = str(uuid.uuid4())
        
        supabase.table("password_reset_tokens").insert({
            "id": uid,
            "user_id": row['id'],
            "token": token,
            "expires_at": expires.isoformat()
        }).execute()
        
        # Simulate Email
        print(f"\n========================================\n[MOCK EMAIL] Password Reset Link: http://localhost:8501/?reset_token={token}\n========================================\n")
        return {"message": "Reset link sent (check console)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/reset-password")
def reset_password(req: ResetPasswordRequest):
    supabase = get_supabase_client()
    
    try:
        # Find valid token
        response = supabase.table("password_reset_tokens").select("*").eq("token", req.token).eq("used", False).execute()
        
        if not response.data:
            raise HTTPException(status_code=400, detail="Invalid token")
        
        row = response.data[0]
        expires = datetime.fromisoformat(row['expires_at'].replace('Z', '+00:00'))
        
        if datetime.now(expires.tzinfo) > expires:
            raise HTTPException(status_code=400, detail="Token expired")
        
        # Update Password
        hashed = get_password_hash(req.new_password)
        supabase.table("users").update({"password_hash": hashed}).eq("id", row['user_id']).execute()
        supabase.table("password_reset_tokens").update({"used": True}).eq("id", row['id']).execute()
        
        return {"message": "Password updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ... (Continuing with remaining endpoints in next file update)
