# Fixing Vercel Configuration Mismatch

## Problem
"Configuration Settings in the current Production deployment differ from your current Project Settings."

This means the deployment was created with different settings than what's currently configured.

## Solution: Sync Settings

### Step 1: Update Vercel Dashboard Settings

1. Go to your Vercel project → **Settings** → **General**
2. Set these values to match the configuration:

   **Root Directory:** `frontend`
   
   **Framework Preset:** Create React App
   
   **Build Command:** `npm run build`
   
   **Output Directory:** `build`
   
   **Install Command:** `npm install`

3. Click **Save**

### Step 2: Redeploy

After updating settings, you have two options:

**Option A: Automatic (Recommended)**
- Push a new commit to trigger auto-deployment
- The new deployment will use the updated settings

**Option B: Manual**
- Go to **Deployments** tab
- Click the **⋯** menu on the latest deployment
- Select **Redeploy**
- Check "Use existing Build Cache" if you want faster rebuild

### Step 3: Verify

After redeployment, check:
- ✅ Build logs show it's building from `frontend/` directory
- ✅ No configuration mismatch warnings
- ✅ Deployment completes successfully

## Alternative: Use vercel.json Only

If you prefer to manage everything via `vercel.json`:

1. **Remove Root Directory setting** in Vercel dashboard (set to empty/root)
2. Update `vercel.json` to include full paths:

```json
{
  "version": 2,
  "buildCommand": "cd frontend && npm install && npm run build",
  "outputDirectory": "frontend/build",
  "installCommand": "cd frontend && npm install",
  "framework": "create-react-app"
}
```

3. Redeploy

## Current Configuration

The current `vercel.json` assumes:
- **Root Directory** is set to `frontend` in Vercel dashboard
- Build commands run from `frontend/` directory
- Output goes to `frontend/build/`

## Environment Variables

Don't forget to set:
- `REACT_APP_API_URL` = Your backend API URL (e.g., `https://your-backend.onrender.com`)

## Troubleshooting

If settings still don't match:
1. Check both **Project Settings** and **Deployment Settings** (they can differ)
2. Delete the project and re-import with correct settings from the start
3. Ensure `vercel.json` and dashboard settings are aligned
