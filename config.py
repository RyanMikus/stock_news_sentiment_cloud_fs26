import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

GOOGLE_APPLICATION_CREDENTIALS = (
    BASE_DIR / "credentials" / "google-cloud-key.json"
)

if GOOGLE_APPLICATION_CREDENTIALS.exists():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(GOOGLE_APPLICATION_CREDENTIALS)
else:
    raise FileNotFoundError(
        f"Google Cloud credentials file not found: {GOOGLE_APPLICATION_CREDENTIALS}"
    )