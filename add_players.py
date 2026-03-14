import sys
import os
import requests

sys.path.insert(0, os.path.dirname(__file__))
from shared.db import add_player

players = [
    ("wolfygear", 25),
    ("Road2okochaZa", 15),
    ("sajipramu", 10),
    ("Sageee_25", 0),
    ("Devisser96", 0),
    ("Harshana_Kalhara", 0),
    ("shehan4real95", 0),
    ("Dyeti9", 0),
    ("G4S_SL", 0),
    ("rmrbavsfd2zo", 0)
]

print("--- ADDING TO LOCAL DATABASE ---")
for name, points in players:
    add_player(name=name, points=points, avatar_url="", real_name="")
    print(f"Added {name} ({points} pts)")

print("\n--- ADDING TO LIVE RENDER SERVICE ---")
url_base = "https://f1-standings-web.onrender.com"
password = os.getenv("ADMIN_PASSWORD", "admin123")

print(f"Logging into {url_base}...")
s = requests.Session()
try:
    r = s.post(f"{url_base}/login", data={"password": password}, timeout=10)
    if "logout" in r.text.lower() or "add new player" in r.text.lower() or "admin123" not in r.text:
        print("Successfully logged in.")
        for name, points in players:
            r_add = s.post(f"{url_base}/add", data={"name": name, "points": points, "real_name": "", "avatar_url": ""})
            if r_add.status_code == 200:
                print(f"Live: Added {name} ({points} pts)")
            else:
                print(f"Live: Failed to add {name}. Code: {r_add.status_code}")
    else:
        print("Failed to login to live service using default password.")
except Exception as e:
    print(f"Live error: {e}")
