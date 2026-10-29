import os
from pathlib import Path

from dotenv import load_dotenv


APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent.parent if APP_DIR.parent.name == "backend" else APP_DIR.parent
load_dotenv(ROOT_DIR / ".env")
configured_db_path = Path(os.getenv("CASEOPS_DB_PATH", ROOT_DIR / "backend" / "losslens.db"))
DB_PATH = configured_db_path if configured_db_path.is_absolute() else ROOT_DIR / configured_db_path
ANALYST_TOKEN = os.getenv("CASEOPS_ANALYST_TOKEN", "local-demo-analyst")
REVIEWER_TOKEN = os.getenv("CASEOPS_REVIEWER_TOKEN", "local-demo-reviewer")
ENVIRONMENT = os.getenv("CASEOPS_ENV", "development")


def validate_configuration() -> None:
    if ANALYST_TOKEN == REVIEWER_TOKEN:
        raise RuntimeError("Analyst and reviewer tokens must be different")
    if ENVIRONMENT == "production":
        tokens = (ANALYST_TOKEN, REVIEWER_TOKEN)
        if any(
            len(token) < 32
            or token.startswith("local-demo-")
            or token.startswith("replace-with-")
            for token in tokens
        ):
            raise RuntimeError("Production requires distinct, non-placeholder tokens of at least 32 characters")