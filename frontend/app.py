import streamlit as st
import httpx
import pandas as pd
from datetime import datetime, timedelta, date
import calendar

# Config
API_URL = "http://localhost:8000"

st.set_page_config(page_title="Hourline", layout="wide", page_icon="⏱️")

# Nord Theme CSS "Glow Up"
NORD_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Roboto+Mono:wght@400;500&display=swap');

    /* Nord Palette */
    :root {
        --polar-night-1: #2E3440;
        --polar-night-2: #3B4252;
        --polar-night-3: #434C5E;
        --polar-night-4: #4C566A;
        --snow-storm-1: #D8DEE9;
        --snow-storm-2: #E5E9F0;
        --snow-storm-3: #ECEFF4;
        --frost-1: #8FBCBB;
        --frost-2: #88C0D0;
        --frost-3: #81A1C1;
        --frost-4: #5E81AC;
        --aurora-red: #BF616A;
        --aurora-orange: #D08770;
        --aurora-yellow: #EBCB8B;
        --aurora-green: #A3BE8C;
    }

    /* Global Typography & Background */
    .stApp {
        background-color: var(--polar-night-1);
        font-family: 'Inter', sans-serif !important;
    }
    
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stText, div {
        color: var(--snow-storm-2) !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* Sidebar - Darker contrast */
    [data-testid="stSidebar"] {
        background-color: #242933;
        border-right: 1px solid var(--polar-night-3);
    }
    
    /* Buttons */
    .stButton > button {
        width: 100%;
        background-color: var(--polar-night-2);
        color: var(--snow-storm-2);
        border: 1px solid var(--polar-night-4);
        border-radius: 6px !important;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: var(--polar-night-3);
        border-color: var(--frost-3);
        color: var(--snow-storm-3);
    }
    
    /* Primary Action */
    button[kind="primary"] {
        background-color: var(--frost-4) !important;
        color: var(--snow-storm-3) !important;
        border: none !important;
        font-weight: 600;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    button[kind="primary"]:hover {
        background-color: var(--frost-3) !important;
        transform: translateY(-1px);
    }

    /* Dialog styling tweak (if possible via CSS inject) */
    div[data-testid="stDialog"] {
        background-color: var(--polar-night-1);
    }

    /* Cards */
    .metric-card {
        background-color: var(--polar-night-2);
        border: 1px solid var(--polar-night-4);
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        height: 100%;
    }
    .metric-card:hover { border-color: var(--frost-4); }
    .metric-label { font-size: 0.85rem; color: var(--snow-storm-1); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
    .metric-value { font-size: 1.8rem; font-weight: 700; color: var(--frost-2); }
    .metric-sub { font-size: 0.8rem; color: var(--aurora-yellow); margin-top: 4px; }

    /* Content Cards */
    .content-card {
        padding: 20px;
        margin-bottom: 20px;
        background-color: var(--polar-night-2); /* Slightly lighter than bg */
        border-radius: 8px; /* Slightly more rounded */
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: 1px solid #4C566A; /* Atlassian subtle border */
    }
    .card-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--snow-storm-2);
        margin-bottom: 15px;
        border-bottom: 1px solid var(--polar-night-4);
        padding-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Tables */
    div[data-testid="stDataFrame"] {
        border: 1px solid var(--polar-night-4);
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Status Box */
    .status-box-track {
        border: 1px solid var(--aurora-green);
        background-color: rgba(163, 190, 140, 0.1);
        color: var(--aurora-green);
        padding: 12px;
        border-radius: 6px;
        text-align: center;
        font-weight: 600;
    }
    .status-box-alert {
        border: 1px solid var(--aurora-red);
        background-color: rgba(191, 97, 106, 0.1);
        color: var(--aurora-red);
        padding: 12px;
        border-radius: 6px;
        text-align: center;
        font-weight: 600;
    }
    
    /* Progress Bar */
    div[data-testid="stProgress"] > div > div { background-color: var(--frost-3) !important; }
    div[data-testid="stProgress"] { background-color: var(--polar-night-1) !important; }

    /* Custom Navigation Tabs (Hide Radio) */
    div[role="radiogroup"] > label > div:first-child {
        display: none;
    }
    div[role="radiogroup"] {
        background-color: transparent;
        gap: 8px;
        display: flex;
        flex-direction: column;
    }
    div[role="radiogroup"] label {
        background-color: transparent;
        border: 1px solid transparent; /* Placeholder for layout stability */
        border-radius: 6px;
        padding-left: 10px;
        padding-right: 10px;
        transition: all 0.2s;
        margin-bottom: 0px !important;
    }
    div[role="radiogroup"] label:hover {
        background-color: var(--polar-night-2);
        color: var(--snow-storm-2);
    }
    /* Active State styling (Streamlit attaches props to the selected one, harder to target pure CSS without :has, 
       but standard Streamlit behavior puts a background on selected radio items if we don't override. 
       We will rely on default highlight or minimal override, but user asked for SPECIFIC active state.
       Since we can't easily target 'checked' radio label parent in pure CSS3 without :has (which is supported in most modern browsers now),
       we'll try :has selector.) */
    
    div[role="radiogroup"] label:has(input:checked) {
        background-color: var(--frost-2) !important;
        color: var(--polar-night-1) !important;
        font-weight: 700; /* Bold for active */
        border: none;
    }
    div[role="radiogroup"] label:has(input:checked) span {
        color: var(--polar-night-1) !important;
    }
    div[role="radiogroup"] label:has(input:checked) p {
        color: var(--polar-night-1) !important;
    }

    /* Primary Button Override (Green for Save) */
    button[kind="primary"] {
        background-color: var(--aurora-green) !important;
        border-color: var(--aurora-green) !important;
        color: var(--polar-night-1) !important;
    }
    button[kind="primary"]:hover {
        background-color: #8FBCBB !important;
        border-color: #8FBCBB !important;
    }

    /* Multiselect Tag Override (Blue/Green instead of Red) */
    span[data-baseweb="tag"] {
        background-color: rgba(136, 192, 208, 0.2) !important; /* Frost Blue Tint */
        border: 1px solid var(--frost-2) !important;
    }
    span[data-baseweb="tag"] span {
        color: var(--snow-storm-2) !important;
    }

    /* Hide Streamlit Deploy Button / Toolbar */
    .stDeployButton { display: none !important; }
    [data-testid="stToolbar"] { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    
</style>
"""
st.markdown(NORD_CSS, unsafe_allow_html=True)

# Session State & Auth Simulation
if 'user' not in st.session_state:
    st.session_state.user = None

# --- AUTH UI ---
def render_auth():
    # check for reset token
    qp = st.query_params
    reset_token = qp.get("reset_token")
    
    if reset_token:
        st.markdown("<h2 style='text-align:center;'>Reset Password 🔐</h2>", unsafe_allow_html=True)
        with st.form("reset_pwd_form"):
            new_pass = st.text_input("New Password", type="password")
            conf_pass = st.text_input("Confirm Password", type="password")
            if st.form_submit_button("Update Password", type="primary"):
                if new_pass != conf_pass:
                    st.error("Passwords do not match")
                elif len(new_pass) < 8:
                     st.error("Password must be 8+ chars")
                else:
                    try:
                        res = httpx.post(f"{API_URL}/auth/reset-password", json={"token": reset_token, "new_password": new_pass})
                        if res.status_code == 200:
                            st.success("Password updated! Please login.")
                            # clear token
                            st.query_params.clear()
                            st.rerun()
                        else:
                            st.error(res.json().get('detail'))
                    except Exception as e:
                        st.error(f"Error: {e}")
        if st.button("Back to Login"):
            st.query_params.clear()
            st.rerun()
        return

    # Normal Auth
    tab1, tab2, tab3 = st.tabs(["Login", "Create Account", "Forgot Password"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", type="primary"):
                try:
                    res = httpx.post(f"{API_URL}/auth/login", json={"email": email, "password": password})
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state.user = data['user']
                        st.session_state.token = data['access_token']
                        st.session_state.user_id = data['user']['id'] # Compat
                        st.success("Welcome back!", icon="👋")
                        st.rerun()
                    else:
                        st.error(res.json().get('detail', "Login failed"))
                except Exception as e:
                    st.error(f"Connection Error: {e}")

    with tab2:
        with st.form("register_form"):
            r_name = st.text_input("Full Name")
            r_email = st.text_input("Email")
            r_pass = st.text_input("Password (min 8 chars)", type="password")
            r_conf = st.text_input("Confirm Password", type="password")
            
            if st.form_submit_button("Create Account"):
                if r_pass != r_conf:
                    st.error("Passwords do not match")
                elif len(r_pass) < 8:
                    st.error("Password too short")
                else:
                    try:
                        payload = {"email": r_email, "password": r_pass, "name": r_name}
                        res = httpx.post(f"{API_URL}/auth/register", json=payload)
                        if res.status_code == 200:
                            st.success("Account created! Please login.")
                        else:
                            st.error(res.json().get('detail', "Registration failed"))
                    except Exception as e:
                        st.error(f"Error: {e}")

    with tab3:
        st.caption("We'll send a mocked link to the backend console.")
        f_email = st.text_input("Enter your email")
        if st.button("Send Reset Link"):
            try:
                res = httpx.post(f"{API_URL}/auth/forgot-password", json={"email": f_email})
                st.info(res.json().get('message'))
            except Exception as e:
                st.error(f"Error: {e}")

# --- HELPERS ---
def fetch_settings(user_id):
    try:
        res = httpx.get(f"{API_URL}/settings", params={"user_id": user_id})
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return {
        "min_daily_hours": 8.0, 
        "office_start_time": "09:00",
        "last_allowed_entry": "10:00",
        "first_half_min_hours": 4.0,
        "effective_date": datetime.now().strftime("%Y-%m-%d"),
        "work_days": "0,1,2,3,4"
    }

def get_month_dates(year, month):
    num_days = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, num_days)
    all_dates = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    return start_date, end_date, all_dates

# --- DIALOGS ---
@st.dialog("Log Correction")
def manual_entry_dialog(default_date=None):
    st.markdown("Update existing logs or add missing days.")
    
    with st.form("manual_entry_form"):
        # If triggered from inline action, pre-fill date
        d_val = default_date if default_date else date.today()
        m_date = st.date_input("Date", value=d_val)
        
        # Type Select first to trigger rerun/disable logic
        m_type = st.selectbox("Day Type", ["working", "half-day", "leave", "holiday"])
        
        # State Lock: Disable inputs if leave/holiday
        is_locked = m_type in ['leave', 'holiday']
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            m_in = st.time_input("Clock In", value=None, disabled=is_locked)
        with col_t2:
            m_out = st.time_input("Clock Out", value=None, disabled=is_locked)
            
        if is_locked and (m_in or m_out):
            st.warning("Switching to Leave/Holiday will clear these times.")
            # We can't auto-clear inputs easily without session state callback or rerun, 
            # but backend validation will block it if user persists.
        
        submitted = st.form_submit_button("Save Record", type="primary")
        if submitted:
            payload = {
                "user_id": st.session_state.user_id,
                "date": str(m_date),
                "day_type": m_type
            }
            # Only send times if not locked (or force None)
            if not is_locked:
                if m_in: payload["clock_in"] = datetime.combine(m_date, m_in).isoformat()
                if m_out: payload["clock_out"] = datetime.combine(m_date, m_out).isoformat()
            
            try:
                res = httpx.post(f"{API_URL}/manual-entry", json=payload)
                if res.status_code == 200:
                    st.success("Entry updated successfully!")
                    st.rerun()
                else:
                    st.error(res.json().get('detail', res.text))
            except Exception as e:
                st.error(str(e))

# --- MAIN APP ---
def main_app():
    if not st.session_state.user:
        render_auth()
        return

    # Authorized Content
    user = st.session_state.user
    settings = fetch_settings(user['id'])
    
    # Sidebar
    with st.sidebar:
        st.markdown("""
        <div style="margin-bottom: 20px;">
            <h2 style='color:#88C0D0; font-weight:800; margin:0;'>Hourline.</h2>
            <div style="font-size: 0.8rem; color: #4C566A;">v2.0 &bull; Secure</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="background-color: #2E3440; padding: 10px; border-radius: 6px; margin-bottom: 20px; border: 1px solid #3B4252;">
            <div style="font-size: 0.75rem; color: #8FBCBB; text-transform: uppercase;">Logged in as</div>
            <div style="font-weight: 600; color: #ECEFF4;">{user['name']}</div>
            <div style="font-size: 0.7rem; color: #4C566A;">{user['email']}</div>
            {'<div style="color: #BF616A; font-weight:bold; font-size: 0.7rem; margin-top:4px;">ADMIN</div>' if user['is_admin'] else ''}
        </div>
        """, unsafe_allow_html=True)

        # Nav
        page = st.radio("Navigate", 
            ["📊 Dashboard", "📅 Monthly History", "⚙️ Configuration"], 
            label_visibility="collapsed"
        )
        
        st.divider()

        # Contextual Actions
        st.markdown("<p style='font-size: 0.8rem; color: #81A1C1; font-weight: 600; text-transform: uppercase;'>Global Actions</p>", unsafe_allow_html=True)
        
        # Check current status for Today to toggle buttons
        # Minimal fetch just for status check could be optimized, but here we can reuse existing state if available.
        # For robustness, we'll let the user click and backend will validate, BUT user asked for "Visual State".
        # We can try to infer from dashboard data if available, or just keeping them generic but clearly distinct.
        # Given the "Hit List" request: "If I am clocked in, 'Clock In' should be disabled"
        # We need to quickly check today's log.
        
        is_clocked_in = False
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            # Quick check - ideally this leads to a dedicated /status endpoint, but re-using stats for now
            status_res = httpx.get(f"{API_URL}/stats?user_id={st.session_state.user_id}&start_date={today_str}&end_date={today_str}")
            if status_res.status_code == 200 and status_res.json():
                idx_log = status_res.json()[0]
                if idx_log.get('clock_in') and not idx_log.get('clock_out'):
                    is_clocked_in = True
        except:
            pass            

        if not is_clocked_in:
            if st.button("Clock In ☀️", type="primary", use_container_width=True):
                try:
                    res = httpx.post(f"{API_URL}/clock-in", json={"user_id": st.session_state.user_id, "timestamp": datetime.now().isoformat()})
                    if res.status_code == 200:
                        st.balloons()
                        st.toast("Clocked In successfully!", icon="✅")
                        st.rerun()
                    else:
                        st.toast(f"Error: {res.json().get('detail')}", icon="❌")
                except Exception as e:
                    st.error(f"Connection Error: {e}")
        else:
            if st.button("Clock Out 🌙", type="primary", use_container_width=True):
                try:
                    res = httpx.post(f"{API_URL}/clock-out", json={"user_id": st.session_state.user_id, "timestamp": datetime.now().isoformat()})
                    if res.status_code == 200:
                            st.toast("Clocked Out successfully!", icon="🏠")
                            st.rerun()
                    else:
                            st.toast(f"Error: {res.json().get('detail')}", icon="❌")
                except Exception as e:
                    st.error(f"Connection Error: {e}")

        # Spacer to push logout to bottom
        st.markdown("<div style='margin-top: auto;'></div>", unsafe_allow_html=True) 
        # Streamlit sidebar doesn't support flex-grow 'auto' easily without custom component, 
        # but we can just add a large gap or divider.
        st.markdown("<br>" * 5, unsafe_allow_html=True)
        st.divider()
        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.token = None
            st.session_state.user_id = None
            st.rerun()

    # Routing
    if "Configuration" in page:
        render_settings(settings)
    elif "Monthly History" in page:
        render_history(settings)
    else:
        render_dashboard(settings, is_clocked_in)

def render_settings(settings):
    st.markdown(f"<h1 style='color:#ECEFF4;'>Configuration</h1>", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">Attendance Rules</div>', unsafe_allow_html=True)
        
        with st.form("settings_form"):
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                new_start = st.time_input("Office Start Time", value=datetime.strptime(settings['office_start_time'], "%H:%M").time())
                new_last = st.time_input("Last Allowed Entry", value=datetime.strptime(settings['last_allowed_entry'], "%H:%M").time())
                new_min = st.number_input("Min Daily Hours", value=float(settings['min_daily_hours']), step=0.5)
            with col_s2:
                new_half = st.number_input("Half Day Min Hours", value=float(settings['first_half_min_hours']), step=0.5)
                
                # Working Days Picker
                DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                current_indices = [int(x) for x in settings.get('work_days', '0,1,2,3,4').split(',') if x]
                default_days = [DAYS[i] for i in current_indices]
                
                selected_days = st.multiselect("Working Days", DAYS, default=default_days)
            
                if st.form_submit_button("Update Settings", type="primary"):
                    # Use standard btn style, overrides will handle Frost Blue
                    pass
                
                    # Convert selected days back to CSV indices
                day_indices = sorted([DAYS.index(d) for d in selected_days])
                work_days_str = ",".join(map(str, day_indices))
                
                payload = {
                    "user_id": st.session_state.user_id,
                    "min_daily_hours": new_min,
                    "office_start_time": new_start.strftime("%H:%M"),
                    "last_allowed_entry": new_last.strftime("%H:%M"),
                    "first_half_min_hours": new_half,
                    "effective_date": datetime.now().strftime("%Y-%m-%d"),
                    "work_days": work_days_str
                }
                try:
                    res = httpx.post(f"{API_URL}/settings", json=payload)
                    if res.status_code == 200:
                        st.success("Settings updated!", icon="💾")
                        st.rerun()
                    else:
                        st.error("Failed to update.")
                except Exception as e:
                    st.error(f"Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

def render_history(settings):
    # Session State for Month Navigation (Independent or Shared? Let's share for continuity)
    if 'view_date' not in st.session_state:
        st.session_state.view_date = date.today()
    
    start_date, end_date, all_dates_in_month = get_month_dates(st.session_state.view_date.year, st.session_state.view_date.month)

            # Top Bar
    col_nav1, col_nav2, col_nav3 = st.columns([1, 4, 1])
    with col_nav1:
        if st.button("←", key="hist_prev"):
             prev = st.session_state.view_date.replace(day=1) - timedelta(days=1)
             st.session_state.view_date = prev
             st.rerun()
    with col_nav2:
        st.markdown(f"<h2 style='text-align:center; margin:0; color:#ECEFF4;'>{st.session_state.view_date.strftime('%B %Y')}</h2>", unsafe_allow_html=True)
    with col_nav3:
         if st.button("→", key="hist_next"):
             curr = st.session_state.view_date.replace(day=1)
             next_m = (curr + timedelta(days=32)).replace(day=1)
             st.session_state.view_date = next_m
             st.rerun()
    
    # Toggle for Future Dates
    show_future = st.toggle("Show Future Dates", value=False)
    
    st.divider()

    try:
        res = httpx.get(f"{API_URL}/stats", params={
            "user_id": st.session_state.user_id,
            "start_date": str(start_date), 
            "end_date": str(end_date)
        })
        
        if res.status_code == 200:
            data = res.json()
            api_logs = {log['date']: log for log in data}
            
            # Merge
            full_data = []
            for d in all_dates_in_month:
                d_str = str(d)
                if d_str in api_logs:
                    full_data.append(api_logs[d_str])
                else:
                    full_data.append({
                        "date": d_str, 
                        "day_type": None, 
                        "clock_in": None, 
                        "clock_out": None, 
                        "worked_minutes": 0, 
                        "late_status": None
                    })
            
            display_df = pd.DataFrame(full_data)
            display_df['date_obj'] = pd.to_datetime(display_df['date'])
            # User feedback: "Default to ascending order"
            display_df = display_df.sort_values('date_obj', ascending=True)

            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            
            # Use columns for header layout
            h_col1, h_col2 = st.columns([3, 1])
            with h_col1:
                st.markdown('<div class="card-header" style="border:none; margin:0;">Daily Logs</div>', unsafe_allow_html=True)
            with h_col2:
                if st.button("➕ Log Correction", key="add_log_btn_hist", use_container_width=True):
                    manual_entry_dialog()
            
            st.markdown('<hr style="margin-top:5px; margin-bottom:15px; border-color:#4C566A;">', unsafe_allow_html=True)

            # Grid
            grid_header = st.columns([2, 2, 2, 2, 2, 2])
            grid_header[0].markdown("**Date**")
            grid_header[1].markdown("**Type**")
            grid_header[2].markdown("**In**")
            grid_header[3].markdown("**Out**")
            grid_header[4].markdown("**Hours**")
            grid_header[5].markdown("**Action**")
            st.divider()
            
            today = date.today()

            for idx, row in display_df.iterrows():
                d_obj = datetime.strptime(row['date'], "%Y-%m-%d")
                d_val = d_obj.date()
                is_future = d_val > today

                # Filter Future Logic
                if is_future and not show_future:
                    continue
                
                r_col = st.columns([2, 2, 2, 2, 2, 2])
                d_disp = d_obj.strftime("%b %d")
                
                # Dim styling for future rows if shown
                opacity_style = "opacity: 0.5;" if is_future else ""
                
                r_col[0].markdown(f"<span style='{opacity_style}'>{d_disp}</span>", unsafe_allow_html=True)
                
                if row['day_type']:
                    r_col[1].write(row['day_type'])
                    c_in = pd.to_datetime(row['clock_in']).strftime('%I:%M %p') if row['clock_in'] else "--:--"
                    c_out = pd.to_datetime(row['clock_out']).strftime('%I:%M %p') if row['clock_out'] else "--:--"
                    hrs = f"{(row['worked_minutes'] / 60):.1f}h" if row['worked_minutes'] else "0.0h"
                    r_col[2].write(c_in)
                    r_col[3].write(c_out)
                    r_col[4].write(hrs)
                    r_col[5].text("✅")
                else:
                        d_val = datetime.strptime(row['date'], "%Y-%m-%d").date()
                        is_future = d_val > date.today()
                        
                        r_col[1].markdown(f"*{'Future' if is_future else 'Missing'}*")
                        r_col[2].write("--")
                        r_col[3].write("--")
                        r_col[4].write("--")
                        
                        if not is_future:
                            if r_col[5].button("Add Log", key=f"add_hist_{row['date']}", help=f"Add missing log for {d_disp}"):
                                manual_entry_dialog(default_date=d_obj.date())
                        else:
                            r_col[5].text("🔒")
            st.markdown('</div>', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Error: {e}")

def render_dashboard(settings, is_active_session=False):
    # Session State for Month Navigation
    if 'dash_view_date' not in st.session_state:
        st.session_state.dash_view_date = date.today()
        
    start_date, end_date, all_dates_in_month = get_month_dates(st.session_state.dash_view_date.year, st.session_state.dash_view_date.month)
    
    # Active Session Banner
    if is_active_session and st.session_state.dash_view_date.month == date.today().month:
        st.markdown("""
        <div style="background-color: rgba(163, 190, 140, 0.15); border: 1px solid #A3BE8C; border-radius: 8px; padding: 15px; margin-bottom: 25px; display: flex; align-items: center; gap: 15px;">
            <div style="font-size: 1.5rem;">🟢</div>
            <div>
                <div style="color: #A3BE8C; font-weight: 700; font-size: 1.05rem;">Active Session in Progress</div>
                <div style="color: #ECEFF4; font-size: 0.9rem; opacity: 0.9;">You are currently clocked in. Duration is updating live above.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom: 24px;">
        <div>
            <h1 style="margin:0; font-weight:800; color:#ECEFF4;">Dashboard</h1>
            <p style="margin:0; opacity:0.7; font-size:1.1rem; color:#D8DEE9;">{st.session_state.dash_view_date.strftime('%B %Y')}</p>
        </div>
        <button style="background:transparent; border:1px solid #4C566A; color:#88C0D0; padding:8px 16px; border-radius:6px; cursor:pointer; font-family:Inter; font-weight:600;" onclick="window.location.reload();">Refresh Data</button>
    </div>
    """, unsafe_allow_html=True)

    # Removed Ghost Refresh Button

    try:
        # Fetch Stats
        res = httpx.get(f"{API_URL}/stats", params={
            "user_id": st.session_state.user_id,
            "start_date": str(start_date), 
            "end_date": str(end_date)
        })
        
        if res.status_code == 200:
            data = res.json()
            df = pd.DataFrame(data)
            
            # Logic: Calculate 'Active' Minutes for Today if Clocked In
            # We need to find today's row in DF.
            today_str = date.today().strftime("%Y-%m-%d")
            
            # Helper to recalc worked minutes
            def recalc_minutes(row):
                if row['date'] == today_str and row['clock_in'] and not row['clock_out']:
                    # It's ongoing
                    cin = pd.to_datetime(row['clock_in'])
                    now = datetime.now()
                    diff = (now - cin).total_seconds() / 60
                    return diff
                return row['worked_minutes'] if pd.notnull(row['worked_minutes']) else 0

            if not df.empty:
                df['worked_minutes'] = df.apply(recalc_minutes, axis=1)

            total_worked = df['worked_minutes'].sum() / 60 if 'worked_minutes' in df.columns else 0
            weekdays = sum(1 for d in all_dates_in_month if d.weekday() < 5)
            required_hours = weekdays * settings['min_daily_hours']
            
            late_count = len(df[df['late_status'] == 'late']) if 'late_status' in df.columns else 0
            pending_logs = len(df[df['worked_minutes'].isna() & (df['day_type'] == 'working')]) if 'worked_minutes' in df.columns else 0
            catch_up = 0
            
            remaining_days = 0
            today = date.today()
            if start_date <= today <= end_date:
                remaining_days = sum(1 for d in all_dates_in_month if d > today and d.weekday() < 5)
            elif today < start_date:
                remaining_days = weekdays
            
            if remaining_days > 0:
                 catch_up = max(0, (required_hours - total_worked) / remaining_days)

            # Metrics with Hierarchy & Tooltips & Smart Zero States
            # Total Hours is "Star Metric" - larger card
            
            # Logic for Smart Text
            late_text = f"{late_count}"
            if late_count == 0:
                late_text += ' <span style="font-size:0.8rem; color:#A3BE8C;">(Perfect!)</span>'
            
            pending_text = f"{pending_logs}"
            if pending_logs == 0:
                 pending_text = '<span style="color:#A3BE8C;">All set</span>'
            
            st.markdown(f"""
            <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                <div class="metric-card" style="border-left: 4px solid #88C0D0;" title="Total hours accumulated this month against your target.">
                    <div class="metric-label" style="font-size:1.1rem; color:#ECEFF4;">Total Hours</div>
                    <div class="metric-value" style="font-size:2.5rem;">{total_worked:.1f}<span style="font-size:1.2rem;color:#81A1C1;">h</span></div>
                    <div class="metric-sub" style="font-size:1rem;">Target: {required_hours}h</div>
                </div>
                <div class="metric-card" title="Number of days you arrived after office start time.">
                    <div class="metric-label">Late Arrivals</div>
                    <div class="metric-value" style="color:{'#D08770' if late_count > 0 else '#A3BE8C'};">{late_text}</div>
                    <div class="metric-sub">Count</div>
                </div>
                <div class="metric-card" title="Days where you are clocked in but missing a clock out, or incomplete logs.">
                    <div class="metric-label">Pending Logs</div>
                    <div class="metric-value" style="color:{'#EBCB8B' if pending_logs > 0 else '#ECEFF4'};">{pending_text}</div>
                    <div class="metric-sub">Action Req</div>
                </div>
                <div class="metric-card" title="Hours per day needed for remaining working days to meet the monthly target.">
                    <div class="metric-label">Catch Up</div>
                    <div class="metric-value">{catch_up:.1f}<span style="font-size:1rem;color:#4C566A;">h</span></div>
                    <div class="metric-sub">Daily Req</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.write("")

            # Minimal Dashboard Content (Action + Status)
            main_c1, main_c2 = st.columns([2, 1])
            
            with main_c1:
                st.markdown('<div class="content-card">', unsafe_allow_html=True)
                st.markdown('<div class="card-header">Activity Snapshot</div>', unsafe_allow_html=True)
                if not df.empty:
                    recent = df.sort_values('date', ascending=False).head(5).copy()
                    # Human Readable Timestamps
                    if 'clock_in' in recent.columns:
                        recent['clock_in'] = pd.to_datetime(recent['clock_in'], format='mixed', errors='coerce').dt.strftime('%b %d, %I:%M %p').fillna('--')
                    
                    st.dataframe(
                        recent[['date', 'day_type', 'clock_in', 'worked_minutes']],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "clock_in": "In Time",
                            "worked_minutes": st.column_config.NumberColumn("Mins"),
                        }
                    )
                    if st.button("View Full Monthly History →"):
                         st.info("Select 'Monthly History' in sidebar for full details.")
                else:
                    st.info("No activity this month.")
                st.markdown('</div>', unsafe_allow_html=True)

            with main_c2:
                st.markdown('<div class="content-card">', unsafe_allow_html=True)
                st.markdown('<div class="card-header">Status Overview</div>', unsafe_allow_html=True)
                
                # Dynamic Logic
                # Red IF: Late Count > 3 OR Catch Up > 2 hours
                is_critical = late_count > 3 or (catch_up > 2.0 and remaining_days > 0)
                
                if is_critical:
                     st.markdown('<div class="status-box-alert">⚠️ Needs Attention</div>', unsafe_allow_html=True)
                     if late_count > 3:
                         st.markdown(f"<p style='margin-top:10px; font-size:0.9rem; text-align:center; color:#BF616A;'>High late frequency.</p>", unsafe_allow_html=True)
                     elif catch_up > 2.0:
                         st.markdown(f"<p style='margin-top:10px; font-size:0.9rem; text-align:center; color:#BF616A;'>Catch-up load is high.</p>", unsafe_allow_html=True)
                else:
                     st.markdown('<div class="status-box-track" style="border-color:#88C0D0; color:#88C0D0; background-color:rgba(136, 192, 208, 0.1);">ℹ️ All Good</div>', unsafe_allow_html=True)
                     st.markdown(f"<p style='margin-top:10px; font-size:0.9rem; text-align:center; color:#8FBCBB;'>You are on track.</p>", unsafe_allow_html=True)
                
                st.markdown("""
                <div style="margin-top:30px; border-top:1px solid #3B4252; padding-top:15px;">
                    <p style="font-size:0.85rem; color:#81A1C1; font-weight:600; text-transform:uppercase;">Quick Rules</p>
                    <ul style="font-size:0.8rem; color:#D8DEE9; padding-left:20px; line-height:1.6;">
                """, unsafe_allow_html=True)
                st.markdown(f"<li>Late after <span style='color:#EBCB8B;'>{settings['last_allowed_entry']}</span></li>", unsafe_allow_html=True)
                st.markdown(f"<li>Half-day: {settings['first_half_min_hours']}h</li>", unsafe_allow_html=True)
                st.markdown("""
                        <li>Clock-out: <span style='color:#A3BE8C;'>Same Day</span></li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        else:
            st.error("Could not fetch data.")
            
    except Exception as e:
        st.error(f"Backend Error: {e}")

# Run
if st.session_state.user_id:
    main_app()
else:
    login_screen()
