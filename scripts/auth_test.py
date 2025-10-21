"""
Auth test helper: fetch Firebase ID token for an email/password
and optionally call the protected /users/me endpoint on the backend.

Usage (PowerShell):
  # Set your Firebase Web API key (from Firebase Console → Project settings)
  $env:FIREBASE_WEB_API_KEY = "<YOUR_API_KEY>"

  # Get token and test /users/me
  py -3.11 scripts/auth_test.py --email "sandy@gmail.com" --password "Sandy@1" --base-url "http://localhost:8000"

  # Or pass the key explicitly
  py -3.11 scripts/auth_test.py --email "sandy@gmail.com" --password "Sandy@1" --api-key "<YOUR_API_KEY>" --base-url "http://localhost:8000"
"""
import os
import sys
import argparse
import json
from typing import Optional

import requests

FIREBASE_SIGNIN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"


def get_firebase_token(email: str, password: str, api_key: str) -> str:
    url = f"{FIREBASE_SIGNIN_URL}?key={api_key}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }
    resp = requests.post(url, json=payload, timeout=20)
    if resp.status_code != 200:
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        raise SystemExit(f"Failed to sign in ({resp.status_code}): {data}")
    data = resp.json()
    id_token = data.get("idToken")
    if not id_token:
        raise SystemExit("No idToken returned by Firebase. Response: " + json.dumps(data))
    return id_token


def call_protected_me(base_url: str, token: str) -> None:
    url = base_url.rstrip("/") + "/users/me"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, timeout=20)
    print("\n=== /users/me response ===")
    print(f"Status: {resp.status_code}")
    try:
        print(json.dumps(resp.json(), indent=2, default=str))
    except Exception:
        print(resp.text)


def main():
    parser = argparse.ArgumentParser(description="Fetch Firebase ID token and test protected endpoint")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--password", required=True, help="User password")
    parser.add_argument("--api-key", default=os.getenv("FIREBASE_WEB_API_KEY"), help="Firebase Web API key")
    parser.add_argument("--base-url", default=os.getenv("API_BASE_URL", "http://localhost:8000"), help="Backend base URL")
    parser.add_argument("--print-token", action="store_true", help="Print only the token and exit")
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit("FIREBASE_WEB_API_KEY is required. Set env var or pass --api-key.")

    print("Signing in with Firebase...")
    token = get_firebase_token(args.email, args.password, args.api_key)
    print("\n=== Firebase ID Token ===")
    print(token)

    if args.print_token:
        return

    print("\nCalling protected endpoint /users/me...")
    call_protected_me(args.base_url, token)


if __name__ == "__main__":
    sys.exit(main())
