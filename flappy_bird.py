#!/usr/bin/env python3
"""
Flappy Bird for PiSugar Whisplay HAT (Raspberry Pi Zero 2 W).
Button = flap.  Run from inside the Whisplay repo:
  cd ~/Whisplay/example/Whisplay-FlappyBird && sudo python3 flappy_bird.py
"""
import sys
import os
import time
import random
from PIL import Image, ImageDraw, ImageFont
from exit_helper import LongPressExit

# ── Audio (optional — game works fine without pygame) ────────────────
_DIR = os.path.dirname(os.path.abspath(__file__))
_SND_DIR = os.path.join(_DIR, "sounds")

try:
    import pygame
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)

    def _load(name):
        path = os.path.join(_SND_DIR, name)
        if os.path.isfile(path):
            return pygame.mixer.Sound(path)
        return None

    SND_WING   = _load("05. Wing.mp3")
    SND_POINT  = _load("03. Point.mp3")
    SND_HIT    = _load("02. Hit.mp3")
    SND_DIE    = _load("01. Die.mp3")
    SND_SWOOSH = _load("04. Swooshing.mp3")
    _HAS_AUDIO = True
except Exception:
    _HAS_AUDIO = False

def _play(snd):
    if _HAS_AUDIO and snd is not None:
        snd.play()

from whisplay_hw import WhisPlayBoard

# ── Game constants ──────────────────────────────────────────────────
GRAVITY    = 0.45
FLAP_VEL   = -6.5
PIPE_W     = 36
PIPE_GAP   = 78
PIPE_SPEED = 3
SPAWN_EVERY = 55
BIRD_W     = 16
BIRD_H     = 14
BIRD_X     = 55
FLOOR_H    = 20

SKY       = (112, 197, 206)
PIPE_BODY = (115, 190, 45)
PIPE_CAP  = (115, 190, 45)
PIPE_HL   = (153, 229, 80)
PIPE_SH   = (89, 150, 31)
BIRD_FILL = (246, 220, 2)
BIRD_WING = (246, 160, 0)
BIRD_OUTLINE = (84, 56, 71)
BIRD_BEAK = (250, 100, 0)
FLOOR_CLR = (222, 216, 149)
FLOOR_TOP = (115, 190, 45)
FLOOR_STRIPE = (200, 190, 110)
FLOOR_OUTLINE = (84, 56, 71)
WHITE     = (255, 255, 255)
BLACK     = (0, 0, 0)

# ── Button state (set from interrupt / poll thread) ─────────────────
_flap = False

def _on_btn():
    global _flap
    _flap = True

# ── Drawing helpers ─────────────────────────────────────────────────
def _draw_bird(draw, by):
    # Body outline
    draw.rectangle([BIRD_X-1, by-1, BIRD_X + BIRD_W, by + BIRD_H], fill=BIRD_OUTLINE)
    # Body fill
    draw.rectangle([BIRD_X, by, BIRD_X + BIRD_W - 1, by + BIRD_H - 1], fill=BIRD_FILL)
    # Beak
    draw.rectangle([BIRD_X + BIRD_W - 2, by + BIRD_H // 2 + 1, BIRD_X + BIRD_W + 4, by + BIRD_H - 2], fill=BIRD_OUTLINE)
    draw.rectangle([BIRD_X + BIRD_W - 1, by + BIRD_H // 2 + 2, BIRD_X + BIRD_W + 3, by + BIRD_H - 3], fill=BIRD_BEAK)
    # Wing outline
    draw.rectangle([BIRD_X + 1, by + BIRD_H // 2 - 1, BIRD_X + BIRD_W // 2 + 1, by + BIRD_H - 2], fill=BIRD_OUTLINE)
    # Wing fill
    draw.rectangle([BIRD_X + 2, by + BIRD_H // 2, BIRD_X + BIRD_W // 2, by + BIRD_H - 3], fill=BIRD_WING)
    # Eye
    ex, ey = BIRD_X + BIRD_W - 6, by + 2
    draw.rectangle([ex-1, ey-1, ex + 4, ey + 4], fill=BIRD_OUTLINE)
    draw.rectangle([ex, ey, ex + 3, ey + 3], fill=WHITE)
    draw.rectangle([ex + 2, ey + 1, ex + 3, ey + 2], fill=BLACK)


def _draw_pipes(draw, pipes, floor_y):
    for p in pipes:
        pxi = int(p[0])
        gt = p[1] - PIPE_GAP // 2
        gb = p[1] + PIPE_GAP // 2
        
        # Top pipe
        draw.rectangle([pxi-1, 0, pxi + PIPE_W, gt - 1], fill=BIRD_OUTLINE)
        draw.rectangle([pxi, 0, pxi + PIPE_W - 1, gt - 1], fill=PIPE_BODY)
        draw.rectangle([pxi + 2, 0, pxi + 6, gt - 1], fill=PIPE_HL)
        draw.rectangle([pxi + PIPE_W - 6, 0, pxi + PIPE_W - 2, gt - 1], fill=PIPE_SH)
        
        draw.rectangle([pxi - 4, gt - 9, pxi + PIPE_W + 3, gt], fill=BIRD_OUTLINE)
        draw.rectangle([pxi - 3, gt - 8, pxi + PIPE_W + 2, gt - 1], fill=PIPE_CAP)
        draw.rectangle([pxi - 1, gt - 8, pxi + 3, gt - 1], fill=PIPE_HL)
        draw.rectangle([pxi + PIPE_W - 3, gt - 8, pxi + PIPE_W + 1, gt - 1], fill=PIPE_SH)

        # Bottom pipe
        draw.rectangle([pxi-1, gb, pxi + PIPE_W, floor_y - 1], fill=BIRD_OUTLINE)
        draw.rectangle([pxi, gb, pxi + PIPE_W - 1, floor_y - 1], fill=PIPE_BODY)
        draw.rectangle([pxi + 2, gb, pxi + 6, floor_y - 1], fill=PIPE_HL)
        draw.rectangle([pxi + PIPE_W - 6, gb, pxi + PIPE_W - 2, floor_y - 1], fill=PIPE_SH)
        
        draw.rectangle([pxi - 4, gb, pxi + PIPE_W + 3, gb + 8], fill=BIRD_OUTLINE)
        draw.rectangle([pxi - 3, gb, pxi + PIPE_W + 2, gb + 7], fill=PIPE_CAP)
        draw.rectangle([pxi - 1, gb, pxi + 3, gb + 7], fill=PIPE_HL)
        draw.rectangle([pxi + PIPE_W - 3, gb, pxi + PIPE_W + 1, gb + 7], fill=PIPE_SH)


def _draw_scaled_text(im, center_x, y, text, font, fill, outline, scale=2):
    # Render text at 1x to a transparent temporary image
    # 200x50 is large enough for short game strings with default font
    temp = Image.new("RGBA", (200, 50), (0, 0, 0, 0))
    td = ImageDraw.Draw(temp)
    
    # Draw outline (1px border)
    td.text((1, 1), text, font=font, fill=outline)
    td.text((3, 1), text, font=font, fill=outline)
    td.text((1, 3), text, font=font, fill=outline)
    td.text((3, 3), text, font=font, fill=outline)
    td.text((2, 1), text, font=font, fill=outline)
    td.text((2, 3), text, font=font, fill=outline)
    td.text((1, 2), text, font=font, fill=outline)
    td.text((3, 2), text, font=font, fill=outline)
    
    # Draw fill
    td.text((2, 2), text, font=font, fill=fill)
    
    bbox = temp.getbbox()
    if bbox:
        temp = temp.crop(bbox)
        nw = temp.width * scale
        nh = temp.height * scale
        temp = temp.resize((nw, nh), Image.NEAREST)
        
        px = center_x - nw // 2
        im.paste(temp, (px, int(y)), temp)


# ── Main ────────────────────────────────────────────────────────────
def main():
    global _flap

    board = WhisPlayBoard(backlight=80)

    def _shutdown():
        try:
            if _HAS_AUDIO:
                pygame.mixer.quit()
        except Exception:
            pass
        try:
            board.cleanup()
        except Exception:
            pass
        sys.exit(0)

    exit_handler = LongPressExit(board, on_press=_on_btn, shutdown_fn=_shutdown)

    from whisplay_hw import LCD_W as W, LCD_H as H
    floor_y = H - FLOOR_H
    font = ImageFont.load_default()

    # Pre-render floor strip (pasted each frame — avoids re-drawing lines)
    floor_img = Image.new("RGB", (W + 12, FLOOR_H), FLOOR_CLR)
    fd = ImageDraw.Draw(floor_img)
    for x in range(-FLOOR_H, W + 12, 12):
        fd.polygon([(x, FLOOR_H), (x + 6, FLOOR_H), (x + 6 + FLOOR_H, 0), (x + FLOOR_H, 0)], fill=FLOOR_STRIPE)
    fd.rectangle([0, 0, W + 12, 4], fill=FLOOR_TOP)
    fd.line([(0, 0), (W + 12, 0)], fill=FLOOR_OUTLINE, width=1)
    fd.line([(0, 4), (W + 12, 4)], fill=FLOOR_OUTLINE, width=1)

    # Pre-render sky background
    bg_img = Image.new("RGB", (W, H), SKY)
    bd = ImageDraw.Draw(bg_img)
    # Draw some simple clouds
    bd.ellipse([30, 40, 70, 70], fill=WHITE)
    bd.ellipse([50, 30, 90, 60], fill=WHITE)
    bd.ellipse([70, 40, 110, 70], fill=WHITE)
    bd.rectangle([50, 50, 90, 70], fill=WHITE)

    bd.ellipse([150, 80, 180, 100], fill=WHITE)
    bd.ellipse([165, 70, 195, 90], fill=WHITE)
    bd.ellipse([180, 80, 210, 100], fill=WHITE)
    bd.rectangle([165, 85, 195, 100], fill=WHITE)

    # City silhouette
    bd.rectangle([20, floor_y - 30, 40, floor_y], fill=(160, 200, 210))
    bd.rectangle([35, floor_y - 50, 60, floor_y], fill=(140, 180, 190))
    bd.rectangle([80, floor_y - 40, 110, floor_y], fill=(150, 190, 200))
    bd.rectangle([160, floor_y - 45, 190, floor_y], fill=(140, 180, 190))
    bd.rectangle([180, floor_y - 25, 220, floor_y], fill=(160, 200, 210))

    def send(im):
        board.display_image(im)

    def new_frame():
        im = bg_img.copy()
        draw = ImageDraw.Draw(im)
        return im, draw

    # Game state
    bird_y = float(H // 2)
    bird_vy = 0.0
    pipes = []          # each entry: [x_float, gap_center_int, scored_bool]
    score = 0
    frame = 0
    state = "title"     # title | play | dead | confirm_exit
    prev_state = None
    confirm_t = 0.0
    CONFIRM_TIMEOUT = 5.0
    TARGET_DT = 1.0 / 30
    floor_offset = 0

    try:
        while True:
            t0 = time.time()

            # ── LONG-PRESS EXIT CHECK ──────────────────
            if state != "confirm_exit" and exit_handler.check_long_press():
                _flap = False
                prev_state = state
                confirm_t = time.time()
                state = "confirm_exit"

            # ── CONFIRM EXIT ───────────────────────────
            if state == "confirm_exit":
                im, draw = new_frame()
                im.paste(floor_img, (floor_offset - 12, floor_y))

                bx = W // 2 - 80
                by = H // 2 - 35
                draw.rectangle([bx + 3, by + 3, bx + 160 + 3, by + 70 + 3],
                               fill=BIRD_OUTLINE)
                draw.rectangle([bx, by, bx + 160, by + 70],
                               fill=FLOOR_CLR, outline=BIRD_OUTLINE, width=2)

                _draw_scaled_text(im, W // 2, by + 8,
                                  "Exit Home?", font, WHITE, BIRD_OUTLINE, scale=2)
                _draw_scaled_text(im, W // 2, by + 40,
                                  "Press = Yes", font, WHITE, BIRD_OUTLINE, scale=2)

                remaining = max(0, CONFIRM_TIMEOUT - (time.time() - confirm_t))
                _draw_scaled_text(im, W // 2, by + 60,
                                  f"{remaining:.0f}s to cancel", font,
                                  WHITE, BIRD_OUTLINE, scale=1)
                send(im)

                if _flap:
                    _flap = False
                    exit_handler.exit_to_launcher()
                elif time.time() - confirm_t >= CONFIRM_TIMEOUT:
                    _flap = False
                    state = prev_state
                else:
                    time.sleep(0.05)
                continue

            # ── TITLE ───────────────────────────────────
            if state == "title":
                floor_offset = (floor_offset - int(PIPE_SPEED)) % 12
                im, draw = new_frame()
                im.paste(floor_img, (floor_offset - 12, floor_y))
                _draw_bird(draw, H // 2 - BIRD_H // 2)
                _draw_scaled_text(im, W // 2, H // 2 - 50, "Flappy", font, WHITE, BIRD_OUTLINE, scale=3)
                _draw_scaled_text(im, W // 2, H // 2 + 10, "Press button!", font, WHITE, BIRD_OUTLINE, scale=2)
                send(im)
                if _flap:
                    _flap = False
                    _play(SND_SWOOSH)
                    bird_y = float(H // 2)
                    bird_vy = FLAP_VEL
                    pipes = []
                    score = 0
                    frame = 0
                    state = "play"
                else:
                    time.sleep(0.04)
                continue

            # ── DEAD ────────────────────────────────────
            if state == "dead":
                im, draw = new_frame()
                _draw_pipes(draw, pipes, floor_y)
                im.paste(floor_img, (floor_offset - 12, floor_y))
                _draw_bird(draw, int(bird_y))
                
                # Make box wider and taller to fit bigger text
                bx = W // 2 - 80
                by = H // 2 - 45
                
                # Drop shadow
                draw.rectangle([bx + 3, by + 3, bx + 160 + 3, by + 90 + 3], fill=BIRD_OUTLINE)
                # Box
                draw.rectangle([bx, by, bx + 160, by + 90], fill=FLOOR_CLR, outline=BIRD_OUTLINE, width=2)
                
                _draw_scaled_text(im, W // 2, by + 8, "Game Over", font, WHITE, BIRD_OUTLINE, scale=2)
                _draw_scaled_text(im, W // 2, by + 40, f"Score: {score}", font, WHITE, BIRD_OUTLINE, scale=2)
                _draw_scaled_text(im, W // 2, by + 70, "Press button", font, WHITE, BIRD_OUTLINE, scale=1)
                send(im)
                if _flap:
                    _flap = False
                    state = "title"
                else:
                    time.sleep(0.05)
                continue

            # ── PLAY ────────────────────────────────────
            if _flap:
                _flap = False
                bird_vy = FLAP_VEL
                _play(SND_WING)

            # Physics
            bird_vy += GRAVITY
            bird_y += bird_vy
            if bird_y < 0:
                bird_y = 0.0
                bird_vy = 0.0
            if bird_y + BIRD_H >= floor_y:
                bird_y = float(floor_y - BIRD_H)
                _play(SND_HIT)
                _play(SND_DIE)
                _flap = False
                state = "dead"
                continue

            # Spawn pipes
            frame += 1
            if frame % SPAWN_EVERY == 0:
                gc = random.randint(PIPE_GAP // 2 + 25, floor_y - PIPE_GAP // 2 - 25)
                pipes.append([float(W), gc, False])

            # Move pipes and remove off-screen ones
            alive = []
            for p in pipes:
                p[0] -= PIPE_SPEED
                if p[0] + PIPE_W > 0:
                    alive.append(p)
            pipes = alive

            # Score when pipe right edge passes bird center
            bird_cx = BIRD_X + BIRD_W // 2
            for p in pipes:
                if not p[2] and int(p[0]) + PIPE_W < bird_cx:
                    p[2] = True
                    score += 1
                    _play(SND_POINT)

            # Collision
            byi = int(bird_y)
            for p in pipes:
                pxi = int(p[0])
                gt = p[1] - PIPE_GAP // 2
                gb = p[1] + PIPE_GAP // 2
                if BIRD_X + BIRD_W > pxi and BIRD_X < pxi + PIPE_W:
                    if byi < gt or byi + BIRD_H > gb:
                        _play(SND_HIT)
                        _play(SND_DIE)
                        _flap = False
                        state = "dead"
                        break
            if state == "dead":
                continue

            # Render
            floor_offset = (floor_offset - int(PIPE_SPEED)) % 12
            im, draw = new_frame()
            _draw_pipes(draw, pipes, floor_y)
            im.paste(floor_img, (floor_offset - 12, floor_y))
            _draw_bird(draw, byi)
            _draw_scaled_text(im, W // 2, 10, str(score), font, WHITE, BIRD_OUTLINE, scale=3)
            send(im)

            elapsed = time.time() - t0
            remain = TARGET_DT - elapsed
            if remain > 0:
                time.sleep(remain)

    except KeyboardInterrupt:
        pass
    finally:
        if _HAS_AUDIO:
            try:
                pygame.mixer.quit()
            except Exception:
                pass
        try:
            board.cleanup()
        except Exception:
            pass


if __name__ == "__main__":
    main()
