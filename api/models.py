from pydantic import BaseModel
from typing import Optional


class VideoCreate(BaseModel):
    num_id: Optional[int] = None
    video_name: str
    video_ext: Optional[str] = None
    storage_system: Optional[str] = None
    video_path: str
    length: Optional[int] = None
    fps: Optional[float] = None
    procedure: Optional[str] = None
    surgical_approach: Optional[str] = "Laparoscopic"
    institution: Optional[str] = None
    date_recorded: Optional[str] = None
    irb_protocol: Optional[str] = None
    anon_status: Optional[str] = None
    pgs_score: Optional[str] = None
    annotation_status: Optional[str] = "Untagged"
    is_usable: Optional[int] = 1
    notes: Optional[str] = None


class VideoUpdate(BaseModel):
    video_name: Optional[str] = None
    video_ext: Optional[str] = None
    storage_system: Optional[str] = None
    video_path: Optional[str] = None
    length: Optional[int] = None
    fps: Optional[float] = None
    procedure: Optional[str] = None
    surgical_approach: Optional[str] = None
    institution: Optional[str] = None
    date_recorded: Optional[str] = None
    irb_protocol: Optional[str] = None
    anon_status: Optional[str] = None
    pgs_score: Optional[str] = None
    annotation_status: Optional[str] = None
    is_usable: Optional[int] = None
    notes: Optional[str] = None
