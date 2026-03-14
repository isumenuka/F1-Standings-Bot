import os
import sys
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
import requests

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

load_dotenv()

from shared.db import (
    load_players, add_player, update_player, delete_player, save_players, update_ranks
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


# ── Auth ──────────────────────────────────────────────────────────────────────
def is_logged_in():
    return session.get("logged_in") is True


# ── Image Upload ──────────────────────────────────────────────────────────────
def upload_image(file_obj):
    """Upload image to a free image host and return the URL."""
    url = "https://freeimage.host/api/1/upload"
    data = {
        "key": os.getenv("IMAGE_HOST_KEY", "6d207e02198a847aa98d0a2a901485a5"),
        "action": "upload",
        "format": "json"
    }
    files = {"source": file_obj}
    try:
        resp = requests.post(url, data=data, files=files, timeout=15)
        resp.raise_for_status()
        return resp.json()["image"]["url"]
    except Exception as e:
        print(f"Image upload failed: {e}")
        return None



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        flash("❌ Wrong password. Try again.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if not is_logged_in():
        return redirect(url_for("login"))
    players = load_players()
    return render_template("index.html", players=players)


# ── Add Player ────────────────────────────────────────────────────────────────
@app.route("/add", methods=["POST"])
def add():
    if not is_logged_in():
        return redirect(url_for("login"))
    name = request.form.get("name", "").strip()
    real_name = request.form.get("real_name", "").strip()
    points = request.form.get("points", "0").strip()
    avatar_url = request.form.get("avatar_url", "").strip()
    
    avatar_file = request.files.get("avatar")
    if avatar_file and avatar_file.filename:
        uploaded_url = upload_image(avatar_file)
        if uploaded_url:
            avatar_url = uploaded_url
        else:
            flash("⚠️ Failed to upload image, but player will be added anyway.", "warning")

    if not name:
        flash("❌ Player name cannot be empty.", "error")
        return redirect(url_for("index"))
    try:
        pts = int(points)
    except ValueError:
        pts = 0
    add_player(name, pts, avatar_url, real_name)
    flash(f"✅ Player '{name}' added with {pts} points!", "success")
    return redirect(url_for("index"))


# ── Update Player ─────────────────────────────────────────────────────────────
@app.route("/update/<int:player_id>", methods=["POST"])
def update(player_id):
    if not is_logged_in():
        return redirect(url_for("login"))
    name = request.form.get("name", "").strip() or None
    real_name = request.form.get("real_name", "").strip() or None
    points_raw = request.form.get("points", "").strip()
    points = int(points_raw) if points_raw else None
    avatar_url = request.form.get("avatar_url", "").strip() or None

    avatar_file = request.files.get("avatar")
    if avatar_file and avatar_file.filename:
        uploaded_url = upload_image(avatar_file)
        if uploaded_url:
            avatar_url = uploaded_url
        else:
            flash("⚠️ Failed to upload image, standard update applied.", "warning")

    update_player(player_id, name=name, points=points, avatar_url=avatar_url, real_name=real_name)
    flash("✅ Player updated!", "success")
    return redirect(url_for("index"))


# ── Delete Player ─────────────────────────────────────────────────────────────
@app.route("/delete/<int:player_id>", methods=["POST"])
def delete(player_id):
    if not is_logged_in():
        return redirect(url_for("login"))
    delete_player(player_id)
    flash("🗑️ Player deleted.", "success")
    return redirect(url_for("index"))


# ── Reorder / Set Exact Points ─────────────────────────────────────────────────
@app.route("/set_points/<int:player_id>", methods=["POST"])
def set_points(player_id):
    if not is_logged_in():
        return redirect(url_for("login"))
    points_raw = request.form.get("points", "0").strip()
    try:
        points = int(points_raw)
    except ValueError:
        points = 0
    update_player(player_id, points=points)
    flash("✅ Points updated!", "success")
    return redirect(url_for("index"))


# ── Update Ranks (Drag & Drop) ────────────────────────────────────────────────
@app.route("/update_ranks", methods=["POST"])
def update_ranks_route():
    if not is_logged_in():
        return {"error": "Unauthorized"}, 401
    
    data = request.get_json()
    if not data or "ordered_ids" not in data:
        return {"error": "Bad Request"}, 400
        
    update_ranks(data["ordered_ids"])
    return {"success": True}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
