import json
import os
import requests

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel (기본 한국어 지원 목소리)
# 한국어에 더 자연스러운 목소리: nPczCjzI2devNBz1zQrb (Brian) 또는 커스텀 목소리 ID 사용 가능

def generate_tts(text, output_path, voice_id=VOICE_ID):
    if not ELEVENLABS_API_KEY:
        print("❌ ELEVENLABS_API_KEY 환경변수를 설정해주세요.")
        return False

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.3,
            "use_speaker_boost": True
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"✅ 음성 저장: {output_path}")
        return True
    else:
        print(f"❌ TTS 실패 (Scene): {response.status_code} - {response.text}")
        return False


def create_all_audio(script_path, output_dir):
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    os.makedirs(output_dir, exist_ok=True)
    all_texts = []

    for i, scene in enumerate(script["scenes"]):
        filename = f"scene_{i+1:02d}_{scene['type']}.mp3"
        output_path = os.path.join(output_dir, filename)
        print(f"\n🎙️ Scene {i+1} TTS 생성 중...")
        generate_tts(scene["tts"], output_path)
        all_texts.append(scene["tts"])

    # 전체 합본 (모든 씬 이어붙이기)
    full_text = " ".join(all_texts)
    full_path = os.path.join(output_dir, "00_full_narration.mp3")
    print(f"\n🎙️ 전체 합본 생성 중...")
    generate_tts(full_text, full_path)
    print(f"\n✅ 전체 완료!")


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(base, "output/01_script/rsi_script.json")
    output_dir  = os.path.join(base, "output/02_audio")
    create_all_audio(script_path, output_dir)
