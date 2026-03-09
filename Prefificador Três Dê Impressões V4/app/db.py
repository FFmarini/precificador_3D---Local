import sqlite3
import sys
from pathlib import Path
from typing import Optional, List


def _app_base_dir() -> Path:
    # EXE: banco ao lado do .exe
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # dev: ao lado do main.py
    return Path(__file__).resolve().parents[1]


DB_PATH = _app_base_dir() / "precificador.db"


def db_connect() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _get_columns(con: sqlite3.Connection, table: str) -> List[str]:
    cur = con.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]


def _ensure_column(con: sqlite3.Connection, table: str, col: str, coldef_sql: str):
    if col not in _get_columns(con, table):
        con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coldef_sql}")


def _ensure_created_at(con: sqlite3.Connection, table: str):
    # SQLite não permite ALTER TABLE com default datetime('now')
    if "created_at" not in _get_columns(con, table):
        con.execute(f"ALTER TABLE {table} ADD COLUMN created_at TEXT")
        con.execute(f"UPDATE {table} SET created_at = datetime('now') WHERE created_at IS NULL")


def db_init():
    con = db_connect()

    con.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")

    con.execute("""
    CREATE TABLE IF NOT EXISTS order_seq (
        id INTEGER PRIMARY KEY CHECK (id=1),
        last_order_no INTEGER NOT NULL
    )""")
    con.execute("INSERT OR IGNORE INTO order_seq (id,last_order_no) VALUES (1,0)")

    con.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        instagram TEXT,
        city TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    _ensure_column(con, "clients", "notes", "TEXT")
    _ensure_created_at(con, "clients")

    con.execute("""
    CREATE TABLE IF NOT EXISTS filaments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        brand TEXT,
        ftype TEXT,
        color TEXT,
        code TEXT,
        price_per_kg REAL DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    for c, d in [
        ("brand", "TEXT"),
        ("ftype", "TEXT"),
        ("color", "TEXT"),
        ("code", "TEXT"),
        ("price_per_kg", "REAL DEFAULT 0"),
        ("notes", "TEXT"),
    ]:
        _ensure_column(con, "filaments", c, d)
    _ensure_created_at(con, "filaments")

    con.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        url TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    _ensure_column(con, "projects", "url", "TEXT")
    _ensure_column(con, "projects", "notes", "TEXT")
    _ensure_created_at(con, "projects")

    con.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no INTEGER NOT NULL,
        created_at TEXT NOT NULL,

        client_id INTEGER NOT NULL,
        project_id INTEGER NOT NULL,
        filament_id INTEGER,

        pieces INTEGER NOT NULL DEFAULT 1,

        time_seconds_per_piece INTEGER NOT NULL DEFAULT 0,
        filament_g_per_piece REAL NOT NULL DEFAULT 0,

        chosen_color TEXT,

        status TEXT NOT NULL DEFAULT 'Orçado',
        payment_method TEXT NOT NULL DEFAULT 'Pix',
        is_paid INTEGER NOT NULL DEFAULT 0,

        notes TEXT,

        filament_price_per_kg REAL NOT NULL DEFAULT 0,
        energy_price_per_kwh REAL NOT NULL DEFAULT 0,
        printer_avg_watts REAL NOT NULL DEFAULT 0,
        machine_cost_per_hour REAL NOT NULL DEFAULT 0,
        labor_cost_fixed REAL NOT NULL DEFAULT 0,
        margin_percent REAL NOT NULL DEFAULT 0,
        round_to REAL NOT NULL DEFAULT 1,

        failure_rate_percent REAL NOT NULL DEFAULT 5,
        overhead_percent REAL NOT NULL DEFAULT 10,
        packaging_cost REAL NOT NULL DEFAULT 0,
        platform_fee_percent REAL NOT NULL DEFAULT 0,
        payment_fee_percent REAL NOT NULL DEFAULT 0,
        shipping_price REAL NOT NULL DEFAULT 0,
        discount_value REAL NOT NULL DEFAULT 0,

        total_cost REAL NOT NULL DEFAULT 0,
        product_price REAL NOT NULL DEFAULT 0,
        fees_estimated REAL NOT NULL DEFAULT 0,
        profit REAL NOT NULL DEFAULT 0,
        final_price REAL NOT NULL DEFAULT 0,

        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (project_id) REFERENCES projects(id),
        FOREIGN KEY (filament_id) REFERENCES filaments(id)
    )""")

    # migrações seguras
    for c, d in [
        ("chosen_color", "TEXT"),
        ("notes", "TEXT"),
        ("profit", "REAL NOT NULL DEFAULT 0"),
        ("fees_estimated", "REAL NOT NULL DEFAULT 0"),
        ("final_price", "REAL NOT NULL DEFAULT 0"),
    ]:
        _ensure_column(con, "orders", c, d)

    con.commit()
    con.close()


def set_setting(key: str, value: Optional[str]):
    con = db_connect()
    if value is None or str(value).strip() == "":
        con.execute("DELETE FROM settings WHERE key=?", (key,))
    else:
        con.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
    con.commit()
    con.close()


def get_setting(key: str) -> Optional[str]:
    con = db_connect()
    row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    con.close()
    return row["value"] if row else None


def next_order_no() -> int:
    con = db_connect()
    cur = con.cursor()
    cur.execute("SELECT last_order_no FROM order_seq WHERE id=1")
    last_no = int(cur.fetchone()[0])
    new_no = last_no + 1
    cur.execute("UPDATE order_seq SET last_order_no=? WHERE id=1", (new_no,))
    con.commit()
    con.close()
    return new_no


def format_order_code(order_no: int) -> str:
    return f"TD-{int(order_no):06d}"
