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
        # Add manual_rank column if it doesn't exist
        cur.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS manual_rank INTEGER;")

_init_db()

def load_players():
    """Load all players, sorted by manual_rank ascending (if set), then points descending."""
    if DB_URL:
        with get_db_cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM players ORDER BY manual_rank ASC NULLS LAST, points DESC")
            return [dict(row) for row in cur.fetchall()]
    else:
        if not os.path.exists(DATA_PATH):
            return []
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            players = json.load(f)
        # Sort by points descending first, then by rank if exists
        players.sort(key=lambda p: p["points"], reverse=True)
        players.sort(key=lambda p: p.get("manual_rank", 9999))
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

def update_ranks(ordered_player_ids):
    """Update manual unk based on ordered list of IDs."""
    if DB_URL:
        with get_db_cursor() as cur:
            # First reset all ranks to NULL
            cur.execute("UPDATE players SET manual_rank = NULL")
            # Then set ranks for provided IDs
            for rank, pid in enumerate(ordered_player_ids, start=1):
                cur.execute("UPDATE players SET manual_rank = %s WHERE id = %s", (rank, int(pid)))
    else:
        players = load_players()
        # Create lookup
        p_dict = {p["id"]: p for p in players}
        
        # Reset all ranks
        for p in players:
            p.pop("manual_rank", None)
            
        # Set new ranks
        for rank, pid in enumerate(ordered_player_ids, start=1):
            if int(pid) in p_dict:
                p_dict[int(pid)]["manual_rank"] = rank
                
        save_players(players)
def bulk_update_players(players_data):
    """
    Apply bulk updates to players.
    'players_data' is a list of dicts: [{'id': 1, 'name': '...', 'points': 10, 'rank': 1}, ...]
    """
    if DB_URL:
        with get_db_cursor() as cur:
            # First, check if we need to update info or just ranks
            for p in players_data:
                pid = int(p["id"])
                name = p.get("name")
                real_name = p.get("real_name")
                points = p.get("points")
                rank = p.get("rank")
                
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
                if rank is not None:
                    fields.append("manual_rank = %s")
                    vals.append(int(rank))
                
                if fields:
                    vals.append(pid)
                    query = f"UPDATE players SET {', '.join(fields)} WHERE id = %s"
                    cur.execute(query, tuple(vals))
    else:
        # JSON fallback
        current_players = load_players()
        p_dict = {p["id"]: p for p in current_players}
        
        for p in players_data:
            pid = int(p["id"])
            if pid in p_dict:
                target = p_dict[pid]
                if "name" in p: target["name"] = p["name"]
                if "real_name" in p: target["real_name"] = p["real_name"]
                if "points" in p: target["points"] = int(p["points"])
                if "rank" in p: target["manual_rank"] = int(p["rank"])
        
        save_players(current_players)

