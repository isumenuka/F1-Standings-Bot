import os
import sys
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

load_dotenv()

from shared.db import (
    load_players, add_player, update_player, delete_player, save_players
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


# ── Auth ──────────────────────────────────────────────────────────────────────
def is_logged_in():
    return session.get("logged_in") is True


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
    points = request.form.get("points", "0").strip()
    avatar_url = request.form.get("avatar_url", "").strip()
    if not name:
        flash("❌ Player name cannot be empty.", "error")
        return redirect(url_for("index"))
    try:
        pts = int(points)
    except ValueError:
        pts = 0
    add_player(name, pts, avatar_url)
    flash(f"✅ Player '{name}' added with {pts} points!", "success")
    return redirect(url_for("index"))


# ── Update Player ─────────────────────────────────────────────────────────────
@app.route("/update/<int:player_id>", methods=["POST"])
def update(player_id):
    if not is_logged_in():
        return redirect(url_for("login"))
    name = request.form.get("name", "").strip() or None
    points_raw = request.form.get("points", "").strip()
    points = int(points_raw) if points_raw else None
    avatar_url = request.form.get("avatar_url", "").strip() or None
    update_player(player_id, name=name, points=points, avatar_url=avatar_url)
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
