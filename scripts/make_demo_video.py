"""Build docs/signspeak-demo.mp4 from the captured frames.

Captions are drawn with PIL and composited above each screenshot; ffmpeg only
concatenates. (This ffmpeg build has no drawtext filter.)

The walkthrough is a captioned sequence of real states of the deployed page, not
a screen recording, and the captions say where the hand in the camera comes from.

Usage:  python scripts/make_demo_video.py
"""

import json
import os
import subprocess
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FRAMES = os.path.join(ROOT, "docs", "frames")
BUILD = os.path.join(ROOT, "docs", "build")
OUT = os.path.join(ROOT, "docs", "signspeak-demo.mp4")

W, H = 1920, 1080
BG = (11, 17, 32)
INK = (232, 238, 249)
DIM = (148, 163, 184)
ACCENT = (125, 211, 252)

BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


# (frame name, heading, body, seconds). A frame of None is a text-only card.
SCRIPT = [
    (None, "SignSpeak",
     "American Sign Language fingerspelling, recognised in the browser.\n"
     "MediaPipe hand landmarks into a small PyTorch classifier.", 4.0),
    ("01-landing", "The whole thing runs on the visitor's device",
     "No upload, no GPU hosting, no account. The page is static files and the\n"
     "classifier is 52,000 parameters.", 5.0),
    ("02-camera-started", "Camera on",
     "Everything past this point is the deployed page at signspeak-asl.vercel.app.\n"
     "The hand in the frame is a recorded dataset image played in as a webcam —\n"
     "nobody here can sign — but the tracking, the model and the readout are real.", 6.5),
    ("03-letter-1-S", "S",
     "MediaPipe finds 21 landmarks. They are centred on the wrist, rotated upright\n"
     "and scaled, so what reaches the model is shape alone.", 4.5),
    ("03-letter-2-I", "I",
     "A letter is only committed after the same sign holds steadily for about half a\n"
     "second, so the buffer does not fill with poses the hand passed through.", 4.5),
    ("03-letter-3-G", "G", "", 3.0),
    ("03-letter-4-N", "S I G N",
     "Four letters, spelled through the live page.", 4.0),
    ("04-numbers", "The number, measured two ways",
     "92.2% on a signer the model has never seen — leave-one-signer-out over five\n"
     "people, every one of 65,522 samples held out exactly once, per-fold 87.5–95.4%.\n"
     "98.7% on a random split of the same data, which is the number not to trust.", 8.0),
    ("05-chart", "What the model actually learned",
     "Each hand is a real pose from the training data, drawn from its landmarks —\n"
     "not an illustration of what the letter should look like.", 5.5),
    ("07-failures", "Where it fails, from the confusion matrix",
     "R goes to U one time in five. P and Q trade places because the rotation\n"
     "normalisation that makes the model work on a stranger is exactly what erases\n"
     "the difference between them. J and Z are not here at all: both are movement.", 8.0),
    ("08-mobile", "And on a phone", "", 4.0),
    (None, "signspeak-asl.vercel.app",
     "Source, evaluation script and the full protocol:\n"
     "github.com/mayankgoel214/SignSpeak", 5.0),
]


def card(frame_name, heading, body):
    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)

    if frame_name is None:
        f_head, f_body = font(BOLD, 84), font(REGULAR, 40)
        hb = draw.textbbox((0, 0), heading, font=f_head)
        lines = body.split("\n") if body else []
        total = (hb[3] - hb[1]) + 40 + len(lines) * 56
        y = (H - total) // 2
        draw.text(((W - (hb[2] - hb[0])) // 2, y), heading, font=f_head, fill=ACCENT)
        y += (hb[3] - hb[1]) + 56
        for line in lines:
            lb = draw.textbbox((0, 0), line, font=f_body)
            draw.text(((W - (lb[2] - lb[0])) // 2, y), line, font=f_body, fill=DIM)
            y += 56
        return canvas

    f_head, f_body = font(BOLD, 52), font(REGULAR, 32)
    margin, y = 72, 56
    draw.text((margin, y), heading, font=f_head, fill=INK)
    y += 74
    for line in (body.split("\n") if body else []):
        draw.text((margin, y), line, font=f_body, fill=DIM)
        y += 44
    y += 24

    shot = Image.open(os.path.join(FRAMES, f"{frame_name}.png")).convert("RGB")
    avail_h, avail_w = H - y - 56, W - 2 * margin
    scale = min(avail_w / shot.width, avail_h / shot.height)
    shot = shot.resize((int(shot.width * scale), int(shot.height * scale)), Image.LANCZOS)
    canvas.paste(shot, ((W - shot.width) // 2, y + (avail_h - shot.height) // 2))
    return canvas


def main():
    if not os.path.isdir(FRAMES):
        sys.exit("no frames -- run scripts/capture-demo.mjs first")
    os.makedirs(BUILD, exist_ok=True)

    entries = []
    for i, (name, heading, body, secs) in enumerate(SCRIPT):
        path = os.path.join(BUILD, f"card-{i:02d}.png")
        card(name, heading, body).save(path)
        entries.append((path, secs))
        print(f"  card {i:02d} {heading[:40]}")

    listing = os.path.join(BUILD, "concat.txt")
    with open(listing, "w") as f:
        for path, secs in entries:
            f.write(f"file '{os.path.abspath(path)}'\nduration {secs}\n")
        f.write(f"file '{os.path.abspath(entries[-1][0])}'\n")  # concat needs the last frame twice

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listing,
        "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
        "-crf", "20", "-movflags", "+faststart", OUT,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    size = os.path.getsize(OUT) / 1e6
    total = sum(s for _, s in entries)
    print(f"wrote {OUT} -- {total:.0f}s, {size:.1f} MB")


if __name__ == "__main__":
    main()
