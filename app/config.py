from pathlib import Path
import os


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / ".factweave"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "factweave.db"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
FACTWEAVE_MODEL = os.getenv("FACTWEAVE_MODEL", "gpt-4o-mini")
FACTWEAVE_EXTRACTION_MODE = os.getenv("FACTWEAVE_EXTRACTION_MODE", "rules")
VERIFICATION_ALLOWED_DOMAINS = {item.strip().lower() for item in os.getenv("VERIFICATION_ALLOWED_DOMAINS", "").split(",") if item.strip()}
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'factweave.db'}")

DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
