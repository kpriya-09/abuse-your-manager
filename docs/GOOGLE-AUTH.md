# Google sign-in setup

Google sign-in is optional. Private login/password authentication continues to work when it is not configured.

1. In Google Cloud Console, configure the OAuth consent screen for this product.
2. Create an OAuth 2.0 Client ID with application type **Web application**.
3. Add these Authorized JavaScript origins:
   - `https://abuseyourmanager.com`
   - `https://www.abuseyourmanager.com`
   - `https://abuse-your-manager.vercel.app`
   - `http://localhost:5050` for local testing, if needed
4. No redirect URI is required for the Google Identity Services callback used here.
5. In Vercel, add the public client ID as `GOOGLE_CLIENT_ID` for Production and Preview, then redeploy.

The browser receives a Google ID token and sends it to the same-origin Flask API. The server verifies its signature, audience, issuer, and expiry with Google's official Python library. Only a one-way derivative of Google's stable `sub` identifier is stored. Google name, email, and profile photo are not stored or exposed. The app assigns the same kind of random public alias used by private-login accounts.

If `GOOGLE_CLIENT_ID` is absent, the Google script is not loaded and the Google button is hidden.
