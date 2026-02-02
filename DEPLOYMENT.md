# Hourline Deployment Guide

## Prerequisites
- GitHub account (for code hosting)
- Supabase account
- Render account
- Streamlit Cloud account

## Step 1: Database Setup (Supabase)

### 1.1 Create Tables
1. Go to your Supabase project: https://tdxduzktqcjbcbtldidb.supabase.co
2. Navigate to **SQL Editor**
3. Copy the contents of `backend/schema.sql`
4. Execute the SQL script

### 1.2 Verify Tables
Run this query to confirm all tables exist:
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';
```

You should see: `users`, `password_reset_tokens`, `attendance_logs`, `user_settings`

---

## Step 2: Backend Deployment (Render)

### 2.1 Push Code to GitHub
```bash
git add .
git commit -m "feat: Supabase migration complete"
git push origin main
```

### 2.2 Create Render Web Service
1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New** → **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `hourline-backend`
   - **Region**: Choose closest to your users
   - **Branch**: `main`
   - **Root Directory**: Leave empty (or `.` if needed)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

### 2.3 Environment Variables
Add these in Render's **Environment** section:

| Key | Value |
|-----|-------|
| `SUPABASE_URL` | `https://tdxduzktqcjbcbtldidb.supabase.co` |
| `SUPABASE_KEY` | `sb_secret_eNmKLfPdGrzDT9Jlmnce7Q_8MPWkMmq` |
| `SECRET_KEY` | Generate a secure random string (e.g., `openssl rand -hex 32`) |
| `PYTHON_VERSION` | `3.11` (optional, recommended) |

### 2.4 Deploy
- Click **Create Web Service**
- Wait for deployment (5-10 minutes)
- Backend URL: `https://hourline.onrender.com`

---

## Step 3: Frontend Deployment (Streamlit Cloud)

### 3.1 Prepare Repository
Ensure `frontend/app.py` is the main file.

### 3.2 Deploy to Streamlit Cloud
1. Go to [Streamlit Cloud](https://share.streamlit.io/)
2. Click **New app**
3. Select your GitHub repo
4. Configure:
   - **Main file path**: `frontend/app.py`
   - **Python version**: `3.11`

### 3.3 Environment Variables (Secrets)
In Streamlit Cloud, add this to the **Secrets** section:
```toml
API_URL = "https://hourline.onrender.com"
```

### 3.4 Deploy
- Click **Deploy**
- Your app will be live at: `https://hourline.streamlit.app`

---

## Step 4: Testing

### 4.1 Create Test Account
1. Go to your Streamlit app
2. Click **Create Account** tab
3. Register with `tauhidur.sifat@gmail.com` (auto-admin)

### 4.2 Verify Features
- ✅ Login works
- ✅ Clock In/Out
- ✅ Manual Entry
- ✅ Monthly History
- ✅ Settings persist

**Live App**: https://hourline.streamlit.app

---

## Common Deployment Errors

### Error: "Port scan timeout reached, no open ports detected"

**Cause**: The app isn't starting properly or crashing before binding to the port.

**Solutions**:

1. **Check Render Logs**:
   - Go to your service in Render Dashboard
   - Click on **Logs** tab
   - Look for Python errors (import errors, missing modules, etc.)

2. **Verify Build Command**:
   - Should be: `pip install -r requirements.txt`
   - Make sure `requirements.txt` includes ALL dependencies

3. **Verify Start Command**:
   - Should be: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - Note: Must use `$PORT` (Render's environment variable)

4. **Check Environment Variables**:
   - Ensure `SUPABASE_URL` and `SUPABASE_KEY` are set
   - Missing env vars can cause import errors

5. **Test Locally First**:
   ```bash
   PORT=8000 uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   ```
   - If this fails locally, fix the error before deploying

6. **Common Import Errors**:
   - Check that `python-dotenv` is in `requirements.txt`
   - Verify all relative imports work (`from .db import ...`)

---

## Troubleshooting

### Backend Issues
- **500 Error**: Check Render logs at https://dashboard.render.com
- **Connection Refused**: Verify `SUPABASE_URL` and `SUPABASE_KEY`
- **Slow Response**: Render free tier spins down after inactivity (cold start ~30s)
- **Test Backend**: Visit https://hourline.onrender.com/docs to see API docs

### Frontend Issues
- **Can't Connect**: Verify `API_URL` in Streamlit secrets matches Render URL
- **CORS Error**: FastAPI should auto-handle, but check browser console

### Database Issues
- **"relation does not exist"**: Run `backend/schema.sql` in Supabase SQL Editor
- **Auth fails**: Check password hashing (bcrypt should work cross-platform)

---

## Local Development (Post-Migration)

Update your `.env`:
```env
SUPABASE_URL=https://tdxduzktqcjbcbtldidb.supabase.co
SUPABASE_KEY=sb_secret_eNmKLfPdGrzDT9Jlmnce7Q_8MPWkMmq
SECRET_KEY=local-dev-secret-key
```

Run:
```bash
# Backend
uvicorn backend.main:app --reload --port 8000

# Frontend (in another terminal)
streamlit run frontend/app.py
```

Frontend will use `http://127.0.0.1:8000` by default (from `os.getenv("API_URL")`).

---

## Security Notes
> [!CAUTION]
> - Never commit `.env` to Git (already in `.gitignore`)
> - Rotate `SECRET_KEY` in production periodically
> - Use Supabase **Service Role** key (not Anon key) in backend
