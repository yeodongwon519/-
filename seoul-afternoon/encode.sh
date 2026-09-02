#!/bin/bash
# frames/f_%04d.png (30 fps, 8 s) + bgm.wav -> seoul_afternoon.mp4 (H.264 + AAC, 9:16)
set -e
cd "$(dirname "$0")"
FF=/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2
$FF -y -loglevel error -framerate 30 -i frames/f_%04d.png -i bgm.wav \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -movflags +faststart \
  -c:a aac -b:a 160k -shortest seoul_afternoon.mp4
$FF -loglevel error -i seoul_afternoon.mp4 -hide_banner 2>&1 | head -5 || true
ls -la seoul_afternoon.mp4
