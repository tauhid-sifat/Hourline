import sqlite3
import os
from datetime import datetime

DB_NAME = "hourline.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Enable FKs
    c.execute("PRAGMA foreign_keys = ON;")
    
    # Create Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS attendance_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        date TEXT NOT NULL,
        clock_in TEXT,
        clock_out TEXT,
        day_type TEXT CHECK (day_type IN ('working', 'half-day', 'leave', 'holiday')) DEFAULT 'working',
        late_status TEXT CHECK (late_status IN ('on-time', 'late', 'violation')),
        worked_minutes INTEGER,
        required_minutes INTEGER,
        entry_method TEXT CHECK (entry_method IN ('auto', 'manual')) DEFAULT 'auto',
        edited_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, date)
    );
    """)

    c.execute(f"""
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id TEXT PRIMARY KEY,
        min_daily_hours REAL DEFAULT 8.0,
        office_start_time TEXT DEFAULT '09:00',
        last_allowed_entry TEXT DEFAULT '10:00',
        first_half_min_hours REAL DEFAULT 4.0,
        effective_date TEXT DEFAULT CURRENT_DATE,
        work_days TEXT DEFAULT '0,1,2,3,4',
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Migration for existing DBs
    try:
        c.execute("ALTER TABLE user_settings ADD COLUMN work_days TEXT DEFAULT '0,1,2,3,4'")
    except sqlite3.OperationalError:
        pass # Column likely exists
    
    except sqlite3.OperationalError:
        pass # Column likely exists
    
    # Auth Tables
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        token TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        used INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    conn.commit()
    conn.close()

# Initialize on module load or explicilty
init_db()
