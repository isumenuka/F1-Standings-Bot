import json
import os
import contextlib
import psycopg2
from psycopg2.extras import RealDictCursor

DATA_PATH = os.getenv("DATA_PATH", "shared/data.json")
DB_URL = os.getenv("DATABASE_URL")

@contextlib.contextmanager
def get_db_cursor(cursor_factory=None):
    conn = psycopg2.connect(DB_URL)
    try:
        with conn:
            with conn.cursor(cursor_factory=cursor_factory) as cur:
                yield cur
    finally:
        conn.close()

def _init_db():
    if not DB_URL: return
    with get_db_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                real_name TEXT,
                points INTEGER DEFAULT 0,
                avatar_url TEXT
            )
        """)

_init_db()

def load_players():
    """Load all players, sorted by points descending."""
    if DB_URL:
        with get_db_cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM players ORDER BY points DESC")
            return [dict(row) for row in cur.fetchall()]
    else:
        if not os.path.exists(DATA_PATH):
            return []
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            players = json.load(f)
        players.sort(key=lambda p: p["points"], reverse=True)
        return players

def save_players(players):
    """Fallback: Save players list to data.json."""
    if DB_URL: return # Postgres auto-saves on execute
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2, ensure_ascii=False)

def get_next_id(players):
    """Fallback ID gen for JSON."""
    if not players: return 1
    return max(p["id"] for p in players) + 1

def add_player(name, points=0, avatar_url="", real_name=""):
    if DB_URL:
        with get_db_cursor() as cur:
            cur.execute(
                "INSERT INTO players (name, real_name, points, avatar_url) VALUES (%s, %s, %s, %s)",
                (name, real_name, int(points), avatar_url)
            )
        return load_players()
    else:
        players = load_players() or []
        new_player = {
            "id": get_next_id(players),
            "name": name,
            "real_name": real_name,
            "points": int(points),
            "avatar_url": avatar_url
        }
        players.append(new_player)
        save_players(players)
        return players

def update_player(player_id, name=None, points=None, avatar_url=None, real_name=None):
    if DB_URL:
        fields = []
        vals = []
        if name is not None:
            fields.append("name = %s")
            vals.append(name)
        if real_name is not None:
            fields.append("real_name = %s")
            vals.append(real_name)
        if points is not None:
            fields.append("points = %s")
            vals.append(int(points))
        if avatar_url is not None:
            fields.append("avatar_url = %s")
            vals.append(avatar_url)
            
        if not fields: return
        vals.append(int(player_id))
        
        query = f"UPDATE players SET {', '.join(fields)} WHERE id = %s"
        with get_db_cursor() as cur:
            cur.execute(query, tuple(vals))
    else:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for p in raw:
            if p["id"] == int(player_id):
                if name is not None: p["name"] = name
                if real_name is not None: p["real_name"] = real_name
                if points is not None:
                    try:
                        p["points"] = int(points)
                    except (ValueError, TypeError):
                        pass
                if avatar_url is not None: p["avatar_url"] = avatar_url
                break
        save_players(raw)

def delete_player(player_id):
    if DB_URL:
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM players WHERE id = %s", (int(player_id),))
    else:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        raw = [p for p in raw if p["id"] != int(player_id)]
        save_players(raw)

