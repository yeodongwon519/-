"""
매매법 유튜브 쇼츠 자동화 파이프라인
사용법: python run_pipeline.py --topic "RSI 매매법"
"""
import os
import sys
import json
import argparse

BASE = os.path.dirname(os.path.abspath(__file__))

def step1_generate_script(topic):
    """Claude API로 대본 생성 (현재는 rsi_script.json 예시 사용)"""
    print(f"\n{'='*50}")
    print(f"[1단계] 대본 생성: {topic}")
    print(f"{'='*50}")
    script_path = os.path.join(BASE, "output/01_script/rsi_script.json")
    if os.path.exists(script_path):
        print(f"✅ 대본 파일 확인: {script_path}")
    else:
        print("❌ 대본 파일 없음. create_script.py 먼저 실행하세요.")
        sys.exit(1)
    return script_path

def step2_create_ppt(script_path):
    print(f"\n{'='*50}")
    print("[2단계] PPT 자동 생성")
    print(f"{'='*50}")
    from create_ppt import create_ppt
    output_path = os.path.join(BASE, "output/03_ppt/rsi_slides.pptx")
    create_ppt(script_path, output_path)
    return output_path

def step3_create_tts(script_path):
    print(f"\n{'='*50}")
    print("[3단계] ElevenLabs TTS 음성 생성")
    print(f"{'='*50}")
    if not os.environ.get("ELEVENLABS_API_KEY"):
        print("⚠️  ELEVENLABS_API_KEY 미설정. TTS 단계 건너뜁니다.")
        print("   → export ELEVENLABS_API_KEY='your_key' 후 재실행")
        return None
    from create_tts import create_all_audio
    audio_dir = os.path.join(BASE, "output/02_audio")
    create_all_audio(script_path, audio_dir)
    return audio_dir

def step4_notice_recording():
    print(f"\n{'='*50}")
    print("[4단계] 트레이딩뷰 녹화 (직접)")
    print(f"{'='*50}")
    print("📌 아래 폴더에 녹화 영상을 저장해주세요:")
    print(f"   {os.path.join(BASE, 'output/04_recording/')}")
    print("📌 파일명 규칙: scene_01.mp4, scene_02.mp4 ...")

def step5_extract_subtitle(audio_dir):
    print(f"\n{'='*50}")
    print("[5단계] Whisper 자막 추출")
    print(f"{'='*50}")
    if audio_dir is None:
        print("⚠️  음성 파일 없음. TTS 완료 후 실행하세요.")
        return
    from extract_subtitle import extract_all
    subtitle_dir = os.path.join(BASE, "output/05_subtitle")
    extract_all(audio_dir, subtitle_dir)

def step6_package():
    print(f"\n{'='*50}")
    print("[6단계] 캡컷 패키지 정리")
    print(f"{'='*50}")
    import shutil
    pkg_dir = os.path.join(BASE, "output/06_capcut_package")
    os.makedirs(pkg_dir, exist_ok=True)

    # 각 폴더에서 파일 복사
    folders = {
        "02_audio":    "음성",
        "03_ppt":      "슬라이드",
        "04_recording":"녹화본",
        "05_subtitle": "자막",
    }
    for src_folder, label in folders.items():
        src = os.path.join(BASE, "output", src_folder)
        dst = os.path.join(pkg_dir, label)
        if os.path.exists(src) and os.listdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
            print(f"✅ {label} 복사 완료")
        else:
            print(f"⚠️  {label} 파일 없음 (건너뜀)")

    print(f"\n📦 캡컷 패키지 위치: {pkg_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="RSI 매매법", help="영상 주제")
    args = parser.parse_args()

    script_path = step1_generate_script(args.topic)
    step2_create_ppt(script_path)
    audio_dir   = step3_create_tts(script_path)
    step4_notice_recording()
    step5_extract_subtitle(audio_dir)
    step6_package()

    print(f"\n{'='*50}")
    print("🎉 파이프라인 완료!")
    print(f"{'='*50}")
    print(f"결과물 위치: {os.path.join(BASE, 'output/')}")
