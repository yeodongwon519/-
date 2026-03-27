import os
import subprocess
import sys

def extract_srt(audio_path, output_dir, model="base"):
    """
    Whisper로 음성 파일에서 SRT 자막 추출
    model: tiny / base / small / medium / large
    """
    os.makedirs(output_dir, exist_ok=True)

    try:
        import whisper
    except ImportError:
        print("Whisper 설치 중...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openai-whisper", "-q"])
        import whisper

    print(f"🎯 Whisper 모델 로딩: {model}")
    wmodel = whisper.load_model(model)

    print(f"📝 자막 추출 중: {audio_path}")
    result = wmodel.transcribe(audio_path, language="ko")

    # SRT 파일 생성
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    srt_path = os.path.join(output_dir, f"{base_name}.srt")

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"]):
            start = format_time(seg["start"])
            end   = format_time(seg["end"])
            text  = seg["text"].strip()
            f.write(f"{i+1}\n{start} --> {end}\n{text}\n\n")

    print(f"✅ 자막 저장: {srt_path}")
    return srt_path


def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def extract_all(audio_dir, output_dir):
    audio_files = [f for f in os.listdir(audio_dir) if f.endswith(".mp3")]
    if not audio_files:
        print("❌ 음성 파일이 없습니다. TTS 먼저 실행하세요.")
        return

    for audio_file in sorted(audio_files):
        audio_path = os.path.join(audio_dir, audio_file)
        extract_srt(audio_path, output_dir)


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    audio_dir  = os.path.join(base, "output/02_audio")
    output_dir = os.path.join(base, "output/05_subtitle")
    extract_all(audio_dir, output_dir)
