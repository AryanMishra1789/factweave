from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app

DATASETS = ROOT / "starter-datasets" / "starter-datasets"

with app.test_client() as client:
    for pdf in sorted(DATASETS.glob("**/*.pdf")):
        with pdf.open("rb") as stream:
            response = client.post("/api/documents", data={"file": (stream, pdf.name)}, content_type="multipart/form-data")
        print(response.status_code, pdf.name, response.get_json())
