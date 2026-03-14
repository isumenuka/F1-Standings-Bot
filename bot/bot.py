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

from shared.db import load_players, get_setting, get_custom_commands, update_player, set_setting
from image_gen import generate_standings_image
from discord.ext import tasks


class StandingsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=APPLICATION_ID
        )

    async def setup_hook(self):
        # Load custom commands from DB
        await self.load_custom_commands()
        
        # Start the sync checker task
        self.check_sync_task.start()
        
        await self.tree.sync()
        print(f"✅ Slash commands synced globally.")

    async def on_ready(self):
        print(f"🤖 Logged in as {self.user} (ID: {self.user.id})")
        print("─" * 40)

    async def load_custom_commands(self):
        """Fetch custom commands from DB and register them."""
        commands = get_custom_commands()
        # Remove existing custom commands to avoid duplicates
        # We identify them by a specific attribute if possible, or just clear non-static ones
        # For simplicity, we can just clear the tree and re-add static ones, 
        # but that's overkill. Instead, we'll just add them.
        # discord.py doesn't have an easy way to 'clear' specific ones without knowing names.
        
        for cmd_data in commands:
            name = cmd_data['name'].lower()
            response_text = cmd_data['response']
            
            # Create a closure for the callback
            async def make_callback(resp):
                async def callback(interaction: discord.Interaction):
                    await interaction.response.send_message(resp)
                return callback

            # Use app_commands.Command to create a dynamic command
            new_cmd = app_commands.Command(
                name=name,
                description=f"Custom league command: /{name}",
                callback=await make_callback(response_text)
            )
            
            # Try to add it. If it exists, remove it first.
            try:
                self.tree.add_command(new_cmd, override=True)
            except Exception as e:
                print(f"[WARN] Could not register custom command /{name}: {e}")

    @tasks.loop(minutes=1)
    async def check_sync_task(self):
        """Check if we need to re-sync commands with Discord."""
        if get_setting("sync_needed") == "true":
            print("🔄 Syncing commands as requested by admin panel...")
            set_setting("sync_needed", "false")
            await self.load_custom_commands()
            await self.tree.sync()
            print("✅ Sync complete.")


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

        # Get dynamic league URL
        league_url = get_setting("league_url", "https://racenet.com/f1_25/leagues/league/leagueID=25953")
        
        content = (
            "🏆 **Driver Standings**\n"
            f"🏎️ **[Click here to view the League on Racenet]({league_url})**\n"
            "*Use `/standings` anytime to refresh*"
        )
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="View Full League", url=league_url, style=discord.ButtonStyle.link))
        
        await interaction.followup.send(content=content, file=file, view=view)

    except Exception as e:
        print(f"[ERROR] Image generation failed: {e}")
        await interaction.followup.send(f"❌ Failed to generate standings image. Error: {e}")

@bot.tree.command(name="league", description="Get the link to the official league page")
async def league(interaction: discord.Interaction):
    """Get the link to the official league page."""
    league_url = get_setting("league_url", "https://racenet.com/f1_25/leagues/league/leagueID=25953")
    
    embed = discord.Embed(
        title="🏁 Official League Page",
        description=f"Click the button below to view the full league standings, results, and upcoming races on Racenet.",
        color=0xFF1801 # F1 Red
    )
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Open Racenet League", url=league_url, style=discord.ButtonStyle.link))
    
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="addpoints", description="[Admin] Add points to a player by name")
@app_commands.describe(name="Player name", points="Points to add (can be negative)")
async def addpoints(interaction: discord.Interaction, name: str, points: int):
    """Quick points update from Discord (for convenience)."""
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ You need **Manage Server** permission to use this command.", ephemeral=True)
        return

    players = load_players()
    player = next((p for p in players if p['name'].lower() == name.lower()), None)

    if not player:
        await interaction.response.send_message(f"❌ Player **{name}** not found.", ephemeral=True)
        return

    new_total = max(0, player['points'] + points)
    update_player(player['id'], player['name'], new_total, player['real_name'], player['avatar_url'])
    
    await interaction.response.send_message(
        f"✅ Updated **{player['name']}**: {player['points']} → **{new_total} pts**",
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
