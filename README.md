# autoedit

비트코인 시황 원테이크 영상을 자동으로 컷편집해 Premiere Pro로 import할 수 있는 FCPXML로 출력하는 CLI 도구.

## 동작 개요

1. 영상에서 오디오 추출 (FFmpeg)
2. faster-whisper로 한국어 단어 단위 타임스탬프 전사
3. 대본과 전사 정렬 (한국어 자모 + RapidFuzz)
4. 발화 중 `"다시"`를 NG 시그널로 보고 직전 시도 구간 자동 컷
5. 인트로/아웃트로 영상을 앞뒤에 부착
6. OpenTimelineIO로 FCPXML 생성 → Premiere에서 import 후 검수/조정

원본 영상은 재인코딩하지 않습니다. 결과 FCPXML은 원본 미디어를 참조하고 in/out 시간만 지정합니다.

## 설치 (Windows)

전제: Python 3.11+, FFmpeg가 PATH에 있을 것.

```powershell
git clone <repo>
cd autoedit
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

LLM 보조 정렬을 쓰려면:

```powershell
pip install -e .[llm]
$env:ANTHROPIC_API_KEY="sk-ant-..."
```

GPU(CUDA)가 있으면 faster-whisper가 자동 사용합니다.

## 사용법

```powershell
# config 복사
copy config.example.toml config.toml

# 풀 파이프라인
autoedit run `
    --video "C:\videos\bitcoin_2026-05-01.mp4" `
    --script "C:\scripts\2026-05-01.txt" `
    --intro assets\intro.mp4 `
    --outro assets\outro.mp4 `
    --output output\2026-05-01.fcpxml `
    --config config.toml

# 단계별 실행 (캐시 활용)
autoedit transcribe --video <video>
autoedit align --video <video> --script <script>
autoedit cuts --video <video> --script <script>
autoedit export --video <video> --cuts cache\<sha>\cuts.json --output result.fcpxml
```

생성된 `.fcpxml`을 Premiere Pro의 **File → Import**로 열면 컷이 적용된 시퀀스가 만들어집니다.

## NG 시그널 사용법

녹화 중 말실수하면 그냥 **"다시"**라고 말하고 그 문장을 처음부터 다시 읽으면 됩니다. 자동으로 NG 구간이 잘려나갑니다.

대본에 `"다시"`라는 단어가 정상적으로 등장하는 경우(예: "다시 강조하지만")는 정렬을 통해 NG와 구분되므로 잘리지 않습니다.

## 프로젝트 구조

```
src/autoedit/
├── cli.py          진입점
├── config.py       TOML 설정
├── pipeline.py     단계 오케스트레이션
├── audio.py        FFmpeg 오디오 추출/probe
├── transcribe.py   faster-whisper 래퍼 + 캐시
├── align.py        대본↔전사 정렬
├── retake.py       "다시" 탐지 + NG 구간 결정
├── silence.py      (옵션) 무음 트리밍
├── timeline.py     keep 병합 + 프레임 스냅
├── fcpxml.py       OTIO 기반 FCPXML 출력
├── llm.py          (옵션) Claude API 보조
└── models.py       공용 dataclass
```

## 라이선스

MIT
