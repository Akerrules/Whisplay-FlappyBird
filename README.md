# Flappy Bird for Whisplay HAT

A Flappy Bird clone that runs on the [PiSugar Whisplay HAT](https://www.pisugar.com/products/whisplay-hat-for-raspberry-pi-zero-2w-audio-display-expansion-board) — a 1.69" IPS LCD (240x280) + audio + button expansion board for Raspberry Pi.

Built with Python and Pillow, optimized for the Raspberry Pi Zero 2 W.

## Hardware

- Raspberry Pi Zero 2 W (or any Pi with a 40-pin header)
- [PiSugar Whisplay HAT](https://docs.pisuga r.com/docs/product-wiki/whisplay/intro)

## Setup

### 1. Clone the Whisplay driver repo and install

```bash
git clone https://github.com/PiSugar/Whisplay.git --depth 1
cd Whisplay/Driver
sudo bash install_wm8960_drive.sh
sudo reboot
```

### 2. Clone this repo into the Whisplay example directory

```bash
cd ~/Whisplay/example
git clone https://github.com/Akerrules/Whisplay-FlappyBird.git
```

### 3. Install numpy (recommended for smooth FPS)

```bash
sudo apt install python3-numpy
```

## Run

```bash
cd ~/Whisplay/example/Whisplay-FlappyBird
sudo python3 flappy_bird.py
```

## How to Play

- **Press the button** to start the game
- **Press the button** to flap (jump)
- Avoid the pipes and the floor
- Score increases each time you pass through a pipe gap
- **Press the button** after game over to restart

## Project Structure

```
Whisplay/                     # PiSugar/Whisplay repo
├── Driver/
│   └── WhisPlay.py           # Hardware driver (LCD, buttons, LEDs)
└── example/
    └── Whisplay-FlappyBird/  # This repo
        └── flappy_bird.py
```

## Performance

The game targets 30 FPS on Pi Zero 2 W. The main optimization is using numpy for RGB565 pixel format conversion, which reduces frame conversion time from ~200 ms to ~2 ms. Without numpy installed, the game will still run but at a lower frame rate.

## License

MIT
