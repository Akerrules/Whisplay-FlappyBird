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
from exit_helper import TriplePressExit

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

# Locate whisplay_hw driver — bundled with the launcher
for _candidate in (
    os.path.join(_DIR, "whisplay_hw.py"),
    os.path.join(_DIR, "..", "Whisplay-Launcher", "settings", "whisplay_hw.py"),
    os.path.join(_DIR, "..", "..", "Whisplay-Launcher", "settings", "whisplay_hw.py"),
):
    _c = os.path.normpath(_candidate)
    if os.path.isfile(_c):
        sys.path.insert(0, os.path.dirname(_c))
        break

try:
    from whisplay_hw import WhisPlayBoard
except ImportError:
    raise SystemExit(
        "whisplay_hw driver not found.\n"
        "  Place whisplay_hw.py next to this script, or ensure\n"
        "  Whisplay-Launcher/settings/whisplay_hw.py is a sibling directory."
    ) from None

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

SKY       = (135, 206, 235)
PIPE_BODY = (34, 139, 34)
PIPE_CAP  = (22, 110, 22)
BIRD_FILL = (255, 220, 0)
BIRD_WING = (230, 180, 0)
FLOOR_CLR = (120, 75, 35)
FLOOR_TOP = (139, 90, 43)
WHITE     = (255, 255, 255)
BLACK     = (0, 0, 0)

# ── Button state (set from interrupt / poll thread) ─────────────────
_flap = False

def _on_btn():
    global _flap
    _flap = True

# ── Drawing helpers ─────────────────────────────────────────────────
def _draw_bird(draw, by):
    draw.rectangle([BIRD_X, by, BIRD_X + BIRD_W - 1, by + BIRD_H - 1], fill=BIRD_FILL)
    draw.rectangle(
        [BIRD_X + 2, by + BIRD_H // 2, BIRD_X + BIRD_W // 2, by + BIRD_H - 3],
        fill=BIRD_WING,
    )
    ex, ey = BIRD_X + BIRD_W - 5, by + 3
    draw.rectangle([ex, ey, ex + 3, ey + 3], fill=WHITE)
    draw.rectangle([ex + 1, ey + 1, ex + 2, ey + 2], fill=BLACK)


def _draw_pipes(draw, pipes, floor_y):
    for p in pipes:
        pxi = int(p[0])
        gt = p[1] - PIPE_GAP // 2
        gb = p[1] + PIPE_GAP // 2
        draw.rectangle([pxi, 0, pxi + PIPE_W - 1, gt - 1], fill=PIPE_BODY)
        draw.rectangle([pxi - 3, gt - 8, pxi + PIPE_W + 2, gt - 1], fill=PIPE_CAP)
        draw.rectangle([pxi, gb, pxi + PIPE_W - 1, floor_y - 1], fill=PIPE_BODY)
        draw.rectangle([pxi - 3, gb, pxi + PIPE_W + 2, gb + 7], fill=PIPE_CAP)


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

    TriplePressExit(board, on_press=_on_btn, shutdown_fn=_shutdown)

    from whisplay_hw import LCD_W as W, LCD_H as H
    floor_y = H - FLOOR_H
    font = ImageFont.load_default()

    # Pre-render floor strip (pasted each frame — avoids re-drawing lines)
    floor_img = Image.new("RGB", (W, FLOOR_H), FLOOR_CLR)
    fd = ImageDraw.Draw(floor_img)
    fd.line([(0, 0), (W, 0)], fill=FLOOR_TOP, width=2)
    for x in range(0, W, 8):
        fd.line([(x, 3), (x + 4, FLOOR_H)], fill=FLOOR_TOP, width=1)

    def send(im):
        board.display_image(im)

    def new_frame():
        im = Image.new("RGB", (W, H), SKY)
        draw = ImageDraw.Draw(im)
        return im, draw

    # Game state
    bird_y = float(H // 2)
    bird_vy = 0.0
    pipes = []          # each entry: [x_float, gap_center_int, scored_bool]
    score = 0
    frame = 0
    state = "title"     # title | play | dead
    TARGET_DT = 1.0 / 30

    try:
        while True:
            t0 = time.time()

            # ── TITLE ───────────────────────────────────
            if state == "title":
                im, draw = new_frame()
                im.paste(floor_img, (0, floor_y))
                _draw_bird(draw, H // 2 - BIRD_H // 2)
                draw.text((W // 2 - 30, H // 2 - 25), "Flappy", fill=BLACK, font=font)
                draw.text((W // 2 - 48, H // 2 + 10), "Press button!", fill=BLACK, font=font)
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
                im.paste(floor_img, (0, floor_y))
                _draw_bird(draw, int(bird_y))
                bx = W // 2 - 55
                by = H // 2 - 35
                draw.rectangle([bx, by, bx + 110, by + 75], fill=WHITE, outline=BLACK, width=2)
                draw.text((W // 2 - 38, by + 8), "Game Over", fill=BLACK, font=font)
                draw.text((W // 2 - 28, by + 28), f"Score: {score}", fill=BLACK, font=font)
                draw.text((W // 2 - 45, by + 50), "Press button", fill=BLACK, font=font)
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
            im, draw = new_frame()
            _draw_pipes(draw, pipes, floor_y)
            im.paste(floor_img, (0, floor_y))
            _draw_bird(draw, byi)
            draw.text((W // 2 - 5, 8), str(score), fill=WHITE, font=font)
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
