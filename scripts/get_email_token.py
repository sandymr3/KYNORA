#!/usr/bin/env python3
"""
Sign in to Firebase with email + password and print the ID token.
- Hardcode EMAIL and PASSWORD below, or pass via CLI.
- Requires the Firebase Web API key (from frontend `.env` as NEXT_PUBLIC_FIREBASE_API_KEY).

Usage:
  python scripts/get_email_token.py \
    --email you@example.com \
    --password yourPassword \
    --api-key AIza... (optional if set below or in env)

If args are omitted, the hardcoded constants or environment variables are used.
"""
import os
import argparse
import sys
import json
import httpx

# --- Hardcode here if you want quick testing ---
EMAIL = "sandy@gmail.com"          # change if needed
PASSWORD = "Sandy@1"               # change if needed
API_KEY = os.getenv("NEXT_PUBLIC_FIREBASE_API_KEY", "AIzaSyDNQvcmaxmJA-CLvF86tZTUgc6CHLwSeNk")

FIREBASE_SIGNIN_URL = (
    "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
)


def sign_in_with_email_password(email: str, password: str, api_key: str) -> dict:
    url = FIREBASE_SIGNIN_URL.format(api_key=api_key)
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }
    headers = {"Content-Type": "application/json"}

    with httpx.Client(timeout=20.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}

        if resp.status_code != 200:
            # Helpful error output
            message = data.get("error", {}).get("message") or data
            raise SystemExit(f"Firebase sign-in failed ({resp.status_code}): {message}")
        return data


def main():
    parser = argparse.ArgumentParser(description="Get Firebase ID token by email/password")
    parser.add_argument("--email", type=str, default=None, help="Email address")
    parser.add_argument("--password", type=str, default=None, help="Password")
    parser.add_argument("--api-key", type=str, default=None, help="Firebase Web API key")
    parser.add_argument("--json", action="store_true", help="Print full JSON response")
    parser.add_argument("--save", type=str, default=None, help="Save result to file path")
    args = parser.parse_args()

    email = args.email or EMAIL
    password = args.password or PASSWORD
    api_key = args.api_key or API_KEY

    if not email or not password or not api_key:
        raise SystemExit("Missing email/password/api-key. Provide via args, hardcode, or NEXT_PUBLIC_FIREBASE_API_KEY env.")

    data = sign_in_with_email_password(email, password, api_key)

    id_token = data.get("idToken")
    refresh_token = data.get("refreshToken")
    local_id = data.get("localId")

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print("\n==============================")
        print("Firebase Email/Password Sign-in")
        print("==============================")
        print(f"Email      : {email}")
        print(f"User ID    : {local_id}")
        print("\nID Token:")
        print(id_token or "<missing idToken>")
        print("\nRefresh Token:")
        print(refresh_token or "<missing refreshToken>")

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump({"email": email, "localId": local_id, "idToken": id_token, "refreshToken": refresh_token}, f, indent=2)
        print(f"\nSaved tokens to: {args.save}")


if __name__ == "__main__":
    main()
