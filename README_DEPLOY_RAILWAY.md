Deploying KYNORA to Railway

This file explains how to deploy the FastAPI application to Railway (https://railway.app).

Prerequisites
- A Railway account
- Git installed and repository pushed to a remote (GitHub/GitLab) connected to Railway
- A Firebase project and service account JSON (if you use Firestore/Authentication)

Steps
1. Prepare environment variables
   - Copy `.env.example` to `.env` locally and fill in values.
   - On Railway, add the following environment variables in the Project settings (Variables):
     - FIREBASE_PROJECT_ID
     - FIREBASE_PRIVATE_KEY (if using JSON key fields; see notes below)
     - FIREBASE_CLIENT_EMAIL
     - SECRET_KEY or JWT_SECRET_KEY
     - Any Cloudinary / SMTP / Redis config you need

    Note: Railway UI accepts multiline secrets but it's easier to save the service account JSON as a single environment variable. The application supports this via `FIREBASE_SERVICE_ACCOUNT`.

    Recommended: set an env var called `FIREBASE_SERVICE_ACCOUNT` containing the full JSON of your Firebase service account. Replace newline characters with literal \n when pasting into the Railway UI (the code will convert them back). Example (simplified):

    {
       "type": "service_account",
       "project_id": "kynora-ecommerce",
       "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIE...\\n-----END PRIVATE KEY-----\\n",
       "client_email": "firebase-adminsdk-xxx@kynora-ecommerce.iam.gserviceaccount.com"
    }

    The code will detect `FIREBASE_SERVICE_ACCOUNT` and write it to a temporary JSON file at runtime before initializing Firebase.

2. Add required files
   - We added a `Procfile` with the recommended command:
     web: uvicorn main:app --host=0.0.0.0 --port=$PORT --timeout-keep-alive 120

3. Ensure dependencies in `requirements.txt` are complete
   - `uvicorn[standard]` and `firebase-admin` are already present. Railway will run `pip install -r requirements.txt`.

4. (Optional) If using the Firebase JSON in Railway env vars follow this pattern in `core/database.py` or create a small startup script to write the JSON file to disk from the env var `FIREBASE_SERVICE_ACCOUNT`.

5. Deploy on Railway
   - Create a new Railway project and choose 'Deploy from GitHub/GitLab'
   - Connect your repository and select the branch to deploy (e.g., `new-version`)
   - Add environment variables in Project > Variables
   - Deploy. Railway will detect Python and install requirements, then run the `Procfile` command.

6. Test
   - After deployment, Railway exposes a public URL. Call `/health` to confirm database connectivity and that the app is running.

Tips and Troubleshooting
- If your Firebase private key contains newlines, escape them when setting as a Railway env var (replace actual newlines with \n). The code can then decode them back into newlines when building the credentials.
- If you prefer Docker, create a small `Dockerfile` and use Railway's Docker deployment.
- Keep `SECRET_KEY` and Firebase credentials secret in Railway project settings.

Next steps I can take for you
- Add helper code to write `FIREBASE_SERVICE_ACCOUNT` env var to `/tmp/serviceAccount.json` at startup (securely) and set `FIREBASE_CREDENTIALS_PATH` to that path.
- Add a minimal `Dockerfile` for containerized deploy.
- Add GitHub Actions to push to Railway automatically.
