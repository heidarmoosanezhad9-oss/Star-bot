"""
SQLite database — all tables and helper functions.
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
        state         TEXT DEFAULT ''
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

    CREATE TABLE IF NOT EXISTS orders (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id       INTEGER,
        target        TEXT,        -- channel/group link or username
        target_type   TEXT,        -- 'channel' or 'group'
        members_count INTEGER,
        stars_cost    INTEGER,
        status        TEXT DEFAULT 'pending',   -- pending/approved/rejected/done
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
    """)

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


def claim_daily(user_id: int) -> bool:
    """Returns True if daily stars were awarded, False if already claimed today."""
    conn = get_conn()
    row = conn.execute("SELECT last_daily FROM users WHERE user_id=?", (user_id,)).fetchone()
    today = datetime.date.today().isoformat()
    if row and row["last_daily"] == today:
        conn.close()
        return False
    conn.execute("UPDATE users SET last_daily=?, stars=stars+? WHERE user_id=?",
                 (today, __import__('config').DAILY_STARS, user_id))
    conn.commit()
    conn.close()
    return True


def get_all_users():
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]


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
    """Returns stars awarded or -1 if invalid/already used."""
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
    """Returns True if reward is new (not already recorded)."""
    conn = get_conn()
    existing = conn.execute(
        "SELECT 1 FROM invite_rewards WHERE invitee_id=?", (invitee_id,)
    ).fetchone()
    if existing:
        conn.close()
        return False
    conn.execute(
        "INSERT INTO invite_rewards (inviter_id,invitee_id) VALUES (?,?)",
        (inviter_id, invitee_id)
    )
    conn.execute(
        "UPDATE users SET stars=stars+? WHERE user_id=?",
        (__import__('config').INVITE_STARS, inviter_id)
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
    conn.close()
    return {"users": users, "orders": orders, "pending": pending, "approved": approved}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now():
    return datetime.datetime.utcnow().isoformat(timespec="seconds")
