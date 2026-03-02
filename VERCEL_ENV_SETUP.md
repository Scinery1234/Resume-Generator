# Fix: "Could not reach the server" Error on Vercel

## The Problem
Your frontend deployed on Vercel can't connect to your backend API because the `REACT_APP_API_URL` environment variable is not set.

## Quick Fix

### Step 1: Set Environment Variable in Vercel

1. Go to your **Vercel Dashboard**
2. Open your project
3. Go to **Settings** → **Environment Variables**
4. Click **Add New**
5. Set:
   - **Key:** `REACT_APP_API_URL`
   - **Value:** `https://your-backend.onrender.com` (your actual backend URL)
   - **Environment:** Select all (Production, Preview, Development)
6. Click **Save**

### Step 2: Redeploy

After adding the environment variable:
1. Go to **Deployments** tab
2. Click **⋯** on the latest deployment
3. Click **Redeploy**
4. ✅ The new deployment will include the environment variable

## Verify Your Backend URL

Make sure your backend is:
- ✅ Deployed and running (e.g., on Render)
- ✅ Accessible at the URL you set
- ✅ CORS configured to allow your Vercel domain

## Update Backend CORS

Your backend needs to allow requests from your Vercel domain:

1. Go to your backend (Render dashboard)
2. **Settings** → **Environment Variables**
3. Update `CORS_ORIGINS` to include your Vercel URL:
   ```
   https://your-app.vercel.app,http://localhost:3000
   ```
4. Redeploy backend

## Test the Connection

After setting `REACT_APP_API_URL`:
1. Open your Vercel app
2. Open browser DevTools → Network tab
3. Try to generate a resume
4. Check if API requests go to the correct backend URL
5. Check for CORS errors in console

## Common Issues

### Issue: Still getting "Could not reach the server"
- ✅ Verify `REACT_APP_API_URL` is set correctly (no trailing slash)
- ✅ Verify backend is running and accessible
- ✅ Check browser console for CORS errors
- ✅ Verify backend CORS includes Vercel domain

### Issue: CORS errors in browser console
- Update backend `CORS_ORIGINS` to include: `https://your-app.vercel.app`
- Make sure no trailing slash in the URL
- Redeploy backend after changing CORS

### Issue: Environment variable not working
- Environment variables must start with `REACT_APP_` to be available in React
- Redeploy after adding environment variables
- Check Vercel build logs to verify env vars are included

## Example Configuration

**Vercel Environment Variables:**
```
REACT_APP_API_URL=https://resume-generator-api.onrender.com
```

**Backend (Render) Environment Variables:**
```
CORS_ORIGINS=https://resume-generator.vercel.app,http://localhost:3000
```

## Quick Checklist

- [ ] `REACT_APP_API_URL` set in Vercel (with your backend URL)
- [ ] Environment variable applied to all environments
- [ ] Redeployed Vercel app after setting env var
- [ ] Backend CORS includes Vercel domain
- [ ] Backend is running and accessible
- [ ] Test the connection in browser
