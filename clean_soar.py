"""
clean_soar.py
MARVL Lab — SOAR Data Cleaning Script
--------------------------------------
Reads a raw CSV export of the SOAR Data tab, cleans it, and outputs:
  1. soar_clean.csv     — cleaned data ready for ingestion
  2. soar_issues.csv    — rows with problems that need human review

Run BEFORE ingest_soar.py.

Usage:
    python clean_soar.py --csv data_tab_export.csv

Issues addressed (from MARVL Database Memo v1.2):
  - length field: confirm frames vs seconds (151427 = frames, not seconds)
  - pgs_score: flag as unexpected/vestigial column — confirm if still needed
  - anon_status: normalize casing, flag 'raw' rows for attention
  - video_ext: strip leading dots, normalize to lowercase
  - institution: map known aliases → schema-approved values
  - video_path: check for consistency, extract date_recorded
  - fps: normalize near-integer floats (29.999 → 30)
  - video_id: generate from num_id if missing
  - duplicates: flag videos with same video_name + institution
  - Missing required fields: video_name, video_path
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

# ── Schema-allowed values (from marvl_database_schema_v1.2.sql) ──────────────

VALID_EXT = {'mp4', 'avi', 'bmp'}
VALID_ANON = {'anonymized', 'raw', 'missing'}
VALID_INSTITUTIONS = {
    'Intermountain', 'SST', 'HeiChole', 'Cholec80',
    'UTSW', 'Stanford', 'AutoLaparo',
    'Medica Sur-Cortes', 'Medica Sur-Hernandez',
    'München Klinik Harlaching'
}
VALID_PROCEDURES = {
    'Cholecystectomy', 'Appendectomy', 'TEP Inguinal Hernia Repair',
    'TAPP Inguinal Hernia Repair', 'Hysterectomy', 'Fundoplication',
    'Umbilical Hernia', 'Colectomy', 'Sleeve Gastrectomy',
    'Diagnostic Lap/Port Placement', 'Bilateral Salpingooophrectomy',
    'Open', 'Unknown', 'Other'
}
VALID_STORAGE = {'Pasteur', 'SC Cluster', 'GDrive'}

# Known aliases: lowercase input → schema-approved value
INSTITUTION_ALIASES = {
    'intermountain':             'Intermountain',
    'intermountain health':      'Intermountain',
    'sst':                       'SST',
    'heichole':                  'HeiChole',
    'hei chole':                 'HeiChole',
    'cholec80':                  'Cholec80',
    'cholec 80':                 'Cholec80',
    'utsw':                      'UTSW',
    'ut southwestern':           'UTSW',
    'stanford':                  'Stanford',
    'autolaparo':                'AutoLaparo',
    'auto laparo':               'AutoLaparo',
    'medica sur cortes':         'Medica Sur-Cortes',
    'medica sur-cortes':         'Medica Sur-Cortes',
    'medica sur‑cortes':    'Medica Sur-Cortes',   # U+2011 non-breaking hyphen
    'medica sur hernandez':      'Medica Sur-Hernandez',
    'medica sur-hernandez':      'Medica Sur-Hernandez',
    'medica sur‑hernandez': 'Medica Sur-Hernandez', # U+2011 non-breaking hyphen
    'münchen klinik harlaching': 'München Klinik Harlaching',
    'munchen klinik harlaching': 'München Klinik Harlaching',
    'munich klinik harlaching':  'München Klinik Harlaching',
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_str(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    return None if s in ('', 'nan', 'NaN', 'N/A', 'n/a', 'none', 'None') else s

def normalize_ext(val):
    if not val:
        return None
    return str(val).lstrip('.').lower().strip()

def normalize_anon(val):
    if not val:
        return 'missing'
    return str(val).lower().strip()

def normalize_institution(val):
    if not val:
        return None
    key = str(val).lower().strip()
    return INSTITUTION_ALIASES.get(key, val.strip())

def normalize_fps(val):
    try:
        f = float(val)
        rounded = round(f)
        if abs(f - rounded) < 0.05:
            return float(rounded)
        return f
    except (TypeError, ValueError):
        return None

def parse_date_from_path(path):
    if not path:
        return None
    match = re.search(r'(\d{4}-\d{2}-\d{2})', path)
    return match.group(1) if match else None

def infer_storage(path):
    if not path:
        return None
    p = str(path).lower()
    if 'pasteur' in p:
        return 'Pasteur'
    if 'sc' in p or 'cluster' in p:
        return 'SC Cluster'
    if 'gdrive' in p or 'drive' in p:
        return 'GDrive'
    return None

def make_video_id(num_id, video_name):
    try:
        return f"VID{int(float(num_id)):03d}"
    except (TypeError, ValueError):
        pass
    if video_name:
        safe = re.sub(r'[^A-Za-z0-9_-]', '_', str(video_name))
        return f"VID_{safe}"
    return None

def check_length(length, fps):
    """Flag suspicious length values. Memo: 151427 frames at 30fps = ~84min (fine)."""
    try:
        l, f = float(length), float(fps)
        if f == 0:
            return None
        duration_sec = l / f
        if duration_sec > 28800:
            return f"Suspiciously long: {duration_sec/3600:.1f}h — check if frames vs seconds"
        if l < 500:
            return f"Very short ({l}) — might be seconds not frames"
    except (TypeError, ValueError):
        pass
    return None


# ── Main cleaning ─────────────────────────────────────────────────────────────

def clean(df: pd.DataFrame):
    issues = []

    # Rename Data tab columns to schema names
    rename_map = {
        'NumID':        'num_id',
        'dataset':      'institution',
        'IRB Protocol': 'irb_protocol',
        'PGS Score':    'pgs_score',
        'annotated?':   'annotation_status',
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # 'res' column (e.g. "(1280, 720)") — not in schema yet, drop to avoid ingestion errors
    # TODO: add video_resolution column to schema if needed
    if 'res' in df.columns:
        print("i  'res' column found (e.g. '(1280, 720)') — not in schema, dropping for now.")
        df = df.drop(columns=['res'])

    # '4:25 - 5:32' clip-range column from Data tab — not in schema, drop it
    if '4:25 - 5:32' in df.columns:
        df = df.drop(columns=['4:25 - 5:32'])

    # pgs_score is a confirmed schema column — no flag needed

    for idx, row in df.iterrows():

        # num_id
        try:
            df.at[idx, 'num_id'] = int(float(row.get('num_id', '')))
        except (TypeError, ValueError):
            df.at[idx, 'num_id'] = None
            issues.append({'row': idx, 'field': 'num_id',
                           'value': row.get('num_id'),
                           'issue': 'Missing or non-numeric num_id'})

        # video_name (required)
        name = clean_str(row.get('video_name'))
        df.at[idx, 'video_name'] = name
        if not name:
            issues.append({'row': idx, 'field': 'video_name', 'value': None,
                           'issue': 'Missing video_name — required field'})

        # video_id: generate if missing
        vid = clean_str(row.get('video_id'))
        if not vid:
            vid = make_video_id(row.get('num_id'), name)
            df.at[idx, 'video_id'] = vid
        if not vid:
            issues.append({'row': idx, 'field': 'video_id', 'value': None,
                           'issue': 'Could not generate video_id'})

        # video_ext
        ext = normalize_ext(clean_str(row.get('video_ext')))
        df.at[idx, 'video_ext'] = ext
        if ext and ext not in VALID_EXT:
            issues.append({'row': idx, 'field': 'video_ext', 'value': ext,
                           'issue': f"'{ext}' not in allowed values {VALID_EXT}"})

        # video_path (required)
        path = clean_str(row.get('video_path'))
        df.at[idx, 'video_path'] = path
        if not path:
            issues.append({'row': idx, 'field': 'video_path', 'value': None,
                           'issue': 'Missing video_path — required field'})

        # storage_system: infer if missing
        storage = clean_str(row.get('storage_system'))
        if not storage:
            storage = infer_storage(path)
            df.at[idx, 'storage_system'] = storage
        if storage and storage not in VALID_STORAGE:
            issues.append({'row': idx, 'field': 'storage_system', 'value': storage,
                           'issue': f"'{storage}' not in allowed values {VALID_STORAGE}"})

        # date_recorded: parse from path if blank
        date_rec = clean_str(row.get('date_recorded'))
        if not date_rec:
            date_rec = parse_date_from_path(path)
            df.at[idx, 'date_recorded'] = date_rec

        # fps: normalize near-integers (29.9997 → 30)
        fps = normalize_fps(clean_str(row.get('fps')))
        df.at[idx, 'fps'] = fps

        # length: coerce + check frames-vs-seconds (memo: confirm with Alan)
        length_raw = clean_str(row.get('length'))
        try:
            length = int(float(length_raw))
            df.at[idx, 'length'] = length
            flag = check_length(length, fps)
            if flag:
                issues.append({'row': idx, 'field': 'length', 'value': length,
                               'issue': flag})
        except (TypeError, ValueError):
            df.at[idx, 'length'] = None
            if length_raw:
                issues.append({'row': idx, 'field': 'length', 'value': length_raw,
                               'issue': 'Non-numeric length'})

        # institution: normalize aliases
        inst = normalize_institution(clean_str(row.get('institution')))
        df.at[idx, 'institution'] = inst
        if inst and inst not in VALID_INSTITUTIONS:
            issues.append({'row': idx, 'field': 'institution', 'value': inst,
                           'issue': f"'{inst}' not in schema — add alias or new value?"})

        # anon_status: normalize + flag raw
        anon = normalize_anon(clean_str(row.get('anon_status')))
        df.at[idx, 'anon_status'] = anon
        if anon not in VALID_ANON:
            issues.append({'row': idx, 'field': 'anon_status', 'value': anon,
                           'issue': f"'{anon}' not in allowed values {VALID_ANON}"})
        # 'raw' = unprocessed, not PHI — confirmed no identifiable content, SC Cluster is fine

        # annotation_status: normalize from 'annotated?' (yes/no/empty → Annotated/Untagged)
        ann = clean_str(row.get('annotation_status'))
        if ann is not None:
            if ann.lower() in ('yes', 'true', '1', 'annotated'):
                df.at[idx, 'annotation_status'] = 'Annotated'
            elif ann.lower() in ('no', 'false', '0', 'untagged'):
                df.at[idx, 'annotation_status'] = 'Untagged'
            # else: pass through as-is (custom status string)

        # procedure: normalize casing
        proc = clean_str(row.get('procedure'))
        if proc:
            # Title-case match attempt
            proc_titled = proc.title()
            # Special cases that title() doesn't handle perfectly
            proc_map = {
                'Cholecystectomy':                   'Cholecystectomy',
                'Cholecysectomy':                    'Cholecystectomy',  # typo in sheet
                'Appendectomy':                      'Appendectomy',
                'Tep Inguinal Hernia Repair':        'TEP Inguinal Hernia Repair',
                'Tapp Inguinal Hernia Repair':       'TAPP Inguinal Hernia Repair',
                'Hysterectomy':                      'Hysterectomy',
                'Fundoplication':                    'Fundoplication',
                'Umbilical Hernia':                  'Umbilical Hernia',
                'Colectomy':                         'Colectomy',
                'Sleeve Gastrectomy':                'Sleeve Gastrectomy',
                'Diagnostic Lap/Port Placement':     'Diagnostic Lap/Port Placement',
                'Bilateral Salpingooophrectomy':     'Bilateral Salpingooophrectomy',
                'Open':                              'Open',
                'Open Surgery':                      'Open',
                'Umbilical Hernias':                 'Umbilical Hernia',
                'Unknown':                           'Unknown',
                'Other':                             'Other',
            }
            normalized = proc_map.get(proc_titled, proc_titled)
            df.at[idx, 'procedure'] = normalized
            if normalized not in VALID_PROCEDURES:
                issues.append({'row': idx, 'field': 'procedure', 'value': proc,
                               'issue': f"'{proc}' could not be mapped to a schema procedure — needs manual review"})

    # Duplicate detection
    if 'video_name' in df.columns and 'institution' in df.columns:
        dupes = df[df.duplicated(subset=['video_name', 'institution'], keep=False)]
        for idx in dupes.index:
            issues.append({
                'row': idx,
                'field': 'video_name+institution',
                'value': f"{df.at[idx, 'video_name']} / {df.at[idx, 'institution']}",
                'issue': 'Duplicate: same video_name + institution'
            })

    # Add default columns
    if 'annotation_status' not in df.columns:
        df['annotation_status'] = 'Untagged'
    if 'is_usable' not in df.columns:
        df['is_usable'] = 1
    if 'surgical_approach' not in df.columns:
        df['surgical_approach'] = 'Laparoscopic'
    df['date_added'] = date.today().isoformat()

    return df, issues


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Clean SOAR CSV for MARVL ingestion")
    parser.add_argument('--csv',        required=True, help='Raw SOAR CSV export')
    parser.add_argument('--out-clean',  default='soar_clean.csv')
    parser.add_argument('--out-issues', default='soar_issues.csv')
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found"); sys.exit(1)

    print(f"Loading {csv_path}...")
    df = pd.read_csv(csv_path, dtype=str)
    print(f"  {len(df)} rows, {len(df.columns)} columns")

    df_clean, issues = clean(df)

    df_clean.to_csv(args.out_clean, index=False)
    print(f"\n✓ Cleaned CSV → {args.out_clean}")

    if issues:
        issues_df = pd.DataFrame(issues)
        issues_df.to_csv(args.out_issues, index=False)
        print(f"⚠  Issues log → {args.out_issues}  ({len(issues)} issues, {issues_df['row'].nunique()} rows affected)")
    else:
        print("✓ No issues found")

    # Summary
    print("\n── Summary ──────────────────────────────────────────────────")
    print(f"  Total rows:     {len(df_clean)}")
    if 'anon_status' in df_clean.columns:
        print(f"  anon_status:    {df_clean['anon_status'].value_counts().to_dict()}")
    if 'institution' in df_clean.columns:
        print(f"  institution:    {df_clean['institution'].value_counts().to_dict()}")
    if issues:
        by_field = pd.DataFrame(issues)['field'].value_counts().to_dict()
        print(f"  Issues/field:   {by_field}")
    print("─────────────────────────────────────────────────────────────")
    print("\nNext: python ingest_soar.py --csv soar_clean.csv --db marvl.db")

if __name__ == '__main__':
    main()
