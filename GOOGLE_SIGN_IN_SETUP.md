# Google sign-in setup

Google sign-in is optional. Without credentials, the Google button returns users to the login page with a configuration message; email/password sign-in remains available.

1. In Google Cloud Console, configure an OAuth consent screen and create an OAuth 2.0 **Web application** client.
2. Add the local redirect URI `http://127.0.0.1:8000/auth/google/callback` to **Authorized redirect URIs**.
3. Set these environment variables before starting the app. Keep the client secret private and do not commit it:

   ```powershell
   $env:GOOGLE_CLIENT_ID = 'your-client-id.apps.googleusercontent.com'
   $env:GOOGLE_CLIENT_SECRET = 'your-client-secret'
   $env:GOOGLE_REDIRECT_URI = 'http://127.0.0.1:8000/auth/google/callback'
   python run.py
   ```

For a deployed environment, register its exact HTTPS callback URI in Google Cloud and set `GOOGLE_REDIRECT_URI` to that URI. Use your secret manager for `GOOGLE_CLIENT_SECRET`.

Google accounts with verified email addresses can sign in to an existing account with the same email. New Google accounts are verified automatically and asked for a phone number before an Engineer account and private workspace are created. Google OAuth uses state, nonce, PKCE, Google signing-key verification, and a short-lived encrypted flow state. No OAuth library or database migration is required.
