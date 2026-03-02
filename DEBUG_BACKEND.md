# Backend Connection Debugging Guide

## Step-by-Step Debugging Process

### 1. Check Environment Variable in Vercel

**In Vercel Dashboard:**
1. Go to **Settings** → **Environment Variables**
2. Verify `REACT_APP_API_URL` exists
3. Check the value - should be your backend URL (e.g., `https://your-backend.onrender.com`)
4. **IMPORTANT**: No trailing slash! Should be `https://api.example.com` NOT `https://api.example.com/`
5. Verify it's applied to **Production**, **Preview**, and **Development**

**After changing:**
- **Redeploy** your Vercel app (environment variables are baked into the build)

### 2. Check Browser Console

**Open your Vercel app and check browser console:**

1. Open DevTools (F12 or Right-click → Inspect)
2. Go to **Console** tab
3. Look for:
   - `🔗 API Base URL: https://your-backend-url.com` (should show your backend URL)
   - `✅ Backend health check passed` or `❌ Backend health check failed`
   - Any CORS errors (red text)
   - Any network errors

### 3. Check Network Tab

**In DevTools → Network tab:**

1. Try to generate a resume
2. Look for failed requests (red)
3. Click on the failed request
4. Check:
   - **Request URL**: Should be your backend URL + `/api/generate`
   - **Status**: What error code? (CORS, 404, 500, etc.)
   - **Response**: What error message?

### 4. Test Backend Directly

**Test if backend is accessible:**

1. Open a new tab
2. Go to: `https://your-backend-url.com/health`
3. Should see: `{"status":"ok","service":"Resume Generator API",...}`
4. If you get an error, backend is down or URL is wrong

### 5. Check CORS Configuration

**Backend CORS must include your Vercel domain:**

1. Go to your backend (Render dashboard)
2. **Settings** → **Environment Variables**
3. Check `CORS_ORIGINS` value
4. Should include: `https://your-app.vercel.app`
5. Format: `https://your-app.vercel.app,http://localhost:3000` (comma-separated, no spaces around commas)

**Common CORS issues:**
- Missing Vercel domain in CORS_ORIGINS
- Trailing slash in URL
- HTTP vs HTTPS mismatch
- Wildcard `*` with credentials (not allowed)

### 6. Verify Backend is Running

**Check backend status:**

1. Go to Render dashboard
2. Check if service is **Running** (not Sleeping)
3. Check logs for any errors
4. If sleeping, wake it up or check auto-sleep settings

### 7. Test API Endpoints

**Test each endpoint manually:**

```bash
# Health check
curl https://your-backend-url.com/health

# Test generate endpoint (should return error without files, but should connect)
curl -X POST https://your-backend-url.com/api/generate \
  -F "job_description=test" \
  -F "files=@test.pdf"
```

### 8. Common Issues & Solutions

#### Issue: "CORS policy" error in console
**Solution:**
- Add Vercel domain to backend `CORS_ORIGINS`
- Format: `https://your-app.vercel.app,http://localhost:3000`
- Redeploy backend

#### Issue: "Network Error" or "ERR_NETWORK"
**Solution:**
- Backend URL might be wrong
- Backend might be down
- Check backend URL in Vercel env vars (no trailing slash)
- Test backend URL directly in browser

#### Issue: "404 Not Found"
**Solution:**
- API endpoint path might be wrong
- Check if backend has `/api/generate` endpoint
- Verify backend is deployed correctly

#### Issue: "503 Service Unavailable"
**Solution:**
- Backend might be sleeping (Render free tier)
- Backend might be starting up
- Check Render logs

#### Issue: Environment variable not working
**Solution:**
- Must start with `REACT_APP_` prefix
- Must redeploy after adding/changing
- Check it's applied to correct environment (Production)

### 9. Quick Diagnostic Checklist

- [ ] `REACT_APP_API_URL` set in Vercel (no trailing slash)
- [ ] Vercel app redeployed after setting env var
- [ ] Backend URL accessible in browser (`/health` endpoint works)
- [ ] Backend CORS includes Vercel domain
- [ ] Backend is running (not sleeping)
- [ ] Browser console shows correct API URL
- [ ] No CORS errors in browser console
- [ ] Network tab shows requests going to correct URL

### 10. Get Detailed Error Info

**After deploying the latest code, check:**

1. Open your Vercel app
2. Open browser console
3. Look for detailed error logs:
   - `❌ API Error:` with full details
   - URL being called
   - Error code and message
4. Share these logs for further debugging

## Still Not Working?

If all above checks pass but still getting errors:

1. **Check Vercel build logs** - ensure env var is included in build
2. **Check backend logs** - see if requests are reaching backend
3. **Try different browser** - rule out browser extensions
4. **Check firewall/proxy** - corporate networks might block
5. **Contact support** with:
   - Backend URL
   - Vercel domain
   - Browser console errors
   - Network tab screenshots
