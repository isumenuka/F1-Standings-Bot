import os
import sys
import threading
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from flask import Flask
import io

# Add parent directory to path for shared module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

load_dotenv()

# ── Tiny health-check server (required by Render web services) ───────────────
_health_app = Flask("health")

@_health_app.route("/")
def _health():
    return "OK", 200

def _run_health_server():
    port = int(os.environ.get("PORT", 8080))
    _health_app.run(host="0.0.0.0", port=port, use_reloader=False)

threading.Thread(target=_run_health_server, daemon=True).start()
# ─────────────────────────────────────────────────────────────────────────────


TOKEN = os.getenv("DISCORD_TOKEN")
APPLICATION_ID = int(os.getenv("APPLICATION_ID", "0"))

from shared.db import load_players
from image_gen import generate_standings_image


class StandingsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=APPLICATION_ID
        )

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Slash commands synced globally.")

    async def on_ready(self):
        print(f"🤖 Logged in as {self.user} (ID: {self.user.id})")
        print("─" * 40)


bot = StandingsBot()


@bot.tree.command(name="standings", description="Show the current driver standings leaderboard image")
async def standings(interaction: discord.Interaction):
    """Generate and post the standings image."""
    await interaction.response.defer()

    players = load_players()
    if not players:
        await interaction.followup.send("❌ No players found! Ask an admin to add players via the admin panel.")
        return

    try:
        image_buf = generate_standings_image(players, "DRIVER STANDINGS")
        file = discord.File(fp=image_buf, filename="standings.png")

        content = (
            "🏆 **Driver Standings**\n"
            "🏎️ **[Click here to view the Gaming Hassa YT League on Racenet](https://racenet.com/f1_25/leagues/league/leagueID=25953)**\n"
            "*Use `/standings` anytime to refresh*"
        )
        await interaction.followup.send(content=content, file=file)

    except Exception as e:
        print(f"[ERROR] Image generation failed: {e}")
        await interaction.followup.send(f"❌ Failed to generate standings image. Error: {e}")


@bot.tree.command(name="addpoints", description="[Admin] Add points to a player by name")
@app_commands.describe(name="Player name", points="Points to add (can be negative)")
async def addpoints(interaction: discord.Interaction, name: str, points: int):
    """Quick points update from Discord (for convenience)."""
    # Check if user has admin/manage guild permissions
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ You need **Manage Server** permission to use this command.", ephemeral=True)
        return

    from shared.db import load_players, save_players
    import json

    raw_path = os.getenv("DATA_PATH", "shared/data.json")
    with open(raw_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    found = False
    for p in raw:
        if p["name"].lower() == name.lower():
            p["points"] += points
            found = True
            final_pts = p["points"]
            break

    if not found:
        await interaction.response.send_message(f"❌ Player **{name}** not found. Check the name and try again.", ephemeral=True)
        return

    from shared.db import save_players
    save_players(raw)
    await interaction.response.send_message(
        f"✅ Added **{points} pts** to **{name}** → Total: **{final_pts} pts**",
        ephemeral=False
    )


@bot.tree.command(name="leaderboard", description="Show text leaderboard (quick view)")
async def leaderboard(interaction: discord.Interaction):
    """Show a quick text leaderboard."""
    players = load_players()
    if not players:
        await interaction.response.send_message("❌ No players yet!", ephemeral=True)
        return

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = ["**🏆 DRIVER STANDINGS**\n"]
    for i, p in enumerate(players, 1):
        medal = medals.get(i, f"`{i:2d}.`")
        lines.append(f"{medal} **{p['name']}** — {p['points']} pts")

    await interaction.response.send_message("\n".join(lines))


if __name__ == "__main__":
    if not TOKEN:
        print("❌ DISCORD_TOKEN not set. Check your .env file.")
        sys.exit(1)
    bot.run(TOKEN)
