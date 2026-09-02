# Seoul Afternoon — 코드로 그린 애니메이션 초상

카페 창가에 앉은 20대 여성의 8초 루프 영상. 외부 AI 모델 없이 Canvas 2D 코드만으로 얼굴·머리카락·니트·창밖 보케를 그리고, 눈 깜빡임·미소·숨결·머리카락 흔들림을 프레임마다 계산합니다.

- `scene.html` — 브라우저에서 열면 바로 재생됩니다. `window.renderFrame(t)`로 임의 시점을 결정적으로 렌더링할 수 있습니다.
- `capture.js` — Playwright로 정지 이미지 또는 프레임 시퀀스를 추출합니다. (`node capture.js still 5.2 out.png 2`, `node capture.js frames 30 8 frames [shard nshard]`)
- `audio.py` — 순수 파이썬으로 로파이 피아노 배경음악(`bgm.wav`)을 합성합니다.
- `encode.sh` — 프레임과 음악을 H.264/AAC MP4(1080×1920, 30 fps)로 인코딩합니다.

```bash
npm i playwright            # 브라우저는 시스템 크로미움 사용
python3 audio.py
for k in 0 1 2 3; do node capture.js frames 30 8 frames $k 4 & done; wait
bash encode.sh              # -> seoul_afternoon.mp4
```
