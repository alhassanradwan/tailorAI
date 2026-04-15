# AdaptiveAI - Setup & Installation Guide

## Prerequisites
- **Python 3.11** (3.11.x required — 3.12+ / 3.14 cause MongoDB TLS and Pydantic errors)
- MongoDB (local or MongoDB Atlas)
- Groq API key
- Modern web browser

## Backend Setup

### 1. Create Virtual Environment (Python 3.11)

> **Important:** The project requires Python 3.11. Python 3.14 causes MongoDB Atlas TLS handshake failures.

```powershell
cd backend

# Remove old venv if it exists (created with wrong Python version)
if (Test-Path ./venv) { Remove-Item -Recurse -Force ./venv }

# Create new venv with Python 3.11
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the `backend` folder:

```env
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/
DATABASE_NAME=adaptiveai

# Groq API
GROQ_API_KEY=your-groq-api-key-here

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-here-change-this

# Admin Credentials
ADMIN_EMAIL=hassangrdwan@gmail.com
ADMIN_PASSWORD=Z3bola3251

# Server Configuration
FLASK_ENV=development
FLASK_DEBUG=True
```

**Important**: Replace `your-groq-api-key-here` with your actual Groq API key.

**Security**: Change `JWT_SECRET_KEY` to a random secure string for production.

### 3. Start MongoDB
Make sure MongoDB is running:

**Option A: Local MongoDB**
```powershell
# Start MongoDB service
net start MongoDB
```

**Option B: MongoDB Atlas**
1. Create account at https://www.mongodb.com/cloud/atlas
2. Create a cluster
3. Get connection string
4. Update `MONGODB_URI` in `.env` file

### 4. Run Backend Server
```powershell
cd backend
python app.py
```

Backend will start on: `http://localhost:5000`

## Frontend Setup (React)

```powershell
cd frontend-react
npm install
npm run dev
```

Frontend will run at: `http://localhost:5173`

## Verify Installation

### 1. Check Backend
Open browser to `http://localhost:5000`:

Should see:
```json
{
  "message": "AdaptiveAI Backend API",
  "status": "running",
  "version": "1.0.0",
  "endpoints": {
    "auth": "/api/auth (login, signup, refresh, logout)",
    "profile": "/api/profile (user profiles)",
    "chat": "/api/chat (AI agent interactions)",
    "analytics": "/api/analytics (quiz data, progress)",
    "context": "/api/context (user state management)"
  }
}
```

### 2. Check Frontend
Open `http://localhost:5173`

Should see:
- React app with Login/Sign Up flow
- Navigation and chat routes
- Space-themed UI

### 3. Test Authentication
1. Click "Sign Up" tab
2. Enter:
   - Name: Test User
   - Email: test@example.com
   - Password: test123
   - Confirm Password: test123
3. Click "Start Your Journey"
4. Should navigate to onboarding

### 4. Test Session Persistence
1. Complete onboarding
2. Start quiz, answer 2-3 questions
3. Refresh the page
4. Should restore to exact question you were on
5. Chat messages should also persist

### 5. Test Admin Access
1. Logout (if logged in)
2. Login with:
   - Email: `hassangrdwan@gmail.com`
   - Password: `Z3bola3251`
3. Admin link should appear in navigation
4. Click "Admin Panel"
5. Should see user management dashboard

## MongoDB Collections

After first use, verify these collections exist:

```powershell
# Connect to MongoDB
mongo

# Use database
use adaptiveai

# List collections
show collections
```

Expected collections:
- `users` - User accounts
- `sessions` - Active sessions
- `contexts` - User state (quiz, chat, onboarding)
- `analytics` - Quiz analytics
- `interactions` - Chat history

## Troubleshooting

### Backend won't start

**Error: "ModuleNotFoundError: No module named 'flask'"**
```powershell
pip install -r requirements.txt
```

**Error: "Connection refused" / MongoDB error**
- Start MongoDB service: `net start MongoDB`
- Or update `MONGODB_URI` to point to MongoDB Atlas

**Error: Groq authentication / model access**
- Check `GROQ_API_KEY` in `.env` file
- Verify key is valid in your Groq account

### Frontend won't connect to backend

**Error: "Failed to fetch" in browser console**
1. Check backend is running on port 5000
2. Check CORS is enabled in `backend/app.py`
3. Verify frontend API base URL resolves to `http://localhost:5000/api`

**Error: 401 Unauthorized**
- Tokens may be expired
- Logout and login again
- Clear localStorage: `localStorage.clear()`

### Session not persisting

**Page refresh loses state**
1. Open browser DevTools → Console
2. Look for errors in `checkSession()` or `loadContext()`
3. Verify tokens in Application → localStorage
4. Check network tab for `/api/context/load` request

**Auto-save not working**
1. Check browser console for `saveContext()` errors
2. Verify MongoDB contexts collection exists
3. Check backend logs for context save errors

### Admin panel not accessible

**Admin link not showing**
- Must login with exact email: `hassangrdwan@gmail.com`
- Password must be: `Z3bola3251`
- Check `localStorage.getItem('admin_auth')` in console

**403 Forbidden on admin routes**
- Verify `is_admin` claim in JWT token
- Check backend `ADMIN_EMAIL` config matches

## Development

### Backend Development
```powershell
# Run with auto-reload
cd backend
python app.py
```

Changes to Python files automatically reload the server.

### Frontend Development
With Live Server, changes to HTML/CSS/JS files automatically refresh the browser.

### View Logs

**Backend logs**
- Check terminal where `python app.py` is running
- Look for request logs, errors, warnings

**Frontend logs**
- Open browser DevTools → Console
- Look for API calls, state changes, errors

**MongoDB logs**
```powershell
# View recent logs
Get-Content "C:\Program Files\MongoDB\Server\<version>\log\mongod.log" -Tail 50
```

## Testing Session Management

### Test 1: Token Lifecycle
1. Login as test user
2. Open DevTools → Application → localStorage
3. Verify `access_token` and `refresh_token` exist
4. Copy access token
5. Decode at https://jwt.io
6. Verify expiry is 8 hours from now
7. Logout
8. Tokens should be removed

### Test 2: Context Persistence
1. Login
2. Complete onboarding
3. Answer 5 quiz questions
4. Send 3 chat messages
5. Refresh page
6. All state should restore:
   - Quiz at question 6
   - Chat messages visible
   - Score preserved

### Test 3: Auto-Save
1. Login
2. Start quiz
3. Wait 30 seconds
4. Check Network tab
5. Should see POST to `/api/context/save` every 30s

### Test 4: Multi-Device (Advanced)
1. Login on Computer A
2. Answer 5 quiz questions
3. Login on Computer B (same account)
4. Should load same progress (question 6)
5. Answer question 6 on Computer B
6. Refresh Computer A
7. Should show question 7

## Production Deployment

### Environment Variables
Update `.env` for production:
```env
FLASK_ENV=production
FLASK_DEBUG=False
JWT_SECRET_KEY=<random-64-char-string>
MONGODB_URI=<atlas-connection-string>
```

### Backend (Heroku/Railway)
```powershell
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn app:app
```

### Frontend (Netlify/Vercel)
Set frontend environment/config to call:
`https://your-backend-url.com/api`

### Security Checklist
- [ ] Change JWT_SECRET_KEY
- [ ] Use environment variables for secrets
- [ ] Enable HTTPS
- [ ] Use MongoDB Atlas with authentication
- [ ] Rotate Groq API key regularly
- [ ] Set secure CORS origins
- [ ] Enable rate limiting
- [ ] Add request logging

## API Documentation

Full API documentation available at:
- Session Management: [SESSION_MANAGEMENT.md](SESSION_MANAGEMENT.md)
- Endpoints: Check backend `app.py` for routes

## Support

For issues or questions:
1. Check [SESSION_MANAGEMENT.md](SESSION_MANAGEMENT.md)
2. Review console logs (frontend and backend)
3. Check MongoDB collections
4. Verify environment variables
5. Test with fresh login

## Quick Reference

### Ports
- Backend: `5000`
- Frontend: `5500`
- MongoDB: `27017`

### URLs
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:5000/api`
- Admin Panel: `http://localhost:5173/admin`

### Credentials
- Admin Email: `hassangrdwan@gmail.com`
- Admin Password: `Z3bola3251`
- Test User: Any email/password combo

### Key Directories
- Backend: `c:\Users\Lenovo\Desktop\AdaptiveAI\tailorAI\backend`
- Frontend: `c:\Users\Lenovo\Desktop\AdaptiveAI\tailorAI\frontend-react`

## Active and Legacy API Notes

### Active chat route
- `POST /api/chat/groq`

### Legacy chat route (disabled)
- `POST /api/chat/message` returns `410`

### Active analytics routes
- `GET /api/analytics/summary`
- `GET /api/analytics/mastery-map`
- `GET /api/analytics/misconceptions`
- `GET /api/analytics/engagement`

### Legacy analytics routes (disabled)
- `POST /api/analytics/save` returns `410`
- `GET /api/analytics/user/<email>` returns `410`
- `GET /api/analytics/progress/<email>` returns `410`
- `POST /api/analytics/webhook/n8n` returns `410`

### MongoDB
- Database: `adaptiveai`
- Collections: `users`, `sessions`, `contexts`, `analytics`, `interactions`

---

**Ready to go!** Follow the setup steps above, then test the session management features. Your graduation project is now fully functional with 8-hour JWT sessions and complete context persistence! 🚀
