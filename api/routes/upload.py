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

# Column names (pre- and post-rename, see clean_soar.clean) used to locate the
# real header row in an uploaded CSV. Matched case-insensitively against cells.
EXPECTED_HEADER_TOKENS = {
    "numid", "num_id", "dataset", "institution",
    "irb protocol", "irb_protocol", "pgs score", "pgs_score",
    "annotated?", "annotation_status",
    "video_name", "video_ext", "video_path", "video_id",
    "length", "fps", "anon_status", "procedure",
    "storage_system", "date_recorded",
}
# How many rows from the top to consider when hunting for the header. Google
# Sheets "Tables" exports only ever add a handful of banner/notes rows above
# the real table, so this comfortably covers that without scanning huge files.
HEADER_SEARCH_WINDOW = 25


def _find_header_row(lines):
    """Locate the header row even if the sheet's table doesn't start at A1 —
    i.e. there are banner/title/notes rows and/or blank columns above or
    beside it. Rather than guessing from row position or blank-cell counts,
    pick the row whose cells match the most known MARVL column names, since
    banner/notes text won't match any of them but a real header will match
    several.
    """
    window = lines[:HEADER_SEARCH_WINDOW]
    scores = [
        len({c.strip().strip('"').lower() for c in line.split(",")} & EXPECTED_HEADER_TOKENS)
        for line in window
    ]
    best_idx = max(range(len(scores)), key=lambda i: scores[i], default=0)
    if scores and scores[best_idx] >= 2:
        return best_idx
    # Fall back to the first row with more than one non-empty cell (handles
    # sheets using column names we don't recognize, while still skipping
    # blank rows and single-cell banner rows).
    return next(
        (i for i, line in enumerate(lines)
         if len([c for c in line.split(",") if c.strip()]) > 1),
        0,
    )


@router.post("/")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    contents = await file.read()
    lines = contents.decode("utf-8-sig").splitlines()
    start = _find_header_row(lines)
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
