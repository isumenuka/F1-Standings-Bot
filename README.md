# 🏆 Discord Standings Bot

A Discord bot that generates F1-style standings images, with a web admin panel for managing player names and points. Deployable on Render.com.

---

## ✨ Features

- `/standings` — Posts a beautiful F1-style standings image in your Discord channel
- `/leaderboard` — Quick text leaderboard
- `/addpoints <name> <points>` — Add points to a player (requires Manage Server permission)
- **Admin Panel** — Web UI to add, rename, edit points, and delete players

---

## 📁 Project Structure

```
bot/
  bot.py         ← Discord bot (slash commands)
  image_gen.py   ← Pillow image generator
web/
  app.py         ← Flask admin panel
  templates/     ← HTML pages
  static/        ← CSS
shared/
  data.json      ← Player data
  db.py          ← Data helpers
render.yaml      ← Render.com deployment config
requirements.txt
.env
```

---

## 🚀 Local Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment variables
Edit `.env`:
```
DISCORD_TOKEN=your_token
APPLICATION_ID=your_app_id
ADMIN_PASSWORD=your_password
SECRET_KEY=random_long_string
DATA_PATH=shared/data.json
```

### 3. Run the bot
```bash
python bot/bot.py
```

### 4. Run the admin panel (separate terminal)
```bash
python web/app.py
# Open http://localhost:5000
```

### 5. Test image generation (standalone)
```bash
python bot/image_gen.py
# Saves standings_preview.png — open it to verify the design
```

---

## 🌐 Deploy to Render.com

### Step 1: Push to GitHub
Create a new GitHub repo and push this folder to it.

> ⚠️ **Important**: Before pushing, check that `.env` is in `.gitignore` so your bot token isn't public!

### Step 2: Create services on Render
1. Go to [render.com](https://render.com) and click **New → Blueprint**
2. Connect your GitHub repo
3. Render will detect `render.yaml` and create both services automatically

### Step 3: Set environment variables in Render
For **both services**, go to the Render dashboard → Environment and add:
| Key | Value |
|-----|-------|
| `DISCORD_TOKEN` | Your bot token |
| `APPLICATION_ID` | `1482206029772099624` |
| `ADMIN_PASSWORD` | Choose a strong password |
| `SECRET_KEY` | A random string |

### Step 4: Enable your Discord bot
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your app → **Bot** → Enable **Message Content Intent**
3. Go to **OAuth2 → URL Generator** → Scopes: `bot`, `applications.commands`
4. Bot permissions: `Send Messages`, `Embed Links`, `Attach Files`
5. Copy the generated URL and invite the bot to your server

---

## 🔑 Discord Bot Permissions Required

| Permission | Why |
|---|---|
| Send Messages | To post standings |
| Embed Links | For rich embeds |
| Attach Files | For the standings image |
| Use Slash Commands | For `/standings` etc. |

---

## 🛠️ Admin Panel Usage

1. Open your Render web service URL (e.g. `https://discord-standings-web.onrender.com`)
2. Login with your `ADMIN_PASSWORD`
3. Add players, set their points, rename or delete them
4. Run `/standings` in Discord to see the updated image

---

## 📝 Notes

- Player data is stored in `shared/data.json`
- Fonts (Roboto) are automatically downloaded on first run
- The bot token in this repo should be **regenerated** if you push to a public GitHub repo
