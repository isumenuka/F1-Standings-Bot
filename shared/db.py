import json
import os
import contextlib
import psycopg2
from psycopg2.extras import RealDictCursor

DATA_PATH = os.getenv("DATA_PATH", "shared/data.json")
DB_URL = os.getenv("DATABASE_URL")

@contextlib.contextmanager
def get_db_cursor(cursor_factory=None):
    url = DB_URL
    if url and "render.com" in url and "sslmode" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    
    try:
        conn = psycopg2.connect(url)
        try:
            with conn:
                with conn.cursor(cursor_factory=cursor_factory) as cur:
                    yield cur
        finally:
            conn.close()
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def _init_db():
    if not DB_URL:
        print("No DATABASE_URL found, skipping DB initialization (using JSON fallback).")
        return
    try:
        with get_db_cursor() as cur:
            # Players table
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
            
            # Bot Settings table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            # Custom Commands table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS custom_commands (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    response TEXT NOT NULL
                )
            """)
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        # We don't crash here so the app can at least start with JSON fallback if needed
        # (Though if DB_URL is set, most functions will still try to use it and fail later)

_init_db()

def get_setting(key, default=None):
    """Retrieve a bot setting."""
    if DB_URL:
        with get_db_cursor() as cur:
            cur.execute("SELECT value FROM bot_settings WHERE key = %s", (key,))
            result = cur.fetchone()
            return result[0] if result else default
    else:
        if not os.path.exists(DATA_PATH): return default
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list): return default
        return data.get("settings", {}).get(key, default)

def set_setting(key, value):
    """Save a bot setting."""
    if DB_URL:
        with get_db_cursor() as cur:
            cur.execute("""
                INSERT INTO bot_settings (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (key, str(value)))
    else:
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"players": [], "settings": {}}
            
        if isinstance(data, list):
            data = {"players": data, "settings": {}}
            
        if "settings" not in data: data["settings"] = {}
        data["settings"][key] = str(value)
        
        save_all_data(data)

def save_all_data(data):
    """Save the entire JSON object (players + settings)."""
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

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
            data = json.load(f)
        
        if isinstance(data, dict):
            players = data.get("players", [])
        else:
            players = data
            
        players.sort(key=lambda p: p["points"], reverse=True)
        players.sort(key=lambda p: p.get("manual_rank", 9999))
        return players

def save_players(players):
    """Save players list to data.json."""
    if DB_URL: return
    
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"players": [], "settings": {}}

    if isinstance(data, list):
        data = {"players": data, "settings": {}}
        
    data["players"] = players
    save_all_data(data)

def get_next_id(players):
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
        players = load_players()
        for p in players:
            if p["id"] == int(player_id):
                if name is not None: p["name"] = name
                if real_name is not None: p["real_name"] = real_name
                if points is not None: p["points"] = int(points)
                if avatar_url is not None: p["avatar_url"] = avatar_url
                break
        save_players(players)

def delete_player(player_id):
    if DB_URL:
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM players WHERE id = %s", (int(player_id),))
    else:
        players = load_players()
        players = [p for p in players if p["id"] != int(player_id)]
        save_players(players)

def update_ranks(ordered_player_ids):
    if DB_URL:
        with get_db_cursor() as cur:
            cur.execute("UPDATE players SET manual_rank = NULL")
            for rank, pid in enumerate(ordered_player_ids, start=1):
                cur.execute("UPDATE players SET manual_rank = %s WHERE id = %s", (rank, int(pid)))
    else:
        players = load_players()
        p_dict = {p["id"]: p for p in players}
        for p in players: p.pop("manual_rank", None)
        for rank, pid in enumerate(ordered_player_ids, start=1):
            if int(pid) in p_dict:
                p_dict[int(pid)]["manual_rank"] = rank
        save_players(players)

def bulk_update_players(players_data):
    if DB_URL:
        with get_db_cursor() as cur:
            for p in players_data:
                pid = int(p["id"])
                name, real_name, points, rank = p.get("name"), p.get("real_name"), p.get("points"), p.get("rank")
                fields, vals = [], []
                if name: fields.append("name = %s"); vals.append(name)
                if real_name: fields.append("real_name = %s"); vals.append(real_name)
                if points is not None: fields.append("points = %s"); vals.append(int(points))
                if rank: fields.append("manual_rank = %s"); vals.append(int(rank))
                if fields:
                    vals.append(pid)
                    cur.execute(f"UPDATE players SET {', '.join(fields)} WHERE id = %s", tuple(vals))
    else:
        players = load_players()
        p_dict = {p["id"]: p for p in players}
        for p in players_data:
            pid = int(p["id"])
            if pid in p_dict:
                target = p_dict[pid]
                if "name" in p: target["name"] = p["name"]
                if "real_name" in p: target["real_name"] = p["real_name"]
                if "points" in p: target["points"] = int(p["points"])
                if "rank" in p: target["manual_rank"] = int(p["rank"])
        save_players(players)

# ── Custom Commands ───────────────────────────────────────────────────────────

def get_custom_commands():
    if DB_URL:
        try:
            with get_db_cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM custom_commands ORDER BY name ASC")
                return cur.fetchall()
        except Exception as e:
            print(f"Error getting custom commands: {e}")
            return []
    return []

def add_custom_command(name, description, response):
    name = name.lower().strip().replace(" ", "-").replace("/", "")
    if not name: return False
    
    if DB_URL:
        try:
            with get_db_cursor() as cur:
                cur.execute("""
                    INSERT INTO custom_commands (name, description, response)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (name) DO UPDATE SET
                        description = EXCLUDED.description,
                        response = EXCLUDED.response
                """, (name, description, response))
            return True
        except Exception as e:
            print(f"Error adding custom command: {e}")
            return False
    return False

def delete_custom_command(cmd_id):
    if DB_URL:
        try:
            with get_db_cursor() as cur:
                cur.execute("DELETE FROM custom_commands WHERE id = %s", (int(cmd_id),))
            return True
        except Exception as e:
            print(f"Error deleting custom command: {e}")
            return False
    return False

def update_custom_command(cmd_id, name, response):
    name = name.lower().strip().replace(" ", "-").replace("/", "")
    if not name: return False
    
    if DB_URL:
        try:
            with get_db_cursor() as cur:
                cur.execute("""
                    UPDATE custom_commands 
                    SET name = %s, response = %s
                    WHERE id = %s
                """, (name, response, int(cmd_id)))
            return True
        except Exception as e:
            print(f"Error updating custom command: {e}")
            return False
    return False
