import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

# Use local key file if present (dev). On GCP the default service account is used.
credentials_path = BASE_DIR / "credentials" / "google-cloud-key.json"
if credentials_path.exists():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)
