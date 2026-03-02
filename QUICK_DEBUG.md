# Quick Backend Connection Debug

## Immediate Steps to Diagnose

### 1. Check Browser Console (Right Now)

1. Open your Vercel app: `https://your-app.vercel.app`
2. Press **F12** (or Right-click → Inspect)
3. Go to **Console** tab
4. Look for these messages:

```
🔗 API Base URL: https://your-backend-url.com
```

**If you see:**
- `🔗 API Base URL: (empty - using proxy in dev)` → Environment variable not set
- `🔗 API Base URL: https://...` → Good! Variable is set
- `⚠️ REACT_APP_API_URL is not set!` → Variable missing

### 2. Check the Debug Widget

After deploying the latest code, you'll see a **debug widget** in the bottom-right corner showing:
- ✅ Connected (green) - Backend is reachable
- ⚠️ Connection Issue (orange) - Backend responds but with errors
- ❌ Cannot Connect (red) - Backend unreachable

### 3. Test Backend Directly

Open these URLs in a new browser tab:

**Health Check:**
```
https://your-backend-url.com/health
```

**Expected Response:**
```json
{"status":"ok","service":"Resume Generator API","timestamp":"..."}
```

**If you get:**
- ✅ JSON response → Backend is working
- ❌ Error/CORS → Backend CORS issue
- ❌ 404 → Wrong URL
- ❌ Timeout → Backend is down

### 4. Check Network Tab

1. In DevTools, go to **Network** tab
2. Try to generate a resume
3. Look for the API request (should be `/api/generate`)
4. Click on it
5. Check:
   - **Request URL**: Full URL being called
   - **Status Code**: What error?
   - **Response**: Error message

### 5. Common Issues Quick Fix

| Error | Cause | Fix |
|-------|-------|-----|
| CORS error | Backend doesn't allow Vercel domain | Add Vercel URL to backend `CORS_ORIGINS` |
| Network Error | Backend URL wrong or backend down | Check `REACT_APP_API_URL` value, test backend directly |
| 404 Not Found | Wrong endpoint path | Verify backend has `/api/generate` endpoint |
| 503 Service Unavailable | Backend sleeping/starting | Wake up backend on Render |
| Empty API URL | Env var not set | Set `REACT_APP_API_URL` in Vercel and redeploy |

### 6. Verify Environment Variable Format

**Correct:**
```
REACT_APP_API_URL=https://resume-api.onrender.com
```

**Wrong:**
```
REACT_APP_API_URL=https://resume-api.onrender.com/  ← No trailing slash!
REACT_APP_API_URL=http://resume-api.onrender.com   ← Should be https
REACT_APP_API_URL=resume-api.onrender.com          ← Missing protocol
```

### 7. Verify Backend CORS

**Backend `CORS_ORIGINS` should be:**
```
https://your-app.vercel.app,http://localhost:3000
```

**Common mistakes:**
- Missing Vercel domain
- Trailing slashes
- Spaces around commas
- Using `*` with credentials (not allowed)

### 8. Quick Test Commands

**Test backend health:**
```bash
curl https://your-backend-url.com/health
```

**Test CORS (from browser console):**
```javascript
fetch('https://your-backend-url.com/health')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)
```

## What to Share for Help

If still not working, share:

1. **Browser Console Output** - Screenshot of console
2. **Network Tab** - Screenshot of failed request
3. **Backend URL** - Your backend URL
4. **Vercel URL** - Your Vercel app URL
5. **Backend CORS_ORIGINS** - Current value (without sensitive data)
6. **Error Message** - Exact error text

## Next Steps

After deploying the latest code:
1. Check the debug widget (bottom-right)
2. Check browser console for detailed logs
3. Follow the steps in `DEBUG_BACKEND.md` for comprehensive troubleshooting
