# Vercel Deployment Checklist

## 1. Environment Setup
- [ ] Create a `.env` file with your Supabase credentials
- [ ] Add `.env` to `.gitignore`
- [ ] Set up environment variables in Vercel dashboard:
  - Name: `SUPABASE_URL`
  - Value: Your Supabase project URL
  - Visibility: Protected
  - Name: `SUPABASE_KEY`
  - Value: Your Supabase project API key
  - Visibility: Protected

## 2. File Structure
- [ ] Ensure `api/index.py` is the main serverless function
- [ ] Move static files to `static/` directory
- [ ] Verify `requirements.txt` contains all dependencies
- [ ] Confirm `vercel.json` is properly configured

## 3. Supabase Configuration
- [ ] Enable Row Level Security (RLS) on all tables
- [ ] Set up proper RLS policies
- [ ] Create necessary database indexes
- [ ] Test database connection locally

## 4. Deployment Steps
1. Commit changes to git:
   ```bash
   git add .
   git commit -m "Prepare for Vercel deployment"
   git push
   ```

2. Deploy to Vercel:
   ```bash
   vercel
   ```

3. After deployment:
   - Verify environment variables are set
   - Test API endpoints
   - Check Vercel logs for errors

## 5. Post-Deployment Verification
- [ ] Test login functionality
- [ ] Test Supabase connection
- [ ] Verify static files are served correctly
- [ ] Check error logs in Vercel dashboard

## Troubleshooting
If you encounter errors:
1. Check Vercel logs
2. Verify environment variables
3. Test API endpoints locally
4. Check database connection
5. Review error messages carefully
