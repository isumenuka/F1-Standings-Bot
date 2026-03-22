import os
import sys
import io
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ── Font setup ──────────────────────────────────────────────────────────────
FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")
FONT_BOLD_PATH = os.path.join(FONTS_DIR, "Roboto-Bold.ttf")
FONT_REG_PATH = os.path.join(FONTS_DIR, "Roboto-Regular.ttf")

FONT_URLS = {
    FONT_BOLD_PATH:    "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
    FONT_REG_PATH:     "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf",
}

def ensure_fonts():
    os.makedirs(FONTS_DIR, exist_ok=True)
    for path, url in FONT_URLS.items():
        if not os.path.exists(path):
            print(f"[image_gen] Downloading font: {os.path.basename(path)} ...")
            try:
                r = requests.get(url, allow_redirects=True, timeout=30)
                r.raise_for_status()
                with open(path, "wb") as _f:
                    _f.write(r.content)
            except Exception as e:
                print(f"Failed to download font {path}: {e}")

ensure_fonts()

def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

# ── Palette ──────────────────────────────────────────────────────────────────
ROW_COLORS = [
    (230, 120, 20),   # 1 – orange (McLaren)
    (20, 140, 230),   # 2 – blue (Red Bull)
    (0, 180, 180),    # 3 – teal (Mercedes)
    (220, 30, 30),    # 4 – red (Ferrari)
    (20, 190, 100),   # 5 – green (Aston/Sauber)
    (150, 50, 220),   # 6 – purple
    (20, 100, 220),   # 7 – cobalt (Williams/Alpine)
    (220, 160, 20),   # 8 – gold
    (220, 40, 130),   # 9 – magenta
    (40, 200, 130),   # 10 – emerald
]

def darken(color, factor=0.5):
    return tuple(int(c * factor) for c in color)

# ── Dimensions ───────────────────────────────────────────────────────────────
IMG_WIDTH   = 1620
TITLE_H     = 270
ROW_H       = 120
FOOTER_H    = 120
POS_W       = 150
PADDING_X   = 38
AVATAR_SIZE = 90

def draw_avatar_placeholder(draw, cx, cy, r, color, initials, font):
    """Draw a fallback circle with initials."""
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=darken(color, 0.4))
    draw.ellipse((cx - r + 3, cy - r + 3, cx + r - 3, cy + r - 3), outline=(255, 255, 255, 80), width=3)
    text = initials[:2].upper()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw // 2, cy - th // 2 - 3), text, fill=(255, 255, 255), font=font)

def load_avatar(url, size=(AVATAR_SIZE, AVATAR_SIZE)):
    if not url:
        return None
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
        
        # Crop to square
        w, h = img.size
        min_dim = min(w, h)
        left = (w - min_dim)/2
        top = (h - min_dim)/2
        img = img.crop((left, top, left+min_dim, top+min_dim))
        img = img.resize(size, Image.Resampling.LANCZOS)
        
        # Make a circular mask
        mask = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size[0], size[1]), fill=255)
        
        output = Image.new("RGBA", size, (0, 0, 0, 0))
        output.paste(img, (0, 0), mask=mask)
        return output
    except Exception as e:
        print(f"Failed to load avatar: {e}")
        return None

def generate_standings_image(players, title="DRIVER STANDINGS"):
    num = len(players)
    img_height = TITLE_H + num * ROW_H + FOOTER_H

    img = Image.new("RGB", (IMG_WIDTH, img_height), (15, 15, 15))
    draw = ImageDraw.Draw(img)

    font_title    = load_font(FONT_BOLD_PATH, 82)
    font_subtitle = load_font(FONT_REG_PATH, 36)
    font_pos      = load_font(FONT_BOLD_PATH, 54)
    font_name     = load_font(FONT_BOLD_PATH, 48)
    font_pts      = load_font(FONT_BOLD_PATH, 63)
    font_pts_lbl  = load_font(FONT_REG_PATH, 24)
    font_init     = load_font(FONT_BOLD_PATH, 33)

    # ── Header ─────────────────────────────────────────────────────────────
    header_img_path = os.path.join(os.path.dirname(__file__), "header_template.png")
    if not os.path.exists(header_img_path):
        header_img_path = os.path.join(os.path.dirname(__file__), "header_template.jpg")
        
    use_fallback = True
    if os.path.exists(header_img_path):
        try:
            with Image.open(header_img_path) as header_img:
                header_img = header_img.convert("RGBA")
                header_img = header_img.resize((IMG_WIDTH, TITLE_H), Image.Resampling.LANCZOS)
                img.paste(header_img, (0, 0), mask=header_img)
                use_fallback = False
        except Exception as e:
            print(f"Failed to load header image: {e}")

    if use_fallback:
        # Dark grey background
        draw.rectangle([(0, 0), (IMG_WIDTH, TITLE_H)], fill=(12, 12, 15))
        # Signature F1 Red Stripes
        draw.rectangle([(0, 0), (IMG_WIDTH, 18)], fill=(225, 6, 0))
        draw.rectangle([(0, TITLE_H - 68), (IMG_WIDTH, TITLE_H - 52)], fill=(225, 6, 0))

        # Title text
        bbox = draw.textbbox((0, 0), title, font=font_title)
        tw = bbox[2] - bbox[0]
        draw.text(((IMG_WIDTH - tw) // 2, 52), title.upper(), fill=(255, 255, 255), font=font_title)

        # Subtitle
        sub = "GAMING HASSA YT LEAGUE"
        bbox2 = draw.textbbox((0, 0), sub, font=font_subtitle)
        sw = bbox2[2] - bbox2[0]
        draw.text(((IMG_WIDTH - sw) // 2, 142), sub, fill=(180, 180, 180), font=font_subtitle)

    # Column Labels
    hdr_y = TITLE_H - 38
    draw.text((48, hdr_y), "POS", fill=(180, 180, 180), font=font_pts_lbl)
    draw.text((POS_W + 22, hdr_y), "PLAYER", fill=(180, 180, 180), font=font_pts_lbl)
    
    pb = draw.textbbox((0, 0), "POINTS", font=font_pts_lbl)
    pw = pb[2] - pb[0]
    draw.text((IMG_WIDTH - pw - PADDING_X - 22, hdr_y), "POINTS", fill=(180, 180, 180), font=font_pts_lbl)

    # ── Rows ───────────────────────────────────────────────────────────────
    for i, player in enumerate(players):
        y_start = TITLE_H + i * ROW_H
        y_end   = y_start + ROW_H - 3

        color_idx = i % len(ROW_COLORS)
        row_color = ROW_COLORS[color_idx]

        # 1) Position block (Dark)
        draw.rectangle([(0, y_start), (POS_W, y_end)], fill=(20, 20, 24))
        
        pos_text = str(i + 1)
        p_bbox = draw.textbbox((0, 0), pos_text, font=font_pos)
        pw, ph = p_bbox[2]-p_bbox[0], p_bbox[3]-p_bbox[1]
        draw.text(((POS_W - pw)//2, y_start + (ROW_H - ph)//2 - 9), pos_text, fill=(255, 255, 255), font=font_pos)

        # 2) Team Color block (Main)
        draw.rectangle([(POS_W, y_start), (IMG_WIDTH, y_end)], fill=row_color)

        # 3) Avatar
        avatar_img = load_avatar(player.get("avatar_url"))
        avatar_x = POS_W + 30
        # Center avatar vertically
        avatar_y = y_start + (ROW_H - AVATAR_SIZE) // 2
        
        if avatar_img:
            img.paste(avatar_img, (avatar_x, avatar_y), mask=avatar_img)
        else:
            initials = "".join(w[0] for w in player["name"].split("_") if w)[:2] or player["name"][:2]
            draw_avatar_placeholder(draw, avatar_x + AVATAR_SIZE//2, y_start + ROW_H//2, AVATAR_SIZE//2, row_color, initials, font_init)

        # 4) Name
        name_x = avatar_x + AVATAR_SIZE + 30
        gaming_name = player["name"].upper()
        real_name = player.get("real_name", "").strip().upper()
        
        if real_name:
            # Draw real name as main, gaming name as subtitle
            n_bbox = draw.textbbox((0, 0), real_name, font=font_name)
            nh = n_bbox[3]-n_bbox[1]
            r_bbox = draw.textbbox((0, 0), gaming_name, font=font_subtitle)
            rh = r_bbox[3]-r_bbox[1]
            total_h = nh + rh + 8
            draw.text((name_x, y_start + (ROW_H - total_h)//2 - 9), real_name, fill=(255, 255, 255), font=font_name)
            draw.text((name_x, y_start + (ROW_H - total_h)//2 - 9 + nh + 8), gaming_name, fill=(180, 180, 180), font=font_subtitle)
        else:
            n_bbox = draw.textbbox((0, 0), gaming_name, font=font_name)
            nh = n_bbox[3]-n_bbox[1]
            draw.text((name_x, y_start + (ROW_H - nh)//2 - 9), gaming_name, fill=(255, 255, 255), font=font_name)

        # 5) Points right aligned
        pts_text = str(player["points"])
        pts_bbox = draw.textbbox((0, 0), pts_text, font=font_pts)
        pt_w = pts_bbox[2]-pts_bbox[0]
        pt_h = pts_bbox[3]-pts_bbox[1]
        pts_x = IMG_WIDTH - pt_w - PADDING_X - 22
        draw.text((pts_x, y_start + (ROW_H - pt_h)//2 - 12), pts_text, fill=(255, 255, 255), font=font_pts)

    # ── Footer ─────────────────────────────────────────────────────────────
    fy = TITLE_H + num * ROW_H
    draw.rectangle([(0, fy), (IMG_WIDTH, img_height)], fill=(12, 12, 15))
    draw.rectangle([(0, img_height - 18), (IMG_WIDTH, img_height)], fill=(225, 6, 0)) # Bottom stripe
    
    footer_text = "https://racenet.com/f1_25/leagues/league/leagueId=26504"
    ftb = draw.textbbox((0,0), footer_text, font=font_subtitle)
    fw = ftb[2]-ftb[0]
    draw.text(((IMG_WIDTH - fw)//2, fy + 36), footer_text, fill=(160, 160, 180), font=font_subtitle)

    # ── Output ─────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from shared.db import load_players
    players = load_players()
    buf = generate_standings_image(players)
    with open("standings_preview.png", "wb") as f:
        f.write(buf.read())
    print("✅ Saved standings_preview.png — open it to verify the design!")
