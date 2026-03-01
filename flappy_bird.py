#!/usr/bin/env python3
"""
Flappy Bird for PiSugar Whisplay HAT (Raspberry Pi Zero 2 W).
- Button = flap (jump)
- Run: cd ~/Whisplay/example && sudo python3 flappy_bird.py
"""
import sys
import os
import time
from PIL import Image

# Add Driver: Whisplay-FlappyBird expects to run alongside PiSugar/Whisplay (Driver at repo root)
# See: https://github.com/PiSugar/Whisplay
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
for _DRIVER in [
    os.path.join(_SCRIPT_DIR, "Driver"),
    os.path.join(_SCRIPT_DIR, "..", "Driver"),
    os.path.join(_SCRIPT_DIR, "..", "..", "Driver"),  # e.g. Whisplay/example/Whisplay-FlappyBird -> Whisplay/Driver
]:
    if os.path.isdir(_DRIVER):
        sys.path.insert(0, os.path.abspath(_DRIVER))
        break
else:
    _DRIVER = None

try:
    from WhisPlay import WhisPlayBoard
except ImportError:
    try:
        from Whisplay import WhisPlayBoard
    except ImportError:
        if _DRIVER is None:
            raise SystemExit(
                "Whisplay driver not found. Clone the PiSugar Whisplay repo and run this example from inside it:\n"
                "  git clone https://github.com/PiSugar/Whisplay.git\n"
                "  cd Whisplay/example && git clone https://github.com/Akerrules/Whisplay-FlappyBird.git\n"
                "  cd Whisplay-FlappyBird && sudo python3 FlappyBird.py\n"
                "Or install the driver and put Whisplay-FlappyBird in a folder that has a 'Driver' sibling with Whisplay.py/WhisPlay.py."
            ) from None
        raise

W, H = 240, 280
GRAVITY = 0.35
FLAP_STRENGTH = -7.5
PIPE_WIDTH = 40
PIPE_GAP = 85
PIPE_SPEED = 2.8
PIPE_SPAWN_INTERVAL = 90
BIRD_SIZE = 18
BIRD_X = 60
FLOOR_Y = H - 25
SKY_COLOR = (135, 206, 235)
PIPE_COLOR = (34, 139, 34)
BIRD_COLOR = (255, 220, 0)
FLOOR_COLOR = (139, 90, 43)
TEXT_COLOR = (0, 0, 0)

def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def image_to_rgb565_bytes(im):
    w, h = im.size
    out = []
    for y in range(h):
        for x in range(w):
            p = im.getpixel((x, y))
            r, g, b = (p[:3] if len(p) >= 3 else p)
            v = rgb565(r, g, b)
            out.extend([(v >> 8) & 0xFF, v & 0xFF])
    return out

flap_requested = False
def on_flap():
    global flap_requested
    flap_requested = True

def main():
    global flap_requested
    import random
    board = WhisPlayBoard()
    board.set_backlight(80)
    board.on_button_press(on_flap)
    lcd_w = getattr(board, "LCD_WIDTH", W)
    lcd_h = getattr(board, "LCD_HEIGHT", H)
    bird_y = lcd_h // 2 - BIRD_SIZE // 2
    bird_vy = 0
    pipes = []
    score = 0
    frame = 0
    game_over = False
    started = False

    try:
        while True:
            if game_over:
                im = Image.new("RGB", (lcd_w, lcd_h), SKY_COLOR)
                for x in range(0, lcd_w, 4):
                    im.line([(x, FLOOR_Y), (x + 2, lcd_h)], fill=FLOOR_COLOR)
                try:
                    from PIL import ImageDraw, ImageFont
                    d = ImageDraw.Draw(im)
                    f = ImageFont.load_default()
                    d.text((lcd_w // 2 - 45, lcd_h // 2 - 30), "Game Over", fill=TEXT_COLOR, font=f)
                    d.text((lcd_w // 2 - 25, lcd_h // 2), f"Score: {score}", fill=TEXT_COLOR, font=f)
                    d.text((lcd_w // 2 - 70, lcd_h // 2 + 25), "Button to restart", fill=TEXT_COLOR, font=f)
                except Exception:
                    pass
                board.draw_image(0, 0, lcd_w, lcd_h, image_to_rgb565_bytes(im))
                if flap_requested:
                    flap_requested = False
                    game_over = False
                    bird_y = lcd_h // 2 - BIRD_SIZE // 2
                    bird_vy = 0
                    pipes, score, frame, started = [], 0, 0, False
                time.sleep(0.05)
                continue

            if not started:
                im = Image.new("RGB", (lcd_w, lcd_h), SKY_COLOR)
                for x in range(0, lcd_w, 4):
                    im.line([(x, FLOOR_Y), (x + 2, lcd_h)], fill=FLOOR_COLOR)
                by = int(bird_y)
                for dy in range(BIRD_SIZE):
                    for dx in range(BIRD_SIZE):
                        if 0 <= BIRD_X + dx < lcd_w and 0 <= by + dy < lcd_h:
                            im.putpixel((BIRD_X + dx, by + dy), BIRD_COLOR)
                try:
                    from PIL import ImageDraw, ImageFont
                    d = ImageDraw.Draw(im)
                    f = ImageFont.load_default()
                    d.text((lcd_w // 2 - 35, lcd_h // 2 - 20), "Flappy", fill=TEXT_COLOR, font=f)
                    d.text((lcd_w // 2 - 45, lcd_h // 2 + 5), "Button = flap", fill=TEXT_COLOR, font=f)
                except Exception:
                    pass
                board.draw_image(0, 0, lcd_w, lcd_h, image_to_rgb565_bytes(im))
                if flap_requested:
                    flap_requested = False
                    started = True
                    bird_vy = FLAP_STRENGTH
                time.sleep(0.05)
                continue

            if flap_requested:
                flap_requested = False
                bird_vy = FLAP_STRENGTH
            bird_vy += GRAVITY
            bird_y += bird_vy
            bird_y = max(0, min(bird_y, FLOOR_Y - BIRD_SIZE))
            if bird_y + BIRD_SIZE >= FLOOR_Y:
                game_over = True
                continue

            frame += 1
            if frame % PIPE_SPAWN_INTERVAL == 0 and frame > 0:
                gap_center = random.randint(PIPE_GAP // 2 + 20, lcd_h - PIPE_GAP // 2 - 20)
                pipes.append((lcd_w, gap_center))

            new_pipes = []
            for x, gap_center in pipes:
                nx = x - PIPE_SPEED
                if nx + PIPE_WIDTH > 0:
                    new_pipes.append((nx, gap_center))
                else:
                    score += 1
            pipes = new_pipes

            bird_top, bird_bottom = int(bird_y), int(bird_y) + BIRD_SIZE
            for px, gap_center in pipes:
                pl, pr = px, px + PIPE_WIDTH
                gap_top = gap_center - PIPE_GAP // 2
                gap_bottom = gap_center + PIPE_GAP // 2
                if BIRD_X + BIRD_SIZE < pl or BIRD_X > pr:
                    continue
                if bird_top > gap_bottom or bird_bottom < gap_top:
                    game_over = True
                    break
            if game_over:
                continue

            im = Image.new("RGB", (lcd_w, lcd_h), SKY_COLOR)
            for x in range(0, lcd_w, 4):
                im.line([(x, FLOOR_Y), (x + 2, lcd_h)], fill=FLOOR_COLOR)
            for px, gap_center in pipes:
                gap_top = gap_center - PIPE_GAP // 2
                gap_bottom = gap_center + PIPE_GAP // 2
                for py in range(0, gap_top):
                    for dx in range(PIPE_WIDTH):
                        if 0 <= px + dx < lcd_w and 0 <= py < lcd_h:
                            im.putpixel((px + dx, py), PIPE_COLOR)
                for py in range(gap_bottom, lcd_h):
                    for dx in range(PIPE_WIDTH):
                        if 0 <= px + dx < lcd_w and 0 <= py < lcd_h:
                            im.putpixel((px + dx, py), PIPE_COLOR)
            by = int(bird_y)
            for dy in range(BIRD_SIZE):
                for dx in range(BIRD_SIZE):
                    if 0 <= BIRD_X + dx < lcd_w and 0 <= by + dy < lcd_h:
                        im.putpixel((BIRD_X + dx, by + dy), BIRD_COLOR)
            board.draw_image(0, 0, lcd_w, lcd_h, image_to_rgb565_bytes(im))
            time.sleep(1 / 35)
    except KeyboardInterrupt:
        pass
    finally:
        board.cleanup()

if __name__ == "__main__":
    main()