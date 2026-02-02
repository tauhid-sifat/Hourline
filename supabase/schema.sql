-- Enable UUID extension if not already enabled
create extension if not exists "uuid-ossp";

CREATE TABLE IF NOT EXISTS attendance_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users NOT NULL,
  date DATE NOT NULL,

  clock_in TIMESTAMPTZ,
  clock_out TIMESTAMPTZ,

  day_type TEXT CHECK (
    day_type IN ('working', 'half-day', 'leave', 'holiday')
  ) DEFAULT 'working',

  late_status TEXT CHECK (
    late_status IN ('on-time', 'late', 'violation')
  ),

  worked_minutes INTEGER,
  required_minutes INTEGER,

  entry_method TEXT CHECK (
    entry_method IN ('auto', 'manual')
  ) DEFAULT 'auto',

  edited_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(user_id, date)
);

-- Row Level Security
ALTER TABLE attendance_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own data" ON attendance_logs
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own data" ON attendance_logs
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own data" ON attendance_logs
  FOR UPDATE USING (auth.uid() = user_id);
