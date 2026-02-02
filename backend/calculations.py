from datetime import datetime, time, timedelta

# Config (Could be dynamic later)
OFFICE_START_TIME = time(9, 0)
LAST_ALLOWED_ENTRY = time(10, 0) # Example
MIN_WORKING_HOURS = 8
HALF_DAY_FACTOR = 0.5

def calculate_late_status(clock_in: datetime) -> str:
    """
    On-time: <= start time
    Late: start < time <= last allowed
    Violation: > last allowed
    """
    entry_time = clock_in.time()
    
    if entry_time <= OFFICE_START_TIME:
        return 'on-time'
    elif entry_time <= LAST_ALLOWED_ENTRY:
        return 'late'
    else:
        return 'violation'

def calculate_required_minutes(day_type: str) -> int:
    if day_type == 'working':
        return MIN_WORKING_HOURS * 60
    elif day_type == 'half-day':
        return int(MIN_WORKING_HOURS * 60 * HALF_DAY_FACTOR)
    else:
        return 0

def calculate_worked_minutes(clock_in: datetime, clock_out: datetime) -> int:
    delta = clock_out - clock_in
    return int(delta.total_seconds() / 60)
