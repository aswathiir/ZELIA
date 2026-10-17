"""
config.py — Centralized environment configuration for the Ultravox Handler service.
All environment variables are read once here and imported by other modules.
"""
import os

# ─────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://zelia:zelia_secure_2024@postgres:5432/zelia"
)

# ─────────────────────────────────────────────
# Ultravox
# ─────────────────────────────────────────────
ULTRAVOX_API_KEY: str = os.getenv("ULTRAVOX_API_KEY", "")
ULTRAVOX_AGENT_ID: str = os.getenv("ULTRAVOX_AGENT_ID", "")
ULTRAVOX_API_URL: str = "https://api.ultravox.ai/api"
ULTRAVOX_STRICT: bool = os.getenv("ULTRAVOX_STRICT", "true").lower() == "true"

# ─────────────────────────────────────────────
# N8N
# ─────────────────────────────────────────────
N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "")

# ─────────────────────────────────────────────
# Downstream services
# ─────────────────────────────────────────────
SUBMISSION_SERVICE_URL: str = os.getenv(
    "SUBMISSION_SERVICE_URL",
    "http://submission-service:8004"
)
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-8b-8192")

# ─────────────────────────────────────────────
# MinIO
# ─────────────────────────────────────────────
MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY: str = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY: str = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_BUCKETS: list[str] = [
    b.strip()
    for b in os.getenv("MINIO_BUCKETS", "verified-docs,filled-forms").split(",")
    if b.strip()
]

# ─────────────────────────────────────────────
# CORS
# ─────────────────────────────────────────────
CORS_ALLOWED_ORIGINS: list[str] = os.getenv(
    "CORS_ALLOWED_ORIGINS", "*"
).split(",")

# ─────────────────────────────────────────────
# Scheme field requirements (kept here to avoid spreading constants)
# ─────────────────────────────────────────────
UNIVERSAL_REQUIRED_FIELDS: list[str] = ["name", "address"]

SCHEME_REQUIRED_FIELDS: dict[str, list[str]] = {
    "ka-widow-pension":   ["monthly_income"],
    "ka-old-age-pension": ["monthly_income"],
    "pmjay":              [],
}

SCHEME_DISPLAY_NAMES: dict[str, str] = {
    "ka-widow-pension":   "Karnataka Widow Pension",
    "ka-old-age-pension": "Karnataka Old Age Pension",
    "pmjay":              "PM-JAY Ayushman Bharat",
}
