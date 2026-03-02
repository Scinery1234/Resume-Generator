# Vercel Stuck on Initializing - Fix Guide

## Problem
Vercel gets stuck on "initializing" because it can't detect the project structure correctly.

## Solution Options

### Option 1: Set Root Directory in Vercel Dashboard (RECOMMENDED)

1. Go to your Vercel project dashboard
2. Click **Settings** → **General**
3. Scroll to **Root Directory**
4. Set it to: `frontend`
5. Click **Save**
6. Redeploy the project

This tells Vercel to treat the `frontend/` directory as the project root, so it will:
- Look for `package.json` in `frontend/`
- Run build commands from `frontend/`
- Output to `frontend/build`

### Option 2: Use Root-Level Package.json (Alternative)

If Option 1 doesn't work, the root `package.json` has been created to delegate to the frontend directory.

## Environment Variables

**CRITICAL**: Set this in Vercel Settings → Environment Variables:

- `REACT_APP_API_URL` = `https://your-backend.onrender.com`
  - Without this, your frontend won't be able to connect to the backend API

## Verification Steps

1. After setting root directory to `frontend`, check:
   - Build logs should show npm commands running
   - Should see "Installing dependencies" message
   - Should see "Building..." message

2. If still stuck:
   - Check Vercel build logs for any error messages
   - Verify `frontend/package-lock.json` exists
   - Try deleting and re-importing the project

## Quick Fix Checklist

- [ ] Set Root Directory to `frontend` in Vercel dashboard
- [ ] Set `REACT_APP_API_URL` environment variable
- [ ] Trigger a new deployment
- [ ] Check build logs for progress

## If Still Not Working

1. **Delete the Vercel project** and re-import
2. During import, manually set:
   - Framework Preset: **Create React App**
   - Root Directory: **frontend**
   - Build Command: `npm run build`
   - Output Directory: `build`
