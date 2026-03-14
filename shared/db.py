import json
import os

DATA_PATH = os.getenv("DATA_PATH", "shared/data.json")


def load_players():
    """Load all players from data.json, sorted by points descending."""
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        players = json.load(f)
    players.sort(key=lambda p: p["points"], reverse=True)
    return players


def save_players(players):
    """Save players list to data.json."""
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2, ensure_ascii=False)


def get_next_id(players):
    """Get next available player ID."""
    if not players:
        return 1
    return max(p["id"] for p in players) + 1


def add_player(name, points=0, avatar_url=""):
    """Add a new player and return updated list."""
    players = load_players()
    new_player = {
        "id": get_next_id(players),
        "name": name,
        "points": int(points),
        "avatar_url": avatar_url
    }
    players.append(new_player)
    save_players(players)
    return players


def update_player(player_id, name=None, points=None, avatar_url=None):
    """Update a player by ID."""
    players = load_players()
    # Reload raw (unsorted) to update
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    for p in raw:
        if p["id"] == int(player_id):
            if name is not None:
                p["name"] = name
            if points is not None:
                p["points"] = int(points)
            if avatar_url is not None:
                p["avatar_url"] = avatar_url
            break
    save_players(raw)


def delete_player(player_id):
    """Delete a player by ID."""
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    raw = [p for p in raw if p["id"] != int(player_id)]
    save_players(raw)
