-- MARVL Lab surgical video database
-- schema v1.2 - laparoscopy demo
-- updated after meeting w alan 3/3


-- videos
CREATE TABLE IF NOT EXISTS videos (
    num_id              INTEGER,
    video_id            TEXT PRIMARY KEY,
    parent_video_id     TEXT,           -- for clips - points back to original
    video_name          TEXT NOT NULL,
    video_ext           TEXT CHECK(video_ext IN ('mp4', 'avi', 'bmp')),
    storage_system       TEXT CHECK(storage_system IN ('Pasteur', 'SC Cluster', 'GDrive')),
    video_path          TEXT NOT NULL,  -- relative path within the storage system
    length              INTEGER,        -- unit TBC - seconds or frames, confirm w alan
    fps                 REAL,
    procedure           TEXT CHECK(procedure IN (
                            'Cholecystectomy',
                            'Appendectomy',
                            'TEP Inguinal Hernia Repair',
                            'TAPP Inguinal Hernia Repair',
                            'Hysterectomy',
                            'Fundoplication',
                            'Umbilical Hernia',
                            'Colectomy',
                            'Sleeve Gastrectomy',
                            'Diagnostic Lap/Port Placement',
                            'Bilateral Salpingooophrectomy',
                            'Open',
                            'Unknown',
                            'Other'
                        )),
    surgical_approach   TEXT DEFAULT 'Laparoscopic',
    surgeon_level       TEXT,
    surgeon_id          TEXT,
    institution         TEXT CHECK(institution IN (
                            'Intermountain',
                            'SST',
                            'HeiChole',
                            'Cholec80',
                            'UTSW',
                            'Stanford',
                            'AutoLaparo',
                            'Medica Sur-Cortes',
                            'Medica Sur-Hernandez',
                            'München Klinik Harlaching',
                            'Queens University'
                        )),
    date_recorded       DATE,
    irb_protocol        TEXT,
    anon_status         TEXT CHECK(anon_status IN ('anonymized', 'raw', 'missing')),
    pgs_score           TEXT,
    patient_case_id     TEXT,
    video_quality       TEXT,
    contributed_by      TEXT,
    date_added          DATE,
    annotation_status   TEXT DEFAULT 'Untagged',
    is_usable           INTEGER DEFAULT 1,  -- 0 = excluded
    notes               TEXT,

    FOREIGN KEY (parent_video_id) REFERENCES videos(video_id)
);

-- annotations - med students populate this
CREATE TABLE IF NOT EXISTS annotations (
    annotation_id       TEXT PRIMARY KEY,
    video_id            TEXT NOT NULL,
    annotator           TEXT,
    annotation_type     TEXT,
    label               TEXT,
    timestamp_start     INTEGER,
    timestamp_end       INTEGER,
    confidence          TEXT,
    date_annotated      DATE,
    notes               TEXT,

    FOREIGN KEY (video_id) REFERENCES videos(video_id)
);

-- contributors
CREATE TABLE IF NOT EXISTS contributors (
    contributor_id      TEXT PRIMARY KEY,
    full_name           TEXT NOT NULL,
    role                TEXT,
    department          TEXT,
    institution         TEXT,
    contact_email       TEXT,
    date_added          DATE
);

-- example row (placeholder values only)
-- INSERT INTO videos (num_id, video_id, video_name, video_ext, video_path, length, fps, procedure, anon_status, irb_protocol, is_usable, institution, storage_system)
-- VALUES
--     (1, 'VID001', 'example-video', 'mp4', '/storage/dataset/YYYY-MM-DD/example-video.mp4', 90000, 30, 'Cholecystectomy', 'anonymized', 'IRB-XXXXX', 1, 'Intermountain', 'Pasteur');

-- queries

-- all cholecystectomies
-- SELECT * FROM videos WHERE procedure = 'Cholecystectomy';

-- usable videos only
-- SELECT * FROM videos WHERE is_usable = 1;

-- untagged
-- SELECT video_id, video_name, procedure FROM videos WHERE annotation_status = 'Untagged';

-- by institution
-- SELECT institution, COUNT(*) FROM videos GROUP BY institution;

-- by procedure type
-- SELECT procedure, COUNT(*) FROM videos GROUP BY procedure;

-- anonymized only
-- SELECT * FROM videos WHERE anon_status = 'anonymized';

-- annotations for a video
-- SELECT * FROM annotations WHERE video_id = 'VID039';
