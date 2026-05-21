import sqlite3
import os
from pathlib import Path

_default = Path(__file__).parent.parent / "marvl.db"
DB_PATH = Path(os.getenv("DB_PATH", str(_default)))


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
