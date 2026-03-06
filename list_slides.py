#!/usr/bin/env python3
"""Simple Google Slides lister using gcloud credentials"""

import subprocess
import json
import sys


def get_access_token():
    """Get access token from gcloud"""
    result = subprocess.run(
        ["./google-cloud-sdk/bin/gcloud", "auth", "print-access-token"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def list_slides():
    """List slides using curl and Drive API"""
    import urllib.request
    import urllib.error

    token = get_access_token()

    # Use Drive API to list presentations
    url = "https://www.googleapis.com/drive/v3/files?q=mimeType='application/vnd.google-apps.presentation'&fields=files(id,name,modifiedTime,webViewLink)&pageSize=50"

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            files = data.get("files", [])

            if not files:
                print("\n📭 No Google Slides presentations found.\n")
                return

            print(f"\n📊 Found {len(files)} Google Slides presentation(s):\n")
            print(f"{'Name':<50} {'Last Modified':<25} {'Link'}")
            print("=" * 100)

            for file in files:
                name = file["name"][:48] if len(file["name"]) > 48 else file["name"]
                modified = (
                    file["modifiedTime"][:19].replace("T", " ")
                    if "modifiedTime" in file
                    else "N/A"
                )
                link = file.get(
                    "webViewLink",
                    f"https://docs.google.com/presentation/d/{file['id']}/edit",
                )
                print(f"{name:<50} {modified:<25} {link}")

            print()

    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"\n❌ Error: {e.code} - {e.reason}")
        print(f"Details: {error_body}")
        print("\nTo access your slides, you need to authenticate with Drive scope.")
        print("Run this command and then try again:")
        print("  ./google-cloud-sdk/bin/gcloud auth login --enable-gdrive-access")


if __name__ == "__main__":
    list_slides()
