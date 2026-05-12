"""
ingest_soar.py
MARVL Lab — SOAR Video Inventory Ingestion Script
--------------------------------------------------
Reads a cleaned CSV export of the SOAR Data tab (via clean_soar.py) and inserts rows
into the `videos` table defined in marvl_database_schema_v1.2.sql

Usage:
    python ingest_soar.py --csv soar_clean.csv --db marvl.db [--dry-run]

Dependencies:
    pip install pandas

Supports:
    SQLite  (default, for local dev — just point --db at a .db file)
    PostgreSQL (SC Cluster/production — set --pg-dsn instead of --db)
"""

import argparse
import csv
import logging
import re
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

# ── optional postgres support ──────────────────────────────────────────────────
try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

import pandas as pd

# ── logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# ── constants: valid values from schema CHECKs ─────────────────────────────────
VALID_EXT           = {'mp4', 'avi', 'bmp'}
VALID_STORAGE       = {'Pasteur', 'SC Cluster', 'GDrive'}
VALID_ANON          = {'anonymized', 'raw', 'missing'}  # 'raw' = unprocessed, confirmed no identifiable content
VALID_INSTITUTIONS  = {
    'Intermountain', 'SST', 'HeiChole', 'Cholec80',
    'UTSW', 'Stanford', 'AutoLaparo',
    'Medica Sur-Cortes', 'Medica Sur-Hernandez',
    'München Klinik Harlaching'
}
VALID_PROCEDURES    = {
    'Cholecystectomy', 'Appendectomy', 'TEP Inguinal Hernia Repair',
    'TAPP Inguinal Hernia Repair', 'Hysterectomy', 'Fundoplication',
    'Umbilical Hernia', 'Colectomy', 'Sleeve Gastrectomy',
    'Diagnostic Lap/Port Placement', 'Bilateral Salpingooophrectomy',
    'Open', 'Unknown', 'Other'
}


# ── helpers ────────────────────────────────────────────────────────────────────

def clean(val):
    """Strip whitespace; return None for empty/NaN strings."""
    if val is None:
        return None
    s = str(val).strip()
    return None if s in ('', 'nan', 'NaN', 'N/A', 'n/a') else s


def parse_date_from_path(path: str) -> str | None:
    """
    Extract date from video_path like:
      /pasteur/data/intermountain/2021-07-26/00003-22976.mp4
    Returns 'YYYY-MM-DD' string or None.
    """
    match = re.search(r'(\d{4}-\d{2}-\d{2})', path or '')
    return match.group(1) if match else None


def parse_ext(video_ext: str | None, video_name: str | None) -> str | None:
    """
    Normalize extension: strip leading dot, lowercase.
    Falls back to parsing from video_name if ext column is blank.
    """
    if video_ext:
        ext = video_ext.lstrip('.').lower()
        return ext if ext in VALID_EXT else None
    if video_name:
        suffix = Path(video_name).suffix.lstrip('.').lower()
        return suffix if suffix in VALID_EXT else None
    return None


def infer_storage(video_path: str | None) -> str | None:
    """Guess storage_system from the path prefix."""
    if not video_path:
        return None
    p = video_path.lower()
    if 'pasteur' in p:
        return 'Pasteur'
    if 'sc' in p or 'cluster' in p:
        return 'SC Cluster'
    if 'drive' in p or 'gdrive' in p:
        return 'GDrive'
    return None


def make_video_id(num_id: int | None, video_name: str | None) -> str:
    """
    Generate a stable video_id.
    Format: VID<zero-padded num_id>  e.g. VID039
    Falls back to name-based ID if num_id missing.
    """
    if num_id is not None:
        try:
            return f"VID{int(num_id):03d}"
        except (ValueError, TypeError):
            pass
    if video_name:
        safe = re.sub(r'[^A-Za-z0-9_-]', '_', video_name)
        return f"VID_{safe}"
    return f"VID_UNKNOWN_{datetime.now().strftime('%f')}"


def validate_row(row: dict) -> list[str]:
    """Return list of warning strings for any constraint violations."""
    warnings = []
    if row.get('video_ext') and row['video_ext'] not in VALID_EXT:
        warnings.append(f"video_ext '{row['video_ext']}' not in schema CHECK")
    if row.get('storage_system') and row['storage_system'] not in VALID_STORAGE:
        warnings.append(f"storage_system '{row['storage_system']}' not in schema CHECK")
    if row.get('anon_status') and row['anon_status'] not in VALID_ANON:
        warnings.append(f"anon_status '{row['anon_status']}' not in schema CHECK")
    if row.get('institution') and row['institution'] not in VALID_INSTITUTIONS:
        warnings.append(f"institution '{row['institution']}' not in schema CHECK")
    if row.get('procedure') and row['procedure'] not in VALID_PROCEDURES:
        warnings.append(f"procedure '{row['procedure']}' not in schema CHECK")
    return warnings


# ── column mapping ─────────────────────────────────────────────────────────────
# Maps CSV column names (as they appear in SOAR export) → schema column names.
# Edit this if your sheet uses different headers.

COLUMN_MAP = {
    # post-clean column name (from soar_clean.csv) : schema column
    'num_id'           : 'num_id',
    'institution'      : 'institution',
    'video_name'       : 'video_name',
    'video_ext'        : 'video_ext',
    'video_path'       : 'video_path',
    'length'           : 'length',
    'fps'              : 'fps',
    'anon_status'      : 'anon_status',
    'procedure'        : 'procedure',
    'irb_protocol'     : 'irb_protocol',
    'pgs_score'        : 'pgs_score',
    'annotation_status': 'annotation_status',
}


# ── transform a single CSV row → schema dict ──────────────────────────────────

def transform_row(raw: dict) -> dict:
    """Map and clean one CSV row into a videos-table dict."""

    # Rename columns
    mapped = {}
    for csv_col, db_col in COLUMN_MAP.items():
        mapped[db_col] = clean(raw.get(csv_col))

    # num_id: coerce to int
    try:
        mapped['num_id'] = int(mapped['num_id']) if mapped['num_id'] else None
    except ValueError:
        mapped['num_id'] = None

    # video_id: generate from num_id
    mapped['video_id'] = make_video_id(mapped.get('num_id'), mapped.get('video_name'))

    # video_ext: normalize
    mapped['video_ext'] = parse_ext(mapped.get('video_ext'), mapped.get('video_name'))

    # storage_system: infer from path if missing
    if not mapped.get('storage_system'):
        mapped['storage_system'] = infer_storage(mapped.get('video_path'))

    # date_recorded: parse from path (SOAR has no explicit date column)
    if not mapped.get('date_recorded'):
        mapped['date_recorded'] = parse_date_from_path(mapped.get('video_path'))

    # length: coerce to int
    try:
        mapped['length'] = int(float(mapped['length'])) if mapped['length'] else None
    except (ValueError, TypeError):
        mapped['length'] = None

    # fps: coerce to float
    try:
        mapped['fps'] = float(mapped['fps']) if mapped['fps'] else None
    except (ValueError, TypeError):
        mapped['fps'] = None

    # defaults
    mapped.setdefault('surgical_approach', 'Laparoscopic')
    mapped.setdefault('annotation_status', 'Untagged')
    mapped.setdefault('is_usable', 1)
    mapped['date_added'] = date.today().isoformat()

    return mapped


# ── SQL ────────────────────────────────────────────────────────────────────────

INSERT_SQL = """
INSERT INTO videos (
    num_id, video_id, video_name, video_ext,
    storage_system, video_path, length, fps,
    procedure, institution, date_recorded, anon_status,
    irb_protocol, pgs_score,
    surgical_approach, annotation_status, is_usable, date_added
)
VALUES (
    :num_id, :video_id, :video_name, :video_ext,
    :storage_system, :video_path, :length, :fps,
    :procedure, :institution, :date_recorded, :anon_status,
    :irb_protocol, :pgs_score,
    :surgical_approach, :annotation_status, :is_usable, :date_added
)
ON CONFLICT (video_id) DO NOTHING;
"""

# PostgreSQL uses %s placeholders — handled separately below


# ── database connections ───────────────────────────────────────────────────────

def get_sqlite_conn(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # enforce foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_pg_conn(dsn: str):
    if not HAS_PSYCOPG2:
        log.error("psycopg2 not installed. Run: pip install psycopg2-binary")
        sys.exit(1)
    return psycopg2.connect(dsn)


# ── main ingestion logic ───────────────────────────────────────────────────────

def ingest(csv_path: str, conn, dry_run: bool = False, pg: bool = False):
    df = pd.read_csv(csv_path, dtype=str)
    log.info(f"Loaded {len(df)} rows from {csv_path}")

    inserted = skipped = errors = 0

    cursor = conn.cursor()

    for i, raw in enumerate(df.to_dict(orient='records'), start=1):
        try:
            row = transform_row(raw)
        except Exception as e:
            log.error(f"Row {i}: transform failed — {e}")
            errors += 1
            continue

        # Validate against schema constraints
        warnings = validate_row(row)
        for w in warnings:
            log.warning(f"Row {i} ({row.get('video_id')}): {w}")

        if dry_run:
            log.info(f"[DRY RUN] Row {i}: {row}")
            inserted += 1
            continue

        try:
            if pg:
                # psycopg2 uses %(key)s style
                pg_sql = INSERT_SQL.replace(':', '%(').replace(
                    ' :',  ' %('
                )
                # simpler: just use named dict with psycopg2
                cursor.execute(
                    """
                    INSERT INTO videos (
                        num_id, video_id, video_name, video_ext,
                        storage_system, video_path, length, fps,
                        procedure, institution, date_recorded, anon_status,
                        irb_protocol, pgs_score,
                        surgical_approach, annotation_status, is_usable, date_added
                    ) VALUES (
                        %(num_id)s, %(video_id)s, %(video_name)s, %(video_ext)s,
                        %(storage_system)s, %(video_path)s, %(length)s, %(fps)s,
                        %(procedure)s, %(institution)s, %(date_recorded)s, %(anon_status)s,
                        %(irb_protocol)s, %(pgs_score)s,
                        %(surgical_approach)s, %(annotation_status)s,
                        %(is_usable)s, %(date_added)s
                    )
                    ON CONFLICT (video_id) DO NOTHING;
                    """,
                    row
                )
            else:
                cursor.execute(INSERT_SQL, row)

            if cursor.rowcount == 0:
                log.debug(f"Row {i} ({row['video_id']}): skipped (already exists)")
                skipped += 1
            else:
                inserted += 1

        except Exception as e:
            log.error(f"Row {i} ({row.get('video_id')}): INSERT failed — {e}")
            errors += 1

    if not dry_run:
        conn.commit()

    log.info("─" * 50)
    log.info(f"Done.  Inserted: {inserted}  |  Skipped: {skipped}  |  Errors: {errors}")
    return {"inserted": inserted, "skipped": skipped, "errors": errors}


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Ingest SOAR CSV export into MARVL videos table"
    )
    parser.add_argument('--csv',    required=True, help='Path to SOAR CSV export')
    parser.add_argument('--db',     default=None,  help='SQLite .db file path (local dev)')
    parser.add_argument('--pg-dsn', default=None,  help='PostgreSQL DSN (production/SC Cluster)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Parse and validate without writing to DB')
    args = parser.parse_args()

    if not args.db and not args.pg_dsn and not args.dry_run:
        parser.error("Provide --db (SQLite) or --pg-dsn (PostgreSQL), or use --dry-run")

    csv_path = Path(args.csv)
    if not csv_path.exists():
        log.error(f"CSV not found: {csv_path}")
        sys.exit(1)

    if args.dry_run and not args.db and not args.pg_dsn:
        log.info("Dry-run mode — no database connection needed")
        ingest(str(csv_path), conn=None, dry_run=True)
        return

    if args.pg_dsn:
        log.info("Connecting to PostgreSQL...")
        conn = get_pg_conn(args.pg_dsn)
        ingest(str(csv_path), conn, dry_run=args.dry_run, pg=True)
    else:
        log.info(f"Connecting to SQLite: {args.db}")
        conn = get_sqlite_conn(args.db)
        ingest(str(csv_path), conn, dry_run=args.dry_run, pg=False)

    conn.close()


if __name__ == '__main__':
    main()
