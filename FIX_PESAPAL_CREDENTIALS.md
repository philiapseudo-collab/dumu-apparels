# How to Fix PesaPal Authentication Error

## Error Message
```
PesaPal authentication failed: Invalid consumer key or secret
```

## Root Cause
Your `PESAPAL_CONSUMER_KEY` and/or `PESAPAL_CONSUMER_SECRET` in Railway environment variables don't match your actual PesaPal Merchant Dashboard credentials.

## Step-by-Step Fix

### Step 1: Get Your PesaPal Credentials

1. **Log in to PesaPal Merchant Dashboard:**
   - Go to: https://developer.pesapal.com/
   - Log in with your merchant account credentials

2. **Navigate to API Credentials:**
   - Click on: **Developer** → **API Credentials**
   - Or go to: **Settings** → **Developer** → **API Credentials**

3. **Copy Your Credentials:**
   - Find your **Consumer Key** (usually a long string)
   - Find your **Consumer Secret** (usually a long string)
   - **Important:** Make sure you're copying from the **Production** section, not Sandbox/Test

### Step 2: Update Railway Environment Variables

1. **Go to Railway Dashboard:**
   - Open: https://railway.app/
   - Select your project
   - Click on your service (the one running the bot)

2. **Navigate to Variables:**
   - Click on the **Variables** tab
   - Or go to: **Settings** → **Variables**

3. **Update PESAPAL_CONSUMER_KEY:**
   - Find the variable `PESAPAL_CONSUMER_KEY`
   - Click on it to edit
   - Paste your Consumer Key from PesaPal dashboard
   - **Ensure:**
     - No leading/trailing spaces
     - No newlines
     - Exact match with dashboard
   - Click **Save**

4. **Update PESAPAL_CONSUMER_SECRET:**
   - Find the variable `PESAPAL_CONSUMER_SECRET`
   - Click on it to edit
   - Paste your Consumer Secret from PesaPal dashboard
   - **Ensure:**
     - No leading/trailing spaces
     - No newlines
     - Exact match with dashboard
   - Click **Save**

### Step 3: Verify the Fix

1. **Wait for Railway to Redeploy:**
   - Railway automatically redeploys when you change environment variables
   - Wait 1-2 minutes for the deployment to complete

2. **Test the Payment Flow:**
   - Send "Hi" to your Instagram bot
   - Select a product
   - Click "Card (PesaPal)"
   - Check Railway logs to confirm authentication succeeds

3. **Check Logs:**
   - In Railway Dashboard → Your Service → **Deployments** → Latest deployment → **Logs**
   - Look for: `PesaPal access token retrieved successfully`
   - If you see this, authentication is working!

## Common Issues & Solutions

### Issue 1: Using Sandbox/Test Credentials
**Symptom:** Authentication fails even with correct-looking credentials

**Solution:** 
- Make sure you're using **Production** credentials, not Sandbox
- Check in PesaPal dashboard: Are you in Production mode?
- The code uses production endpoints (`https://pay.pesapal.com`)

### Issue 2: Extra Spaces or Newlines
**Symptom:** Credentials look correct but still fail

**Solution:**
- When pasting into Railway, make sure there are no spaces before/after
- No line breaks in the middle of the credential
- Try copying the credential again from PesaPal dashboard

### Issue 3: Wrong Account
**Symptom:** Credentials work but from a different account

**Solution:**
- Make sure you're logged into the correct PesaPal merchant account
- Verify the Consumer Key matches the account you want to use

### Issue 4: Credentials Were Regenerated
**Symptom:** Credentials used to work but stopped

**Solution:**
- If you regenerated credentials in PesaPal dashboard, update Railway with the new ones
- Old credentials become invalid when regenerated

## Verification Checklist

- [ ] Logged into correct PesaPal merchant account
- [ ] Using Production credentials (not Sandbox)
- [ ] Copied Consumer Key exactly (no spaces/newlines)
- [ ] Copied Consumer Secret exactly (no spaces/newlines)
- [ ] Updated `PESAPAL_CONSUMER_KEY` in Railway
- [ ] Updated `PESAPAL_CONSUMER_SECRET` in Railway
- [ ] Railway redeployed successfully
- [ ] Tested payment flow and authentication succeeds

## Still Not Working?

If authentication still fails after following these steps:

1. **Double-check credentials in PesaPal:**
   - Log out and log back into PesaPal dashboard
   - Go to API Credentials again
   - Copy credentials fresh

2. **Verify in Railway:**
   - Check that variables are set (not empty)
   - Check for any special characters that might be causing issues

3. **Check Railway Logs:**
   - Look for the exact error message
   - The improved error logging should give you more details

4. **Contact PesaPal Support:**
   - If credentials are definitely correct, there might be an account issue
   - Contact PesaPal support to verify your account status

