import os
import sys
import io
import requests as _requests
from PIL import Image, ImageDraw, ImageFont

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
            r = _requests.get(url, allow_redirects=True, timeout=30)
            r.raise_for_status()
            with open(path, "wb") as _f:
                _f.write(r.content)


ensure_fonts()


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


# ── Palette ──────────────────────────────────────────────────────────────────
BG_COLOR       = (10, 10, 20)           # near-black background
TITLE_BG       = (15, 15, 30)
TITLE_COLOR    = (255, 255, 255)
SUBTITLE_COLOR = (180, 180, 200)

ROW_COLORS = [
    (230, 120, 20),   # 1 – orange
    (20, 140, 230),   # 2 – blue
    (0, 180, 180),    # 3 – teal
    (220, 30, 30),    # 4 – red
    (20, 190, 100),   # 5 – green
    (150, 50, 220),   # 6 – purple
    (20, 100, 220),   # 7 – cobalt
    (220, 160, 20),   # 8 – gold
    (220, 40, 130),   # 9 – magenta
    (40, 200, 130),   # 10 – emerald
]

ROW_DARK_MULTIPLIER = 0.35   # darkness applied to the right-side points area


def darken(color, factor=ROW_DARK_MULTIPLIER):
    return tuple(int(c * factor) for c in color)


# ── Dimensions ───────────────────────────────────────────────────────────────
IMG_WIDTH   = 820
TITLE_H     = 130
ROW_H       = 68
FOOTER_H    = 50
PADDING_X   = 28
AVATAR_R    = 26          # circle radius
POINTS_W    = 160         # width of the points + dark section on right


def draw_avatar_circle(draw, cx, cy, r, color, initials, font):
    """Draw a filled circle with initials inside."""
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    # White inner ring
    draw.ellipse((cx - r + 3, cy - r + 3, cx + r - 3, cy + r - 3),
                 outline=(255, 255, 255, 80), width=2)
    # Initials
    text = initials[:2].upper()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw // 2, cy - th // 2), text, fill=(255, 255, 255), font=font)


def generate_standings_image(players, title="DRIVER STANDINGS", subtitle="Season 2025"):
    """
    Generate an F1-style standings image.

    Args:
        players: list of dicts with keys: name, points, avatar_url (optional)
        title: header title text
        subtitle: smaller subtitle under the title

    Returns:
        BytesIO object containing the PNG image
    """
    num = len(players)
    img_height = TITLE_H + num * ROW_H + FOOTER_H

    img = Image.new("RGB", (IMG_WIDTH, img_height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # ── Fonts ─────────────────────────────────────────────────────────────
    font_title    = load_font(FONT_BOLD_PATH, 40)
    font_subtitle = load_font(FONT_REG_PATH, 18)
    font_pos      = load_font(FONT_BOLD_PATH, 28)
    font_name     = load_font(FONT_BOLD_PATH, 22)
    font_pts      = load_font(FONT_BOLD_PATH, 30)
    font_pts_lbl  = load_font(FONT_REG_PATH, 13)
    font_init     = load_font(FONT_BOLD_PATH, 16)

    # ── Title block ───────────────────────────────────────────────────────
    # Gradient-like effect — two rectangles
    draw.rectangle([(0, 0), (IMG_WIDTH, TITLE_H)], fill=(12, 12, 25))
    # Accent bar on top
    draw.rectangle([(0, 0), (IMG_WIDTH, 5)], fill=(220, 40, 40))

    # Title text
    title_upper = title.upper()
    bbox = draw.textbbox((0, 0), title_upper, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text(((IMG_WIDTH - tw) // 2, 22), title_upper, fill=(255, 255, 255), font=font_title)

    # Subtitle
    bbox2 = draw.textbbox((0, 0), subtitle, font=font_subtitle)
    sw = bbox2[2] - bbox2[0]
    draw.text(((IMG_WIDTH - sw) // 2, 76), subtitle, fill=(160, 160, 190), font=font_subtitle)

    # Column headers
    hdr_y = TITLE_H - 30
    draw.text((PADDING_X, hdr_y), "POS.", fill=(130, 130, 160), font=font_pts_lbl)
    draw.text((PADDING_X + 100, hdr_y), "PLAYER", fill=(130, 130, 160), font=font_pts_lbl)
    pts_hdr_bbox = draw.textbbox((0, 0), "POINTS", font=font_pts_lbl)
    pts_hdr_w = pts_hdr_bbox[2] - pts_hdr_bbox[0]
    draw.text((IMG_WIDTH - PADDING_X - pts_hdr_w, hdr_y), "POINTS", fill=(130, 130, 160), font=font_pts_lbl)

    # ── Rows ─────────────────────────────────────────────────────────────
    for i, player in enumerate(players):
        y_start = TITLE_H + i * ROW_H
        y_end   = y_start + ROW_H - 2      # 2px gap between rows

        color_idx = i % len(ROW_COLORS)
        row_color = ROW_COLORS[color_idx]
        dark_color = darken(row_color, 0.2)

        # ── Row background (gradient split) ──────────────────────────────
        # Left section: vibrant color
        split_x = IMG_WIDTH - POINTS_W
        draw.rectangle([(0, y_start), (split_x, y_end)], fill=row_color)
        # Right section: dark
        draw.rectangle([(split_x, y_start), (IMG_WIDTH, y_end)], fill=dark_color)

        # Subtle inner border between sections
        draw.line([(split_x, y_start), (split_x, y_end)], fill=(255, 255, 255, 40), width=1)

        # Row center Y
        cy = y_start + ROW_H // 2 - 1

        # ── Position number ───────────────────────────────────────────────
        pos_text = str(i + 1)
        pos_bbox = draw.textbbox((0, 0), pos_text, font=font_pos)
        ph = pos_bbox[3] - pos_bbox[1]
        draw.text((PADDING_X, cy - ph // 2), pos_text, fill=(255, 255, 255), font=font_pos)

        # ── Avatar circle ─────────────────────────────────────────────────
        avatar_cx = PADDING_X + 55
        initials = "".join(w[0] for w in player["name"].split("_") if w)[:2] or player["name"][:2]
        circle_color = darken(row_color, 0.55)
        draw_avatar_circle(draw, avatar_cx, cy, AVATAR_R, circle_color, initials, font_init)

        # ── Player name ───────────────────────────────────────────────────
        name_text = player["name"].upper()
        name_bbox = draw.textbbox((0, 0), name_text, font=font_name)
        nh = name_bbox[3] - name_bbox[1]
        draw.text((PADDING_X + 90, cy - nh // 2), name_text, fill=(255, 255, 255), font=font_name)

        # ── Points (right side) ───────────────────────────────────────────
        pts_text = str(player["points"])
        pts_bbox = draw.textbbox((0, 0), pts_text, font=font_pts)
        pw = pts_bbox[2] - pts_bbox[0]
        ph2 = pts_bbox[3] - pts_bbox[1]
        pts_x = split_x + (POINTS_W - pw) // 2
        draw.text((pts_x, cy - ph2 // 2), pts_text, fill=(255, 255, 255), font=font_pts)

    # ── Footer ─────────────────────────────────────────────────────────────
    fy = TITLE_H + num * ROW_H
    draw.rectangle([(0, fy), (IMG_WIDTH, fy + FOOTER_H)], fill=(6, 6, 15))
    footer_text = "STANDINGS • BOT POWERED"
    ftb = draw.textbbox((0, 0), footer_text, font=font_subtitle)
    fw = ftb[2] - ftb[0]
    draw.text(((IMG_WIDTH - fw) // 2, fy + 14), footer_text, fill=(80, 80, 110), font=font_subtitle)

    # ── Save to BytesIO ────────────────────────────────────────────────────
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from shared.db import load_players
    players = load_players()
    buf = generate_standings_image(players)
    with open("standings_preview.png", "wb") as f:
        f.write(buf.read())
    print("✅ Saved standings_preview.png — open it to verify the design!")
