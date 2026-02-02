from fastapi import FastAPI, HTTPException
from datetime import datetime, date, timedelta
from typing import List, Optional
from .models import ClockInRequest, AttendanceLog, ManualEntryRequest, UserSettings
from .models import UserCreate, UserLogin, UserResponse, Token, ForgotPasswordRequest, ResetPasswordRequest
from .db import get_db_connection
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
def get_user_settings(conn, user_id: str):
    row = conn.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,)).fetchone()
    if row:
        return dict(row)
    # Default Fallback
    return {
        "min_daily_hours": 8.0, 
        "office_start_time": "09:00",
        "last_allowed_entry": "10:00",
        "first_half_min_hours": 4.0
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
    conn = get_db_connection()
    try:
        c = conn.cursor()
        print(f"[DEBUG] Registering {user.email}...")
        
        # Check existing
        row = c.execute("SELECT * FROM users WHERE email = ?", (user.email,)).fetchone()
        if row:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash
        print("[DEBUG] Hashing password...")
        hashed = get_password_hash(user.password)
        print("[DEBUG] Hashing complete.")
        uid = str(uuid.uuid4())
        is_admin = 1 if user.email == "tauhidur.sifat@gmail.com" else 0
        
        c.execute("INSERT INTO users (id, email, name, password_hash, is_admin) VALUES (?, ?, ?, ?, ?)",
                  (uid, user.email, user.name, hashed, is_admin))
        conn.commit()
        print("[DEBUG] User committed to DB.")
        
        return {"id": uid, "email": user.email, "name": user.name, "is_admin": bool(is_admin), "created_at": datetime.now()}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/auth/login", response_model=Token)
def login(creds: UserLogin):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (creds.email,)).fetchone()
        
        if not row or not verify_password(creds.password, row['password_hash']):
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        
        # Generate Token
        token = create_access_token({"sub": row['id'], "email": row['email'], "name": row['name'], "is_admin": row['is_admin']})
        
        user_data = {"id": row['id'], "email": row['email'], "name": row['name'], "is_admin": bool(row['is_admin']), "created_at": row['created_at']}
        return {"access_token": token, "token_type": "bearer", "user": user_data}
    finally:
        conn.close()

@app.post("/auth/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (req.email,)).fetchone()
    if not row:
        conn.close()
        return {"message": "If email exists, reset link sent."} # Security: don't leak existence
    
    # Generate Token
    token = str(uuid.uuid4())
    expires = datetime.now() + timedelta(hours=1)
    uid = str(uuid.uuid4())
    
    conn.execute("INSERT INTO password_reset_tokens (id, user_id, token, expires_at) VALUES (?, ?, ?, ?)",
                 (uid, row['id'], token, expires.isoformat()))
    conn.commit()
    conn.close()
    
    # Simulate Email
    print(f"\n========================================\n[MOCK EMAIL] Password Reset Link: http://localhost:8501/?reset_token={token}\n========================================\n")
    return {"message": "Reset link sent (check console)"}

@app.post("/auth/reset-password")
def reset_password(req: ResetPasswordRequest):
    conn = get_db_connection()
    # Find valid token
    row = conn.execute("SELECT * FROM password_reset_tokens WHERE token = ? AND used = 0", (req.token,)).fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid token")
        
    expires = datetime.fromisoformat(row['expires_at'])
    if datetime.now() > expires:
        conn.close()
        raise HTTPException(status_code=400, detail="Token expired")
        
    # Update Password
    hashed = get_password_hash(req.new_password)
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, row['user_id']))
    conn.execute("UPDATE password_reset_tokens SET used = 1 WHERE id = ?", (row['id'],))
    conn.commit()
    conn.close()
    
    return {"message": "Password updated successfully"}

@app.post("/clock-in")
def clock_in(req: ClockInRequest):
    conn = get_db_connection()
    c = conn.cursor()
    today = req.timestamp.date()
    
    # 1. Future Date Check (Though mostly for manual, good safety)
    if req.timestamp.date() > date.today():
         conn.close()
         raise HTTPException(status_code=400, detail="Cannot clock-in for a future date.")

    # 2. Check for existing entry today
    exists = c.execute("SELECT * FROM attendance_logs WHERE user_id = ? AND date = ?", (req.user_id, str(today))).fetchone()
    
    settings = get_user_settings(conn, req.user_id)
    late_status = calculate_late_status_dynamic(req.timestamp, settings)
    required = calculate_required_dynamic("working", settings)
    
    if exists:
        # Edge Case: Overlapping Leave/Holiday (Constraint 4)
        # If exists but NO clock_in (e.g. manual leave entry), convert to Working
        if not exists['clock_in']:
            # Auto-switch to Working
            c.execute("""
                UPDATE attendance_logs 
                SET clock_in = ?, day_type = 'working', late_status = ?, required_minutes = ?, entry_method = 'auto'
                WHERE id = ?
            """, (req.timestamp.isoformat(), late_status, required, exists['id']))
            conn.commit()
            
            updated = c.execute("SELECT * FROM attendance_logs WHERE id = ?", (exists['id'],)).fetchone()
            res = dict(updated)
            conn.close()
            return res
        else:
             conn.close()
             raise HTTPException(status_code=400, detail="You already clocked in today.")

    # 3. Last Entry Check (Prev Day Missing Clock-out)
    yesterday = today - timedelta(days=1)
    # Ideally should check 'previous working day', but for MVP strict yesterday is per spec
    yest_log = c.execute("SELECT * FROM attendance_logs WHERE user_id = ? AND date = ?", (req.user_id, str(yesterday))).fetchone()
    if yest_log:
        if yest_log['clock_in'] and not yest_log['clock_out'] and yest_log['day_type'] in ['working', 'half-day']:
             conn.close()
             raise HTTPException(status_code=403, detail="Cannot clock-in: Previous day missing clock-out. Please fix manually.")

    # 4. Auto-Switch Day Type logic (Constraint 4)
    # Handled above in "exists" check for pre-existing manual entries.
    # Here we are creating a fresh one.

    c.execute("""
        INSERT INTO attendance_logs 
        (user_id, date, clock_in, day_type, late_status, required_minutes, entry_method)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (req.user_id, str(today), req.timestamp.isoformat(), "working", late_status, required, "auto"))
    conn.commit()
    
    # Return inserted
    new_row = c.execute("SELECT * FROM attendance_logs WHERE user_id = ? AND date = ?", (req.user_id, str(today))).fetchone()
    res = dict(new_row)
    conn.close()
    return res

@app.post("/clock-out")
def clock_out(req: ClockInRequest):
    conn = get_db_connection()
    c = conn.cursor()
    today = req.timestamp.date()
    
    current = c.execute("SELECT * FROM attendance_logs WHERE user_id = ? AND date = ?", (req.user_id, str(today))).fetchone()
    if not current:
         conn.close()
         raise HTTPException(status_code=404, detail="No clock-in record found for today.")
    
    if current['clock_out']:
        conn.close()
        raise HTTPException(status_code=400, detail="Already clocked out.")

    clock_in_time = datetime.fromisoformat(current['clock_in'])
    
    # 1. Time Logic: Out > In
    if req.timestamp <= clock_in_time:
         conn.close()
         raise HTTPException(status_code=400, detail="Clock-out must be after clock-in.")

    # 2. Strict Same-Day Rule (Midnight Oil)
    if not validate_same_day(clock_in_time, req.timestamp):
         conn.close()
         # In reality, might auto-cap. But per spec: "Default Rule: Enforce same-day only"
         raise HTTPException(status_code=400, detail="Clock-out cannot extend past 23:59:59 of the clock-in day.")

    worked = calculate_worked_minutes(clock_in_time, req.timestamp)
    
    c.execute("""
        UPDATE attendance_logs 
        SET clock_out = ?, worked_minutes = ?
        WHERE id = ?
    """, (req.timestamp.isoformat(), worked, current['id']))
    conn.commit()
    
    updated = c.execute("SELECT * FROM attendance_logs WHERE id = ?", (current['id'],)).fetchone()
    res = dict(updated)
    conn.close()
    return res

@app.post("/manual-entry")
def manual_entry(req: ManualEntryRequest):
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. No Future Dates
    if req.date > date.today():
         conn.close()
         raise HTTPException(status_code=400, detail="Manual entry cannot be set for a future date.")

    # 2. Time Logic
    if req.clock_in and req.clock_out:
        if req.clock_out <= req.clock_in:
             conn.close()
             raise HTTPException(status_code=400, detail="Manual entry invalid: Clock-out must be after clock-in.")
    
    # 3. Validation: No hours on Leave/Holiday
    if req.day_type in ['leave', 'holiday']:
        if req.clock_in or req.clock_out:
             conn.close()
             raise HTTPException(status_code=400, detail="Cannot log working hours on a Leave or Holiday. Change type to 'Working' or clear times.")

    exists = c.execute("SELECT * FROM attendance_logs WHERE user_id = ? AND date = ?", (req.user_id, str(req.date))).fetchone()
    
    entry_method = "manual"
    edited_at = datetime.now().isoformat()
    
    clock_in_val = req.clock_in.isoformat() if req.clock_in else None
    clock_out_val = req.clock_out.isoformat() if req.clock_out else None
    
    # Fetch Dynamic Settings
    settings = get_user_settings(conn, req.user_id)

    late_status = None
    if req.clock_in:
        late_status = calculate_late_status_dynamic(req.clock_in, settings)
    
    # Calculate worked minutes
    wholed_mins = None
    if req.clock_in and req.clock_out:
        wholed_mins = calculate_worked_minutes(req.clock_in, req.clock_out)
    else:
        # If clearing times or just setting status
        if req.day_type in ['leave', 'holiday']:
            wholed_mins = 0
    
    # 3. Day Type Logic warning check is mostly UI, but backend should enforce consequences
    # If they are setting 'working' but providing no times, worked_mins is None => Pending Log (Correct)

    required_mins = calculate_required_dynamic(req.day_type, settings)
    
    if exists:
        # Update
        fields = ["day_type = ?", "entry_method = ?", "edited_at = ?", "required_minutes = ?"]
        values = [req.day_type, entry_method, edited_at, required_mins]
        
        # Explicitly handle clock in/out updates
        fields.append("clock_in = ?")
        values.append(clock_in_val)
        
        fields.append("clock_out = ?")
        values.append(clock_out_val)
        
        fields.append("late_status = ?")
        # Logic: If clock-in changed, recalculate late status
        if req.clock_in:
             late_status = calculate_late_status_dynamic(req.clock_in, settings)
        else:
             pass # Keep existing
             
        values.append(late_status)
        
        if wholed_mins is not None:
             fields.append("worked_minutes = ?")
             values.append(wholed_mins)
        # If switching to leave/holiday, force worked_minutes to 0 if not calculated
        elif req.day_type in ['leave', 'holiday']:
             fields.append("worked_minutes = ?")
             values.append(0)

        values.append(exists['id'])
        
        sql = f"UPDATE attendance_logs SET {', '.join(fields)} WHERE id = ?"
        c.execute(sql, values)
        
    else:
        # Insert
        c.execute("""
            INSERT INTO attendance_logs 
            (user_id, date, day_type, entry_method, edited_at, clock_in, clock_out, late_status, worked_minutes, required_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (req.user_id, str(req.date), req.day_type, entry_method, edited_at, clock_in_val, clock_out_val, late_status, wholed_mins, required_mins))
        
    conn.commit()
    
    row = c.execute("SELECT * FROM attendance_logs WHERE user_id = ? AND date = ?", (req.user_id, str(req.date))).fetchone()
    res = dict(row)
    conn.close()
    return res

@app.get("/stats")
def get_stats(user_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None):
    conn = get_db_connection()
    c = conn.cursor()
    
    query = "SELECT * FROM attendance_logs WHERE user_id = ?"
    params = [user_id]
    
    if start_date:
        query += " AND date >= ?"
        params.append(str(start_date))
    if end_date:
        query += " AND date <= ?"
        params.append(str(end_date))
        
    rows = c.execute(query, params).fetchall()
    data = [dict(row) for row in rows]
    conn.close()
    return data

@app.get("/settings")
def get_settings(user_id: str):
    conn = get_db_connection()
    settings = get_user_settings(conn, user_id)
    conn.close()
    return settings

@app.post("/settings")
def update_settings(req: UserSettings):
    conn = get_db_connection()
    c = conn.cursor()
    # Upsert
    c.execute("""
        INSERT INTO user_settings (user_id, min_daily_hours, office_start_time, last_allowed_entry, first_half_min_hours, effective_date)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            min_daily_hours=excluded.min_daily_hours,
            office_start_time=excluded.office_start_time,
            last_allowed_entry=excluded.last_allowed_entry,
            first_half_min_hours=excluded.first_half_min_hours,
            effective_date=excluded.effective_date,
            updated_at=CURRENT_TIMESTAMP
    """, (req.user_id, req.min_daily_hours, req.office_start_time, req.last_allowed_entry, req.first_half_min_hours, req.effective_date))
    conn.commit()
    conn.close()
    return {"status": "updated"}

    """, (req.user_id, req.min_daily_hours, req.office_start_time, req.last_allowed_entry, req.first_half_min_hours, req.effective_date))
    conn.commit()
    conn.close()
    return {"status": "updated"}
