#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 Video TTS Maker
영상에 TTS 음성과 자막을 자동으로 추가하는 프로그램

사용법:
    python main.py

필요사항:
    - Python 3.8+
    - ffmpeg (설치 방법은 아래 참고)
    - pip install -r requirements.txt
"""

import os
import re
import sys
import json
import asyncio
import tempfile
import subprocess
import shutil
import platform
from pathlib import Path


# ==================== 설정 ====================

VOICE_OPTIONS = {
    "1": {
        "name": "SunHi - 여성, 자연스럽고 부드러움 (추천)",
        "engine": "edge",
        "voice": "ko-KR-SunHiNeural"
    },
    "2": {
        "name": "InJoon - 남성, 안정적이고 차분함",
        "engine": "edge",
        "voice": "ko-KR-InJoonNeural"
    },
    "3": {
        "name": "BongJin - 남성, 낮고 무게감 있음",
        "engine": "edge",
        "voice": "ko-KR-BongJinNeural"
    },
    "4": {
        "name": "GookMin - 남성, 젊고 활기참",
        "engine": "edge",
        "voice": "ko-KR-GookMinNeural"
    },
    "5": {
        "name": "Hyunsu - 남성, 밝고 친근함",
        "engine": "edge",
        "voice": "ko-KR-HyunsuNeural"
    },
    "6": {
        "name": "Google TTS - 여성, 무난한 한국어",
        "engine": "gtts"
    },
    "7": {
        "name": "시스템 TTS - 오프라인 사용 가능 (품질 낮음)",
        "engine": "pyttsx3"
    },
}

SUBTITLE_STYLES = {
    "1": "심플 - 한 문장씩 깔끔하게 표시",
    "2": "하이라이트 - 읽히는 단어 색상 강조 (릴스 유행 스타일)",
}


# ==================== 유틸리티 ====================

def print_header():
    print("\n" + "=" * 55)
    print("  🎬 Video TTS Maker - 영상 자동 음성/자막 추가기")
    print("=" * 55)


def show_menu(title, options: dict) -> str:
    print(f"\n[ {title} ]")
    print("-" * 40)
    for key, value in options.items():
        if isinstance(value, dict):
            print(f"  {key}. {value['name']}")
        else:
            print(f"  {key}. {value}")
    print("-" * 40)
    while True:
        choice = input("번호 입력: ").strip()
        if choice in options:
            return choice
        print(f"  ❌ {list(options.keys())[0]}~{list(options.keys())[-1]} 중에서 선택하세요.")


def split_sentences(text: str) -> list[str]:
    """긴 텍스트를 문장 단위로 분리"""
    text = text.strip()
    # 줄바꿈을 공백으로 통일
    text = re.sub(r'\n+', ' ', text)
    # 마침표/느낌표/물음표 기준으로 분리
    sentences = re.split(r'(?<=[.!?。！？…])\s+', text)
    result = []
    for s in sentences:
        s = s.strip()
        if s and len(s) > 1:
            result.append(s)
    return result


def seconds_to_ass(seconds: float) -> str:
    """초를 ASS 자막 시간 형식으로 변환 (H:MM:SS.cc)"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def get_media_duration(file_path: str) -> float:
    """ffprobe로 미디어 파일 길이(초) 반환"""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_streams", file_path
            ],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout)
        for stream in data.get("streams", []):
            if "duration" in stream:
                return float(stream["duration"])
    except Exception:
        pass
    return 0.0


def find_korean_font() -> str:
    """시스템에서 한국어 폰트 경로 반환"""
    system = platform.system()

    if system == "Darwin":  # macOS
        candidates = [
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
            "/Library/Fonts/NanumGothic.ttf",
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        ]
    elif system == "Windows":
        candidates = [
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/NanumGothic.ttf",
            "C:/Windows/Fonts/gulim.ttc",
        ]
    else:  # Linux
        candidates = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ]

    for path in candidates:
        if os.path.exists(path):
            return path

    return ""  # 시스템 기본 폰트 사용


# ==================== TTS 엔진 ====================

async def generate_edge_tts(text: str, voice: str, output_path: str) -> list[dict]:
    """
    edge-tts로 음성 생성.
    단어별 타이밍 정보(word_timings) 반환.
    """
    try:
        import edge_tts
    except ImportError:
        print("  edge-tts 설치 중...")
        subprocess.run([sys.executable, "-m", "pip", "install", "edge-tts", "-q"])
        import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    word_timings = []
    audio_data = b""

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
        elif chunk["type"] == "WordBoundary":
            word_timings.append({
                "word": chunk["text"],
                "start": chunk["offset"] / 10_000_000,    # 100ns → 초
                "duration": chunk["duration"] / 10_000_000,
            })

    with open(output_path, "wb") as f:
        f.write(audio_data)

    return word_timings


def generate_gtts(text: str, output_path: str) -> list:
    """gTTS로 음성 생성 (타이밍 정보 없음)"""
    try:
        from gtts import gTTS
    except ImportError:
        print("  gTTS 설치 중...")
        subprocess.run([sys.executable, "-m", "pip", "install", "gtts", "-q"])
        from gtts import gTTS

    tts = gTTS(text=text, lang="ko", slow=False)
    tts.save(output_path)
    return []


def generate_pyttsx3(text: str, output_path: str) -> list:
    """pyttsx3로 음성 생성 (타이밍 정보 없음)"""
    try:
        import pyttsx3
    except ImportError:
        print("  pyttsx3 설치 중...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyttsx3", "-q"])
        import pyttsx3

    engine = pyttsx3.init()
    engine.setProperty("rate", 150)

    # 한국어 목소리 탐색
    for voice in engine.getProperty("voices"):
        if "ko" in voice.id.lower() or "korean" in voice.name.lower():
            engine.setProperty("voice", voice.id)
            break

    # wav로 저장 후 mp3 변환
    wav_path = output_path.replace(".mp3", ".wav")
    engine.save_to_file(text, wav_path)
    engine.runAndWait()

    # wav → mp3 변환
    subprocess.run(
        ["ffmpeg", "-i", wav_path, output_path, "-y", "-loglevel", "quiet"],
        check=True
    )
    os.unlink(wav_path)

    return []


async def generate_audio(sentence: str, voice_config: dict, output_path: str) -> list[dict]:
    """선택된 엔진으로 음성 생성"""
    engine = voice_config["engine"]

    if engine == "edge":
        return await generate_edge_tts(sentence, voice_config["voice"], output_path)
    elif engine == "gtts":
        return generate_gtts(sentence, output_path)
    elif engine == "pyttsx3":
        return generate_pyttsx3(sentence, output_path)

    return []


# ==================== ASS 자막 생성 ====================

ASS_HEADER_TEMPLATE = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},62,&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,-1,0,0,0,100,100,1,0,1,3,1,2,60,60,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def estimate_word_timings(sentence: str, total_duration: float) -> list[dict]:
    """타이밍 정보가 없을 때 단어를 균등하게 나눠 추정"""
    words = sentence.split()
    if not words:
        return []

    # 한국어는 글자 수 기준으로 배분이 더 자연스러움
    char_counts = [len(w) for w in words]
    total_chars = sum(char_counts)

    timings = []
    current_time = 0.0
    for word, chars in zip(words, char_counts):
        duration = total_duration * (chars / total_chars)
        timings.append({
            "word": word,
            "start": current_time,
            "duration": duration,
        })
        current_time += duration

    return timings


def build_subtitles_style1(
    sentences: list[str],
    sentence_timings: list[tuple[float, float]],
    font_name: str,
    output_path: str
):
    """스타일 1: 한 문장씩 심플하게 표시"""
    lines = [ASS_HEADER_TEMPLATE.format(font=font_name or "Arial")]

    for sentence, (start, end) in zip(sentences, sentence_timings):
        # 긴 문장은 줄 나누기
        wrapped = wrap_korean_text(sentence, max_chars=20)
        line = wrapped.replace("\n", "\\N")
        lines.append(
            f"Dialogue: 0,{seconds_to_ass(start)},{seconds_to_ass(end)},"
            f"Default,,0,0,0,,{line}"
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def build_subtitles_style2(
    sentences: list[str],
    sentence_timings: list[tuple[float, float]],
    word_timings_list: list[list[dict]],
    font_name: str,
    output_path: str
):
    """스타일 2: 현재 읽히는 단어 노란색 하이라이트"""
    lines = [ASS_HEADER_TEMPLATE.format(font=font_name or "Arial")]

    for sent_idx, (sentence, (sent_start, sent_end)) in enumerate(
        zip(sentences, sentence_timings)
    ):
        word_timings = word_timings_list[sent_idx]
        sent_duration = sent_end - sent_start

        # 타이밍 없으면 균등 추정
        if not word_timings:
            word_timings = estimate_word_timings(sentence, sent_duration)

        words = [wt["word"] for wt in word_timings]

        for w_idx, wt in enumerate(word_timings):
            w_start = sent_start + wt["start"]

            # 다음 단어 시작 전까지 표시
            if w_idx < len(word_timings) - 1:
                w_end = sent_start + word_timings[w_idx + 1]["start"]
            else:
                w_end = sent_end

            # 현재 단어는 노란색, 나머지는 흰색
            parts = []
            for i, word in enumerate(words):
                if i == w_idx:
                    parts.append(f"{{\\c&H00FFFF&\\b1}}{word}{{\\b0\\c&HFFFFFF&}}")
                else:
                    parts.append(word)

            line_text = " ".join(parts)
            lines.append(
                f"Dialogue: 0,{seconds_to_ass(w_start)},{seconds_to_ass(w_end)},"
                f"Default,,0,0,0,,{line_text}"
            )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def wrap_korean_text(text: str, max_chars: int = 20) -> str:
    """한국어 텍스트 줄 나누기"""
    if len(text) <= max_chars:
        return text

    mid = len(text) // 2
    # 가장 가까운 공백 찾기
    for offset in range(0, mid):
        if text[mid - offset] == " ":
            return text[:mid - offset] + "\n" + text[mid - offset + 1:]
        if text[mid + offset] == " ":
            return text[:mid + offset] + "\n" + text[mid + offset + 1:]

    # 공백 없으면 중간에서 강제 줄 나누기
    return text[:mid] + "\n" + text[mid:]


# ==================== 오디오/영상 합성 ====================

def merge_audio_files(audio_files: list[str], output_path: str):
    """여러 오디오 파일을 하나로 이어 붙이기"""
    concat_list = output_path + "_concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for af in audio_files:
            f.write(f"file '{af}'\n")

    subprocess.run(
        [
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c", "copy", output_path,
            "-y", "-loglevel", "quiet"
        ],
        check=True
    )
    os.unlink(concat_list)


def compose_final_video(
    video_path: str,
    audio_path: str,
    subtitle_path: str,
    output_path: str
):
    """영상 + 음성 + 자막 최종 합성"""
    video_duration = get_media_duration(video_path)
    audio_duration = get_media_duration(audio_path)

    temp_video = None

    # 음성이 영상보다 길면 영상 루프
    if audio_duration > video_duration and video_duration > 0:
        print(f"  📌 음성({audio_duration:.1f}초) > 영상({video_duration:.1f}초) → 영상 자동 루프")
        loops = int(audio_duration / video_duration) + 2
        temp_video = audio_path.replace(".mp3", "_looped_video.mp4")
        subprocess.run(
            [
                "ffmpeg",
                "-stream_loop", str(loops),
                "-i", video_path,
                "-t", str(audio_duration),
                "-c", "copy",
                temp_video,
                "-y", "-loglevel", "quiet"
            ],
            check=True
        )
        input_video = temp_video
    else:
        input_video = video_path

    # 자막 경로 이스케이프 (ffmpeg 요구사항)
    sub_escaped = subtitle_path.replace("\\", "/").replace(":", "\\:")

    print("  🎞 ffmpeg 영상 합성 중...")
    result = subprocess.run(
        [
            "ffmpeg",
            "-i", input_video,
            "-i", audio_path,
            "-vf", f"ass={sub_escaped}",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            output_path,
            "-y", "-loglevel", "warning"
        ]
    )

    if temp_video and os.path.exists(temp_video):
        os.unlink(temp_video)

    return result.returncode == 0


# ==================== 환경 체크 ====================

def check_ffmpeg() -> bool:
    """ffmpeg 설치 여부 확인"""
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def print_ffmpeg_install_guide():
    system = platform.system()
    print("\n❌ ffmpeg가 설치되어 있지 않습니다.")
    print("  ffmpeg는 이 프로그램의 핵심 도구입니다.\n")
    if system == "Darwin":
        print("  macOS 설치 방법:")
        print("    brew install ffmpeg")
        print("\n  (Homebrew가 없다면: https://brew.sh)")
    elif system == "Windows":
        print("  Windows 설치 방법:")
        print("    winget install ffmpeg")
        print("  또는 https://ffmpeg.org/download.html 에서 다운로드")
    else:
        print("  Linux 설치 방법:")
        print("    sudo apt install ffmpeg   # Ubuntu/Debian")
        print("    sudo yum install ffmpeg   # CentOS/RHEL")


# ==================== 메인 ====================

async def main():
    print_header()

    # ffmpeg 체크
    if not check_ffmpeg():
        print_ffmpeg_install_guide()
        sys.exit(1)

    # --- 1. 영상 파일 ---
    print("\n📂 파일 입력")
    print("-" * 40)
    while True:
        video_path = input("영상 파일 경로: ").strip().strip('"').strip("'")
        if os.path.exists(video_path):
            break
        print(f"  ❌ 파일을 찾을 수 없습니다: {video_path}")

    # --- 2. 텍스트 파일 ---
    while True:
        text_path = input("텍스트 파일 경로: ").strip().strip('"').strip("'")
        if os.path.exists(text_path):
            break
        print(f"  ❌ 파일을 찾을 수 없습니다: {text_path}")

    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()

    sentences = split_sentences(text)
    print(f"\n  ✅ 총 {len(sentences)}개 문장 감지됨")
    for i, s in enumerate(sentences[:3], 1):
        print(f"     {i}. {s[:40]}{'...' if len(s) > 40 else ''}")
    if len(sentences) > 3:
        print(f"     ... 외 {len(sentences) - 3}개")

    # --- 3. TTS 선택 ---
    voice_key = show_menu("TTS 음성 선택", VOICE_OPTIONS)
    voice_config = VOICE_OPTIONS[voice_key]

    # --- 4. 자막 스타일 선택 ---
    style_key = show_menu("자막 스타일 선택", SUBTITLE_STYLES)

    # --- 5. 출력 경로 ---
    input_stem = Path(video_path).stem
    default_output = f"{input_stem}_output.mp4"
    output_input = input(f"\n출력 파일명 (엔터 = {default_output}): ").strip()
    output_path = output_input if output_input else default_output

    print("\n" + "=" * 55)
    print("  ⏳ 처리 시작")
    print("=" * 55)

    temp_dir = tempfile.mkdtemp(prefix="video_tts_")

    try:
        # --- 6. TTS 음성 생성 ---
        print(f"\n🎙 음성 생성 중... ({voice_config['name']})")
        audio_files = []
        all_word_timings = []

        for i, sentence in enumerate(sentences):
            audio_out = os.path.join(temp_dir, f"audio_{i:04d}.mp3")
            print(f"  [{i + 1}/{len(sentences)}] {sentence[:35]}{'...' if len(sentence) > 35 else ''}")
            word_timings = await generate_audio(sentence, voice_config, audio_out)
            audio_files.append(audio_out)
            all_word_timings.append(word_timings)

        # --- 7. 오디오 합치기 ---
        print("\n🔊 오디오 파일 병합 중...")
        merged_audio = os.path.join(temp_dir, "merged_audio.mp3")
        merge_audio_files(audio_files, merged_audio)

        # --- 8. 자막 타이밍 계산 ---
        print("\n📝 자막 생성 중...")
        sentence_offsets = [0.0]
        for af in audio_files[:-1]:
            duration = get_media_duration(af)
            sentence_offsets.append(sentence_offsets[-1] + duration)

        sentence_timings = []
        for i, af in enumerate(audio_files):
            start = sentence_offsets[i]
            end = start + get_media_duration(af)
            sentence_timings.append((start, end))

        # --- 9. 자막 파일 생성 ---
        font_path = find_korean_font()
        font_name = Path(font_path).stem if font_path else "Arial"
        subtitle_path = os.path.join(temp_dir, "subtitles.ass")

        if style_key == "1":
            build_subtitles_style1(sentences, sentence_timings, font_name, subtitle_path)
        else:
            build_subtitles_style2(
                sentences, sentence_timings, all_word_timings, font_name, subtitle_path
            )

        # --- 10. 최종 영상 합성 ---
        print("\n🎬 영상 합성 중... (시간이 걸릴 수 있습니다)")
        success = compose_final_video(video_path, merged_audio, subtitle_path, output_path)

        if success:
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            print(f"\n{'=' * 55}")
            print(f"  ✅ 완성!")
            print(f"  📁 출력 파일: {output_path}")
            print(f"  📏 파일 크기: {file_size:.1f} MB")
            print(f"{'=' * 55}\n")
        else:
            print("\n❌ 영상 합성 중 오류가 발생했습니다.")

    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다.")
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        raise
    finally:
        # 임시 파일 정리
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
