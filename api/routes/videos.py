import re
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..db import get_conn
from ..models import VideoCreate, VideoUpdate

router = APIRouter(prefix="/videos", tags=["videos"])


def _make_video_id(num_id, video_name):
    if num_id is not None:
        return f"VID{int(num_id):03d}"
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", str(video_name))
    return f"VID_{safe}"


def _humanize_db_error(e: Exception, video_id: str) -> str:
    """Turn a raw sqlite constraint error into a message the user can act on."""
    msg = str(e)
    m = re.match(r"UNIQUE constraint failed: videos\.(\w+)", msg)
    if m:
        if m.group(1) == "video_id":
            return (
                f"A video with this name/ID already exists (video_id: {video_id}). "
                "Try a different Video Name, or set a Numeric ID to make it unique."
            )
        return f"A video with this {m.group(1)} already exists."
    m = re.match(r"NOT NULL constraint failed: videos\.(\w+)", msg)
    if m:
        return f"'{m.group(1)}' is required"
    m = re.match(r"CHECK constraint failed: (\w+)", msg)
    if m:
        return f"That value isn't allowed for '{m.group(1)}'"
    return msg


@router.get("/")
def list_videos(
    institution: Optional[str] = None,
    procedure: Optional[str] = None,
    anon_status: Optional[str] = None,
    annotation_status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
):
    conn = get_conn()
    query = "SELECT * FROM videos WHERE 1=1"
    params = []

    if institution:
        query += " AND institution = ?"
        params.append(institution)
    if procedure:
        query += " AND procedure = ?"
        params.append(procedure)
    if anon_status:
        query += " AND anon_status = ?"
        params.append(anon_status)
    if annotation_status:
        query += " AND annotation_status = ?"
        params.append(annotation_status)
    if search:
        query += " AND (video_name LIKE ? OR video_path LIKE ? OR institution LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]

    query += " ORDER BY num_id LIMIT ? OFFSET ?"
    params += [limit, offset]

    rows = conn.execute(query, params).fetchall()
    total = conn.execute(
        query.replace("SELECT *", "SELECT COUNT(*)").split("ORDER BY")[0],
        params[:-2],
    ).fetchone()[0]
    conn.close()
    return {"total": total, "results": [dict(r) for r in rows]}


@router.get("/{video_id}")
def get_video(video_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM videos WHERE video_id = ?", (video_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Video not found")
    return dict(row)


@router.post("/", status_code=201)
def create_video(video: VideoCreate):
    video_id = _make_video_id(video.num_id, video.video_name)
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO videos (
                num_id, video_id, video_name, video_ext,
                storage_system, video_path, length, fps,
                procedure, institution, date_recorded, anon_status,
                irb_protocol, pgs_score,
                surgical_approach, annotation_status, is_usable, notes, date_added
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                video.num_id, video_id, video.video_name, video.video_ext,
                video.storage_system, video.video_path, video.length, video.fps,
                video.procedure, video.institution, video.date_recorded, video.anon_status,
                video.irb_protocol, video.pgs_score,
                video.surgical_approach, video.annotation_status, video.is_usable,
                video.notes, date.today().isoformat(),
            ),
        )
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=_humanize_db_error(e, video_id))
    conn.close()
    return {"video_id": video_id}


@router.put("/{video_id}")
def update_video(video_id: str, update: VideoUpdate):
    conn = get_conn()
    if not conn.execute("SELECT 1 FROM videos WHERE video_id = ?", (video_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Video not found")

    fields = {k: v for k, v in update.model_dump().items() if v is not None}
    if not fields:
        conn.close()
        return {"message": "No fields to update"}

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    try:
        conn.execute(
            f"UPDATE videos SET {set_clause} WHERE video_id = ?",
            list(fields.values()) + [video_id],
        )
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=_humanize_db_error(e, video_id))
    conn.close()
    return {"message": "Updated", "video_id": video_id}


@router.delete("/{video_id}", status_code=204)
def delete_video(video_id: str):
    conn = get_conn()
    if not conn.execute("SELECT 1 FROM videos WHERE video_id = ?", (video_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Video not found")
    conn.execute("DELETE FROM videos WHERE video_id = ?", (video_id,))
    conn.commit()
    conn.close()
