# Vercel Deployment Guide

## Fixed Issues

The Vercel configuration has been updated to properly handle the frontend React app located in the `frontend/` subdirectory.

## Environment Variables Required

Set these in your Vercel project settings (Settings → Environment Variables):

### Required:
- `REACT_APP_API_URL` - Your backend API URL (e.g., `https://your-backend.onrender.com`)
  - **Important**: This must be set for the frontend to connect to your backend API
  - Without this, API calls will fail

### Optional (for backend):
- `OPENAI_API_KEY` - For AI resume generation features
- `CORS_ORIGINS` - Comma-separated list of allowed origins (should include your Vercel URL)

## Deployment Steps

1. **Connect Repository to Vercel**
   - Go to Vercel Dashboard
   - Import your GitHub repository
   - Vercel will auto-detect the configuration

2. **Set Environment Variables**
   - Go to Project Settings → Environment Variables
   - Add `REACT_APP_API_URL` with your backend URL
   - Add any other required variables

3. **Deploy**
   - Vercel will automatically deploy on push
   - Or trigger a manual deployment from the dashboard

## Configuration Details

The `vercel.json` is configured to:
- Build from the `frontend/` directory
- Output to `frontend/build`
- Use `npm ci` for faster, reliable installs
- Handle React Router routing with rewrites
- Cache static assets for better performance

## Troubleshooting

### Build Freezes/Timeouts
- Check that `package-lock.json` exists in `frontend/`
- Ensure all dependencies are listed in `package.json`
- Try increasing build timeout in Vercel settings (if on Pro plan)

### API Connection Issues
- Verify `REACT_APP_API_URL` is set correctly
- Check CORS settings on your backend
- Ensure backend is deployed and accessible

### Routing Issues
- The `rewrites` configuration handles client-side routing
- All routes should redirect to `/index.html` for React Router

## Notes

- The backend (FastAPI) should be deployed separately (e.g., on Render)
- Only the frontend React app is deployed to Vercel
- Make sure your backend CORS settings include your Vercel domain
