# PesaPal Authentication Troubleshooting

## Current Status
Your credentials appear to be correctly set in Railway, but authentication is still failing.

## Possible Issues & Solutions

### Issue 1: Sandbox vs Production Credentials
**Check:** Are your credentials for Sandbox (Test) or Production (Live)?

**Solution:**
- The code currently uses **Production endpoints** (`https://pay.pesapal.com/v3/api/...`)
- If your credentials are for **Sandbox/Test**, they won't work with production endpoints
- Check your PesaPal email or dashboard to confirm which environment your credentials are for

**To verify:**
1. Log into PesaPal Merchant Dashboard
2. Check if there's a "Sandbox" or "Test" mode toggle
3. Verify if your credentials are labeled as "Production" or "Sandbox"

### Issue 2: Account Not Activated
**Check:** Is your PesaPal merchant account fully activated?

**Solution:**
- Some PesaPal accounts require activation/verification before API credentials work
- Contact PesaPal support to verify your account status
- Ensure all required documents/verifications are completed

### Issue 3: Credentials Need to be Regenerated
**Check:** Were these credentials recently created or regenerated?

**Solution:**
- Sometimes credentials need a few minutes to activate after creation
- Try regenerating credentials in PesaPal dashboard
- Wait 5-10 minutes after regeneration before testing

### Issue 4: Verify Credentials in PesaPal Dashboard
**Action:** Double-check credentials directly in PesaPal dashboard

**Steps:**
1. Log into: https://developer.pesapal.com/ or your PesaPal Merchant Dashboard
2. Navigate to: Developer → API Credentials (or Settings → API Credentials)
3. Compare the credentials shown there with what's in Railway
4. **Important:** Make sure you're viewing the correct environment (Production vs Sandbox)

### Issue 5: Contact PesaPal Support
If credentials are definitely correct but still failing:

**Contact PesaPal Support:**
- Email: support@pesapal.com
- Support Portal: https://www.pesapal.com/support
- Mention: "API v3 authentication failing with valid credentials"
- Provide: Your Consumer Key (first 8 characters for security: `YdBWAzrc...`)

## Verification Steps

1. ✅ **Credentials match between email and Railway** - DONE
2. ⚠️ **Verify if credentials are Production or Sandbox**
3. ⚠️ **Check PesaPal account activation status**
4. ⚠️ **Verify credentials directly in PesaPal dashboard**
5. ⚠️ **Try regenerating credentials if needed**

## Next Steps

1. **Check PesaPal Dashboard:**
   - Log into your PesaPal merchant account
   - Go to Developer/API Credentials section
   - Verify:
     - Are these Production or Sandbox credentials?
     - Do the credentials match exactly what's in Railway?
     - Is there any account status/activation message?

2. **If credentials are Sandbox:**
   - You'll need Production credentials for live payments
   - Contact PesaPal to get Production credentials
   - Or we can modify the code to support Sandbox endpoints for testing

3. **If credentials are Production but still failing:**
   - Contact PesaPal support
   - Verify account is fully activated
   - Check if there are any API access restrictions on your account

