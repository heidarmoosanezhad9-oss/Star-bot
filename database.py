"""
SQLite database — all tables and helper functions.
New tables: settings (dynamic config), text_overrides (admin-editable texts),
            earn_channel_claims (track who already claimed per channel),
            user_lang (per-user language preference).
"""

import sqlite3
import datetime
from config import DATABASE_PATH


def get_conn():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id       INTEGER PRIMARY KEY,
        username      TEXT,
        full_name     TEXT,
        stars         INTEGER DEFAULT 0,
        invited_by    INTEGER,
        joined_at     TEXT,
        last_daily    TEXT,
        state         TEXT DEFAULT '',
        lang          TEXT DEFAULT 'fa'
    );

    CREATE TABLE IF NOT EXISTS required_channels (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id    TEXT UNIQUE,
        channel_name  TEXT,
        invite_link   TEXT
    );

    CREATE TABLE IF NOT EXISTS earn_channels (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id    TEXT UNIQUE,
        channel_name  TEXT,
        invite_link   TEXT,
        stars_reward  INTEGER DEFAULT 3
    );

    CREATE TABLE IF NOT EXISTS earn_channel_claims (
        user_id       INTEGER,
        channel_id    TEXT,
        PRIMARY KEY (user_id, channel_id)
    );

    CREATE TABLE IF NOT EXISTS orders (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id       INTEGER,
        target        TEXT,
        target_type   TEXT,
        members_count INTEGER,
        stars_cost    INTEGER,
        status        TEXT DEFAULT 'pending',
        created_at    TEXT,
        note          TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS star_codes (
        code          TEXT PRIMARY KEY,
        stars         INTEGER,
        max_uses      INTEGER DEFAULT 1,
        uses          INTEGER DEFAULT 0,
        created_at    TEXT
    );

    CREATE TABLE IF NOT EXISTS code_redemptions (
        user_id       INTEGER,
        code          TEXT,
        PRIMARY KEY (user_id, code)
    );

    CREATE TABLE IF NOT EXISTS invite_rewards (
        inviter_id    INTEGER,
        invitee_id    INTEGER PRIMARY KEY
    );

    CREATE TABLE IF NOT EXISTS settings (
        key           TEXT PRIMARY KEY,
        value         TEXT
    );

    CREATE TABLE IF NOT EXISTS text_overrides (
        lang          TEXT,
        key           TEXT,
        value         TEXT,
        PRIMARY KEY (lang, key)
    );
    """)

    # Seed default settings if not present
    defaults = {
        "daily_stars":      "5",
        "invite_stars":     "10",
        "join_stars":       "3",
        "stars_per_member": "5",
        "buy_contact":      "@admin",
        "bot_username":     "user_info_bot",
        "results_channel":  "-1003965394113",
        "min_order":        "10",
        "max_order":        "10000",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key,value) VALUES (?,?)", (k, v))

    conn.commit()
    conn.close()


# ── Settings ───────────────────────────────────────────────────────────────────

def get_setting(key: str, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    if row:
        return row["value"]
    return str(default) if default is not None else None


def set_setting(key: str, value: str):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()


def get_all_settings():
    conn = get_conn()
    rows = conn.execute("SELECT key,value FROM settings ORDER BY key").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def get_int_setting(key: str, default: int = 0) -> int:
    v = get_setting(key)
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


# ── Text overrides ─────────────────────────────────────────────────────────────

def get_text_overrides(lang: str) -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT key,value FROM text_overrides WHERE lang=?", (lang,)).fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def set_text_override(lang: str, key: str, value: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO text_overrides (lang,key,value) VALUES (?,?,?)",
        (lang, key, value)
    )
    conn.commit()
    conn.close()


def delete_text_override(lang: str, key: str):
    conn = get_conn()
    conn.execute("DELETE FROM text_overrides WHERE lang=? AND key=?", (lang, key))
    conn.commit()
    conn.close()


# ── Users ──────────────────────────────────────────────────────────────────────

def get_user(user_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row


def upsert_user(user_id: int, username: str, full_name: str, invited_by: int = None):
    conn = get_conn()
    existing = conn.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO users (user_id,username,full_name,invited_by,joined_at) VALUES (?,?,?,?,?)",
            (user_id, username, full_name, invited_by, _now())
        )
        conn.commit()
    conn.close()


def update_stars(user_id: int, delta: int):
    conn = get_conn()
    conn.execute("UPDATE users SET stars=MAX(0,stars+?) WHERE user_id=?", (delta, user_id))
    conn.commit()
    conn.close()


def set_state(user_id: int, state: str):
    conn = get_conn()
    conn.execute("UPDATE users SET state=? WHERE user_id=?", (state, user_id))
    conn.commit()
    conn.close()


def get_state(user_id: int) -> str:
    conn = get_conn()
    row = conn.execute("SELECT state FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row["state"] if row else ""


def get_user_lang(user_id: int) -> str:
    conn = get_conn()
    row = conn.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if row and row["lang"]:
        return row["lang"]
    return "fa"


def set_user_lang(user_id: int, lang: str):
    conn = get_conn()
    conn.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))
    conn.commit()
    conn.close()


def claim_daily(user_id: int) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT last_daily FROM users WHERE user_id=?", (user_id,)).fetchone()
    today = datetime.date.today().isoformat()
    if row and row["last_daily"] == today:
        conn.close()
        return False
    daily = get_int_setting("daily_stars", 5)
    conn.execute(
        "UPDATE users SET last_daily=?, stars=stars+? WHERE user_id=?",
        (today, daily, user_id)
    )
    conn.commit()
    conn.close()
    return True


def get_all_users():
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]


def set_user_stars(user_id: int, amount: int):
    conn = get_conn()
    conn.execute("UPDATE users SET stars=? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()


# ── Required channels ──────────────────────────────────────────────────────────

def get_required_channels():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM required_channels").fetchall()
    conn.close()
    return rows


def add_required_channel(channel_id: str, name: str, link: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO required_channels (channel_id,channel_name,invite_link) VALUES (?,?,?)",
        (channel_id, name, link)
    )
    conn.commit()
    conn.close()


def remove_required_channel(channel_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM required_channels WHERE channel_id=?", (channel_id,))
    conn.commit()
    conn.close()


# ── Earn channels ──────────────────────────────────────────────────────────────

def get_earn_channels():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM earn_channels").fetchall()
    conn.close()
    return rows


def add_earn_channel(channel_id: str, name: str, link: str, stars: int):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO earn_channels (channel_id,channel_name,invite_link,stars_reward) VALUES (?,?,?,?)",
        (channel_id, name, link, stars)
    )
    conn.commit()
    conn.close()


def remove_earn_channel(channel_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM earn_channels WHERE channel_id=?", (channel_id,))
    conn.commit()
    conn.close()


def has_claimed_earn(user_id: int, channel_id: str) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM earn_channel_claims WHERE user_id=? AND channel_id=?",
        (user_id, channel_id)
    ).fetchone()
    conn.close()
    return row is not None


def record_earn_claim(user_id: int, channel_id: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO earn_channel_claims (user_id,channel_id) VALUES (?,?)",
        (user_id, channel_id)
    )
    conn.commit()
    conn.close()


# ── Orders ─────────────────────────────────────────────────────────────────────

def create_order(user_id: int, target: str, target_type: str, members: int, cost: int):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO orders (user_id,target,target_type,members_count,stars_cost,created_at) VALUES (?,?,?,?,?,?)",
        (user_id, target, target_type, members, cost, _now())
    )
    order_id = cur.lastrowid
    conn.commit()
    conn.close()
    return order_id


def get_order(order_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    conn.close()
    return row


def get_user_orders(user_id: int):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()
    conn.close()
    return rows


def get_pending_orders():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM orders WHERE status='pending' ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def update_order_status(order_id: int, status: str, note: str = ""):
    conn = get_conn()
    conn.execute("UPDATE orders SET status=?,note=? WHERE id=?", (status, note, order_id))
    conn.commit()
    conn.close()


# ── Star codes ─────────────────────────────────────────────────────────────────

def create_star_code(code: str, stars: int, max_uses: int):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO star_codes (code,stars,max_uses,uses,created_at) VALUES (?,?,?,0,?)",
        (code, stars, max_uses, _now())
    )
    conn.commit()
    conn.close()


def redeem_star_code(user_id: int, code: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM star_codes WHERE code=?", (code,)).fetchone()
    if not row or row["uses"] >= row["max_uses"]:
        conn.close()
        return -1
    already = conn.execute(
        "SELECT 1 FROM code_redemptions WHERE user_id=? AND code=?", (user_id, code)
    ).fetchone()
    if already:
        conn.close()
        return -1
    conn.execute("UPDATE star_codes SET uses=uses+1 WHERE code=?", (code,))
    conn.execute("INSERT INTO code_redemptions (user_id,code) VALUES (?,?)", (user_id, code))
    conn.execute("UPDATE users SET stars=stars+? WHERE user_id=?", (row["stars"], user_id))
    conn.commit()
    conn.close()
    return row["stars"]


def get_all_star_codes():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM star_codes ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows


def delete_star_code(code: str):
    conn = get_conn()
    conn.execute("DELETE FROM star_codes WHERE code=?", (code,))
    conn.commit()
    conn.close()


# ── Invites ────────────────────────────────────────────────────────────────────

def record_invite_reward(inviter_id: int, invitee_id: int) -> bool:
    conn = get_conn()
    existing = conn.execute(
        "SELECT 1 FROM invite_rewards WHERE invitee_id=?", (invitee_id,)
    ).fetchone()
    if existing:
        conn.close()
        return False
    invite_stars = get_int_setting("invite_stars", 10)
    conn.execute(
        "INSERT INTO invite_rewards (inviter_id,invitee_id) VALUES (?,?)",
        (inviter_id, invitee_id)
    )
    conn.execute(
        "UPDATE users SET stars=stars+? WHERE user_id=?",
        (invite_stars, inviter_id)
    )
    conn.commit()
    conn.close()
    return True


def get_invite_count(user_id: int) -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM invite_rewards WHERE inviter_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


# ── Stats ──────────────────────────────────────────────────────────────────────

def get_stats():
    conn = get_conn()
    users    = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    orders   = conn.execute("SELECT COUNT(*) as c FROM orders").fetchone()["c"]
    pending  = conn.execute("SELECT COUNT(*) as c FROM orders WHERE status='pending'").fetchone()["c"]
    approved = conn.execute("SELECT COUNT(*) as c FROM orders WHERE status='approved'").fetchone()["c"]
    rejected = conn.execute("SELECT COUNT(*) as c FROM orders WHERE status='rejected'").fetchone()["c"]
    stars_total = conn.execute("SELECT COALESCE(SUM(stars),0) as s FROM users").fetchone()["s"]
    conn.close()
    return {
        "users": users, "orders": orders, "pending": pending,
        "approved": approved, "rejected": rejected, "stars_total": stars_total
    }


# ── User management (admin) ────────────────────────────────────────────────────

def get_user_by_id(user_id: int):
    return get_user(user_id)


def search_users(query: str):
    conn = get_conn()
    q = f"%{query}%"
    rows = conn.execute(
        "SELECT * FROM users WHERE username LIKE ? OR full_name LIKE ? OR CAST(user_id AS TEXT) LIKE ? LIMIT 20",
        (q, q, q)
    ).fetchall()
    conn.close()
    return rows


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now():
    return datetime.datetime.utcnow().isoformat(timespec="seconds")
