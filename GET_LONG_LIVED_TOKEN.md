# How to Get a Long-Lived (Permanent) Instagram Page Access Token

## Important Note
Facebook/Meta doesn't have truly "permanent" tokens, but you can get a **long-lived Page Access Token** that **doesn't expire** as long as:
- The user who generated it maintains admin rights to the Page
- The token isn't revoked manually

## Step-by-Step Guide

### Step 1: Get a Short-Lived User Access Token

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. In the top right, select your app from the dropdown
3. Click "Generate Access Token" button
4. Grant these permissions when prompted:
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_metadata` (optional but recommended)
   - `instagram_basic`
   - `instagram_manage_messages`
5. Copy the generated token (this is a short-lived token, expires in ~1-2 hours)

### Step 2: Exchange for Long-Lived User Access Token

1. Go to [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/)
2. Paste your short-lived token from Step 1
3. Click "Debug" button
4. Click "Extend Access Token" button
5. Copy the new token (this is a long-lived user token, expires in ~60 days)

### Step 3: Get the Permanent Page Access Token

1. Go back to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Replace the token in the explorer with your long-lived user token from Step 2
3. In the query field, enter: `me/accounts` and click "Submit"
4. You'll see a list of Pages you manage
5. Find your Instagram-connected Page in the list
6. Look for the `access_token` field for that Page
7. **Copy this token** - this is your permanent Page Access Token!

### Step 4: Verify the Token Doesn't Expire

1. Go to [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/)
2. Paste your Page Access Token from Step 3
3. Click "Debug"
4. Check the "Expires At" field - it should show "Never" or a date far in the future

### Step 5: Update in Railway

1. Go to Railway Dashboard → Your Service → Variables
2. Find `PAGE_ACCESS_TOKEN`
3. Paste the new permanent Page Access Token
4. Save (Railway will redeploy automatically)

## Alternative: Quick Method (If You Have App Admin Access)

If you're the app admin and just need a quick token:

1. Go to [Meta for Developers Dashboard](https://developers.facebook.com/)
2. Select your App
3. Go to: **Tools** → **Graph API Explorer**
4. Select your App from the dropdown
5. Click "Generate Access Token"
6. Select your Instagram Page from the dropdown
7. Copy the token (this will be a long-lived token if you have the right permissions)

## Important Notes

⚠️ **Security:**
- Store the token securely (never commit to git)
- If you lose the token, you'll need to regenerate it
- If the user who generated the token loses Page admin access, the token will stop working

⚠️ **Token Validity:**
- The token remains valid as long as the user who generated it is a Page admin
- If the user is removed as admin, the token will become invalid
- You can regenerate the token anytime by repeating these steps

## Troubleshooting

**Token expires immediately:**
- Make sure you completed all steps, especially Step 2 (extending the token)
- Ensure you're using the Page Access Token from `me/accounts`, not the user token

**Token doesn't work:**
- Verify the token in Access Token Debugger
- Check that your app has the required permissions in App Settings
- Ensure your Instagram account is connected to a Facebook Page

