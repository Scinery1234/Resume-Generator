# Fix: "cd frontend: No such file or directory"

## The Error
```
Running "install" command: `cd frontend && npm ci`...
sh: line 1: cd: frontend: No such file or directory
```

## Root Cause
When **Root Directory** is set to `frontend` in Vercel dashboard, Vercel **already changes into that directory** before running commands. So when the install command tries to `cd frontend`, it fails because you're already IN the frontend directory.

## Solution

### In Vercel Dashboard Settings:

1. Go to **Settings** → **General**
2. Verify **Root Directory** is set to: `frontend`
3. Set **Install Command** to: `npm ci` (NOT `cd frontend && npm ci`)
4. Set **Build Command** to: `npm run build` (NOT `cd frontend && npm run build`)
5. Set **Output Directory** to: `build` (NOT `frontend/build`)
6. Click **Save**

### What Changed

- ✅ Created `vercel.json` with correct commands (no `cd frontend`)
- ✅ Commands assume Root Directory = `frontend`
- ✅ Install: `npm ci`
- ✅ Build: `npm run build`
- ✅ Output: `build`

## Quick Fix Checklist

- [ ] Root Directory = `frontend` in Vercel Settings
- [ ] Install Command = `npm ci` (no `cd frontend`)
- [ ] Build Command = `npm run build` (no `cd frontend`)
- [ ] Output Directory = `build` (not `frontend/build`)
- [ ] Redeploy after changing settings

## How It Works

When Root Directory = `frontend`:
- Vercel clones repo
- Vercel changes into `frontend/` directory
- Vercel runs install/build commands from `frontend/`
- So commands should NOT include `cd frontend`

## Alternative: If Root Directory is Empty

If you set Root Directory to empty/root, then use:
- Install Command: `cd frontend && npm ci`
- Build Command: `cd frontend && npm run build`
- Output Directory: `frontend/build`

But the recommended approach is Root Directory = `frontend` with simple commands.
