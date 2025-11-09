# utils/db.py
import sqlite3
import logging

log = logging.getLogger("db")

def init_sqlite(path="orders.db"):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            flow TEXT,
            asset TEXT,
            asset_amount REAL,
            base_usdt REAL,
            fee_usdt REAL,
            total_usdt REAL,
            username TEXT,
            user_id INTEGER,
            wallet TEXT,
            status TEXT
        );
    """)
    conn.commit()
    conn.close()

def log_to_sqlite(row: dict, path="orders.db"):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders (ts, flow, asset, asset_amount, base_usdt, fee_usdt, total_usdt,
                            username, user_id, wallet, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        row.get("ts"), row.get("flow"), row.get("asset"), row.get("asset_amount"),
        row.get("base_usdt"), row.get("fee_usdt"), row.get("total_usdt"),
        row.get("username"), row.get("user_id"), row.get("wallet"), row.get("status")
    ))
    conn.commit()
    conn.close()

# ----- Google Sheets -----
_gs_worksheet = None

def init_google_sheets(json_path, sheet_name):
    global _gs_worksheet
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        scope = ["https://spreadsheets.google.com/feeds",
                 "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(json_path, scope)
        client = gspread.authorize(creds)
        try:
            sh = client.open(sheet_name)
        except Exception:
            sh = client.create(sheet_name)
        try:
            _gs_worksheet = sh.worksheet("Orders")
        except Exception:
            _gs_worksheet = sh.add_worksheet(title="Orders", rows="1000", cols="20")
            _gs_worksheet.append_row(
                ["ts", "flow", "asset", "asset_amount", "base_usdt", "fee_usdt", "total_usdt",
                 "username", "user_id", "wallet", "status"]
            )
    except Exception as e:
        log.error(f"Google Sheets init failed: {e}")

def log_to_google_sheets(row: dict):
    if _gs_worksheet is None:
        return
    try:
        _gs_worksheet.append_row([
            row.get("ts"), row.get("flow"), row.get("asset"), row.get("asset_amount"),
            row.get("base_usdt"), row.get("fee_usdt"), row.get("total_usdt"),
            row.get("username"), row.get("user_id"), row.get("wallet"), row.get("status")
        ])
    except Exception as e:
        log.error(f"Google Sheets append failed: {e}")

def log_request(row: dict, enable_sqlite=True, enable_gs=False):
    if enable_sqlite:
        log_to_sqlite(row)
    if enable_gs:
        log_to_google_sheets(row)
