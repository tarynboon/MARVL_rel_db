import io
import tempfile
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile, File

from ..db import get_conn

router = APIRouter(prefix="/upload", tags=["upload"])

# Import clean/ingest from project root
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from clean_soar import clean
from ingest_soar import ingest


@router.post("/")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    contents = await file.read()
    # Skip leading blank rows (e.g. the banner row Google Sheets "Tables" adds
    # above the real header when exported to CSV), which would otherwise be
    # read as the header and push real column names into the first data row.
    lines = contents.decode("utf-8-sig").splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip(",").strip()), 0)
    try:
        df = pd.read_csv(io.StringIO("\n".join(lines[start:])), dtype=str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    df_clean, issues = clean(df)

    with tempfile.NamedTemporaryFile(suffix="_clean.csv", delete=False, mode="w") as f:
        df_clean.to_csv(f, index=False)
        clean_path = f.name

    conn = get_conn()
    counts = ingest(clean_path, conn)
    conn.close()

    return {
        "inserted": counts["inserted"],
        "skipped": counts["skipped"],
        "errors": counts["errors"],
        "issues_count": len(issues),
        "issues": issues[:50],
    }
