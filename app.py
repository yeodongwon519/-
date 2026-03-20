"""
AI Shorts Maker - 자동 숏츠 영상 생성 웹앱
Streamlit + MoviePy + Pexels API + ElevenLabs API
"""

import os
import re
import uuid
import time
import shutil
import requests
import tempfile
import traceback
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Shorts Maker",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# 상수 및 설정
# ─────────────────────────────────────────────
TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)

PEXELS_API_URL = "https://api.pexels.com/videos/search"
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"

DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel

# 9:16 비율 (Shorts 표준)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920


# ─────────────────────────────────────────────
# 유틸리티 함수
# ─────────────────────────────────────────────

def get_session_dir() -> Path:
    """세션별 임시 디렉토리 생성"""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]
    session_dir = TEMP_DIR / st.session_state.session_id
    session_dir.mkdir(exist_ok=True)
    return session_dir


def cleanup_session_dir():
    """세션 임시 파일 정리"""
    if "session_id" in st.session_state:
        session_dir = TEMP_DIR / st.session_state.session_id
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)


def extract_keywords(script: str) -> list[str]:
    """스크립트에서 검색 키워드 추출"""
    # 문장 단위로 분리
    sentences = re.split(r'[.!?\n]+', script)
    keywords = []

    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "shall", "can", "need",
        "and", "or", "but", "in", "on", "at", "to", "for", "of",
        "with", "by", "from", "as", "into", "through", "that", "this",
        "it", "its", "i", "you", "he", "she", "we", "they", "my", "your",
        "our", "their", "so", "if", "not", "no", "up", "out", "about",
        "이", "가", "을", "를", "은", "는", "의", "에", "에서", "로", "으로",
        "와", "과", "도", "만", "도", "하다", "있다", "이다"
    }

    for sentence in sentences:
        # 단어 추출 (한글/영문 단어만)
        words = re.findall(r'[a-zA-Z가-힣]{3,}', sentence)
        meaningful = [w.lower() for w in words if w.lower() not in stop_words]
        if meaningful:
            # 문장당 최대 2개 키워드 조합
            keyword = " ".join(meaningful[:2])
            if keyword and keyword not in keywords:
                keywords.append(keyword)

    # 키워드가 없으면 기본값
    if not keywords:
        keywords = ["nature", "city", "people"]

    return keywords[:10]  # 최대 10개


def estimate_audio_duration(script: str) -> float:
    """텍스트 길이로 음성 재생 시간 추정 (평균 150단어/분)"""
    words = len(script.split())
    return max(5.0, (words / 150) * 60)


# ─────────────────────────────────────────────
# Pexels API 함수
# ─────────────────────────────────────────────

def search_pexels_videos(keyword: str, api_key: str, per_page: int = 5) -> list[dict]:
    """Pexels에서 세로형 영상 검색"""
    headers = {"Authorization": api_key}
    params = {
        "query": keyword,
        "per_page": per_page,
        "orientation": "portrait",  # 세로형 (9:16)
        "size": "medium",
    }

    try:
        resp = requests.get(PEXELS_API_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("videos", [])
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 401:
            raise ValueError("Pexels API 키가 유효하지 않습니다. 키를 확인하세요.")
        raise RuntimeError(f"Pexels API 오류: {e}")
    except requests.exceptions.Timeout:
        raise RuntimeError("Pexels API 요청 시간이 초과되었습니다.")
    except Exception as e:
        raise RuntimeError(f"Pexels 검색 실패: {e}")


def download_pexels_video(video_info: dict, save_path: Path) -> Path:
    """Pexels 영상 다운로드 - 최적 화질 선택"""
    video_files = video_info.get("video_files", [])
    if not video_files:
        raise RuntimeError("다운로드 가능한 영상 파일이 없습니다.")

    # HD 또는 그에 가까운 해상도 선택
    def quality_score(vf):
        w = vf.get("width", 0)
        h = vf.get("height", 0)
        # 세로형 우선 (높이 > 너비)
        is_portrait = h > w
        return (1 if is_portrait else 0, min(h, 1920))

    sorted_files = sorted(video_files, key=quality_score, reverse=True)
    best_file = sorted_files[0]
    download_url = best_file.get("link")

    if not download_url:
        raise RuntimeError("다운로드 URL을 찾을 수 없습니다.")

    try:
        resp = requests.get(download_url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return save_path
    except Exception as e:
        raise RuntimeError(f"영상 다운로드 실패: {e}")


# ─────────────────────────────────────────────
# ElevenLabs API 함수
# ─────────────────────────────────────────────

def generate_voiceover(script: str, api_key: str, voice_id: str, save_path: Path) -> Path:
    """ElevenLabs TTS로 음성 생성"""
    url = f"{ELEVENLABS_API_URL}/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": script,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code == 401:
            raise ValueError("ElevenLabs API 키가 유효하지 않습니다.")
        if resp.status_code == 422:
            raise ValueError("ElevenLabs: 텍스트가 너무 길거나 형식이 잘못되었습니다.")
        resp.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(resp.content)
        return save_path
    except ValueError:
        raise
    except requests.exceptions.Timeout:
        raise RuntimeError("ElevenLabs API 요청 시간이 초과되었습니다.")
    except Exception as e:
        raise RuntimeError(f"음성 생성 실패: {e}")


def get_audio_duration_elevenlabs(audio_path: Path) -> float:
    """생성된 오디오 파일의 재생 시간 측정"""
    try:
        from moviepy import AudioFileClip
        audio = AudioFileClip(str(audio_path))
        dur = audio.duration
        audio.close()
        return dur
    except Exception:
        # MoviePy 없을 경우 추정값 반환
        file_size = audio_path.stat().st_size
        # MP3 평균 128kbps 기준 추정
        return max(5.0, file_size / (128 * 1024 / 8))


# ─────────────────────────────────────────────
# MoviePy 영상 편집 함수
# ─────────────────────────────────────────────

def check_moviepy_available() -> bool:
    """MoviePy 및 FFmpeg 사용 가능 여부 확인"""
    try:
        import moviepy
        import subprocess
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def create_subtitle_clip(text: str, duration: float, video_size: tuple):
    """자막 클립 생성 (MoviePy 2.x API)"""
    from moviepy import TextClip

    try:
        txt_clip = TextClip(
            text=text,
            font_size=55,
            color="white",
            font="DejaVu-Sans-Bold",
            stroke_color="black",
            stroke_width=3,
            method="caption",
            size=(video_size[0] - 80, None),
            text_align="center",
            duration=duration,
        )
        txt_clip = txt_clip.with_position(("center", video_size[1] * 0.72))
        return txt_clip

    except Exception:
        try:
            txt_clip = TextClip(
                text=text,
                font_size=45,
                color="white",
                stroke_color="black",
                stroke_width=2,
                duration=duration,
            )
            txt_clip = txt_clip.with_position(("center", video_size[1] * 0.72))
            return txt_clip
        except Exception as e:
            st.warning(f"자막 생성 건너뜀: {e}")
            return None


def create_shorts_video(
    video_paths: list[Path],
    audio_path: Path,
    output_path: Path,
    script_sentences: list[str],
    total_duration: float,
    progress_callback=None,
) -> Path:
    """숏츠 영상 최종 생성 (MoviePy 2.x API)"""
    from moviepy import (
        VideoFileClip, AudioFileClip, CompositeVideoClip,
        concatenate_videoclips, ColorClip
    )

    if progress_callback:
        progress_callback(0.5, "영상 클립 처리 중...")

    clips = []
    num_clips = len(video_paths)
    clip_duration = total_duration / max(num_clips, 1)

    for i, vpath in enumerate(video_paths):
        try:
            clip = VideoFileClip(str(vpath), audio=False)

            # 9:16 비율로 크롭/리사이즈
            target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT
            clip_ratio = clip.w / clip.h

            if clip_ratio > target_ratio:
                # 가로가 더 길면 → 좌우 크롭
                new_w = int(clip.h * target_ratio)
                x_center = clip.w / 2
                clip = clip.cropped(
                    x1=x_center - new_w / 2,
                    x2=x_center + new_w / 2,
                )
            else:
                # 세로가 더 길면 → 상하 크롭
                new_h = int(clip.w / target_ratio)
                y_center = clip.h / 2
                clip = clip.cropped(
                    y1=y_center - new_h / 2,
                    y2=y_center + new_h / 2,
                )

            # 해상도 통일
            clip = clip.resized((VIDEO_WIDTH, VIDEO_HEIGHT))

            # 클립 길이 조정
            if clip.duration > clip_duration:
                clip = clip.subclipped(0, clip_duration)
            elif clip.duration < clip_duration:
                # 짧은 클립은 반복 (with_end로 루프 효과)
                loops = int(clip_duration / clip.duration) + 1
                repeated = concatenate_videoclips([clip] * loops)
                clip = repeated.subclipped(0, clip_duration)

            clips.append(clip)

        except Exception as e:
            st.warning(f"클립 {i+1} 처리 오류 (건너뜀): {e}")
            # 검은 화면으로 대체
            black = ColorClip(
                size=(VIDEO_WIDTH, VIDEO_HEIGHT),
                color=[0, 0, 0],
                duration=clip_duration,
            )
            clips.append(black)

    if not clips:
        raise RuntimeError("처리 가능한 영상 클립이 없습니다.")

    if progress_callback:
        progress_callback(0.65, "영상 합치는 중...")

    # 클립 연결
    final_video = concatenate_videoclips(clips, method="compose")

    # 전체 길이를 오디오 길이에 맞춤
    if final_video.duration > total_duration:
        final_video = final_video.subclipped(0, total_duration)

    # 오디오 추가
    audio = AudioFileClip(str(audio_path))
    if audio.duration > final_video.duration:
        audio = audio.subclipped(0, final_video.duration)
    final_video = final_video.with_audio(audio)

    if progress_callback:
        progress_callback(0.75, "자막 합성 중...")

    # 자막 오버레이
    subtitle_clips = []
    if script_sentences:
        sub_duration = total_duration / len(script_sentences)
        for i, sentence in enumerate(script_sentences):
            if sentence.strip():
                start_t = i * sub_duration
                sub_clip = create_subtitle_clip(
                    sentence.strip(),
                    min(sub_duration, total_duration - start_t),
                    (VIDEO_WIDTH, VIDEO_HEIGHT),
                )
                if sub_clip:
                    sub_clip = sub_clip.with_start(start_t)
                    subtitle_clips.append(sub_clip)

    if subtitle_clips:
        final_video = CompositeVideoClip([final_video] + subtitle_clips)

    if progress_callback:
        progress_callback(0.85, "최종 MP4 렌더링 중... (시간이 걸릴 수 있습니다)")

    # MP4 출력
    final_video.write_videofile(
        str(output_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        bitrate="4000k",
        audio_bitrate="192k",
        preset="ultrafast",
        threads=4,
        logger=None,  # MoviePy 로그 숨김
    )

    # 리소스 해제
    final_video.close()
    audio.close()
    for clip in clips:
        try:
            clip.close()
        except Exception:
            pass

    return output_path


# ─────────────────────────────────────────────
# Streamlit UI
# ─────────────────────────────────────────────

def render_sidebar():
    """사이드바: API 키 입력 및 설정"""
    with st.sidebar:
        st.title("⚙️ 설정")
        st.markdown("---")

        st.subheader("🔑 API 키")

        pexels_key = st.text_input(
            "Pexels API Key",
            value=os.getenv("PEXELS_API_KEY", ""),
            type="password",
            help="https://www.pexels.com/api/ 에서 무료로 발급",
        )

        elevenlabs_key = st.text_input(
            "ElevenLabs API Key",
            value=os.getenv("ELEVENLABS_API_KEY", ""),
            type="password",
            help="https://elevenlabs.io/ 에서 발급",
        )

        st.markdown("---")
        st.subheader("🎙️ 음성 설정")

        voice_options = {
            "Rachel (여성, 미국)": "21m00Tcm4TlvDq8ikWAM",
            "Drew (남성, 미국)": "29vD33N1CtxCmqQRPOHJ",
            "Clyde (남성, 영국)": "2EiwWnXFnvU5JabPnv8n",
            "Bella (여성, 미국)": "EXAVITQu4vr4xnSDxMaL",
        }

        selected_voice_name = st.selectbox(
            "TTS 음성 선택",
            options=list(voice_options.keys()),
        )
        voice_id = voice_options[selected_voice_name]

        st.markdown("---")
        st.subheader("ℹ️ 시스템 상태")

        moviepy_ok = check_moviepy_available()
        if moviepy_ok:
            st.success("✅ FFmpeg & MoviePy 준비됨")
        else:
            st.error("❌ FFmpeg 미설치")
            with st.expander("FFmpeg 설치 방법"):
                st.code(
                    "# Ubuntu/Debian\nsudo apt-get install ffmpeg\n\n"
                    "# macOS (Homebrew)\nbrew install ffmpeg\n\n"
                    "# Windows\n# https://ffmpeg.org/download.html",
                    language="bash",
                )

        st.markdown("---")
        st.caption("AI Shorts Maker v1.0")

    return pexels_key, elevenlabs_key, voice_id


def split_script_sentences(script: str) -> list[str]:
    """스크립트를 자막 단위로 분리"""
    # 문장 부호 기준 분리
    sentences = re.split(r'(?<=[.!?。！？])\s+', script.strip())
    # 빈 문자열 제거, 너무 긴 문장은 분리
    result = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        # 50자 이상이면 쉼표나 접속사로 추가 분리
        if len(s) > 50:
            sub = re.split(r',\s+|;\s+', s)
            result.extend([p.strip() for p in sub if p.strip()])
        else:
            result.append(s)
    return result if result else [script]


def main():
    # 세션 상태 초기화
    if "generated_video_path" not in st.session_state:
        st.session_state.generated_video_path = None
    if "generation_error" not in st.session_state:
        st.session_state.generation_error = None

    # 사이드바
    pexels_key, elevenlabs_key, voice_id = render_sidebar()

    # 메인 헤더
    st.title("🎬 AI Shorts Maker")
    st.markdown(
        "스크립트를 입력하면 **9:16 숏츠 영상**을 자동으로 생성합니다.  \n"
        "Pexels 영상 + ElevenLabs 음성 + 자동 자막을 합성합니다."
    )
    st.markdown("---")

    # 스크립트 입력
    st.subheader("📝 스크립트 입력")
    script = st.text_area(
        label="영상 내용을 입력하세요",
        placeholder=(
            "예시:\n"
            "오늘은 서울의 야경을 소개합니다. "
            "한강 다리 위에서 바라보는 밤하늘은 정말 아름답습니다. "
            "네온사인과 불빛이 물 위에 반사되어 환상적인 풍경을 만들어냅니다. "
            "서울을 방문한다면 꼭 한번 야경을 즐겨보세요."
        ),
        height=200,
        max_chars=2000,
    )

    col1, col2 = st.columns(2)
    with col1:
        estimated_duration = estimate_audio_duration(script) if script else 0
        st.metric("예상 재생 시간", f"{estimated_duration:.0f}초" if script else "-")
    with col2:
        keywords = extract_keywords(script) if script else []
        st.metric("추출된 키워드 수", f"{len(keywords)}개" if script else "-")

    if script and keywords:
        with st.expander("🔍 추출된 검색 키워드 미리보기"):
            st.write(keywords)

    st.markdown("---")

    # 생성 버튼
    generate_btn = st.button(
        "🚀 영상 생성하기",
        type="primary",
        disabled=not script,
        use_container_width=True,
    )

    # 이전 에러 표시
    if st.session_state.generation_error:
        st.error(st.session_state.generation_error)

    # 이전 생성 영상 표시
    if st.session_state.generated_video_path:
        vpath = Path(st.session_state.generated_video_path)
        if vpath.exists():
            st.markdown("---")
            st.subheader("🎉 생성 완료!")
            st.video(str(vpath))
            with open(vpath, "rb") as f:
                st.download_button(
                    label="⬇️ MP4 다운로드",
                    data=f,
                    file_name="ai_shorts.mp4",
                    mime="video/mp4",
                    use_container_width=True,
                )

    # 영상 생성 로직
    if generate_btn:
        st.session_state.generated_video_path = None
        st.session_state.generation_error = None

        # 입력 검증
        errors = []
        if not script.strip():
            errors.append("스크립트를 입력해주세요.")
        if not pexels_key.strip():
            errors.append("Pexels API Key를 사이드바에 입력해주세요.")
        if not elevenlabs_key.strip():
            errors.append("ElevenLabs API Key를 사이드바에 입력해주세요.")
        if not check_moviepy_available():
            errors.append(
                "FFmpeg가 설치되지 않았습니다. 사이드바의 설치 가이드를 참고하세요."
            )

        if errors:
            for err in errors:
                st.error(f"❌ {err}")
            st.stop()

        # 생성 프로세스 시작
        session_dir = get_session_dir()
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(value: float, message: str):
            progress_bar.progress(value)
            status_text.text(f"⏳ {message}")

        try:
            # 1단계: 키워드 추출
            update_progress(0.05, "스크립트 분석 중...")
            keywords = extract_keywords(script)
            sentences = split_script_sentences(script)

            # 2단계: ElevenLabs 음성 생성
            update_progress(0.1, "AI 음성 생성 중... (ElevenLabs)")
            audio_path = session_dir / "voiceover.mp3"
            generate_voiceover(script, elevenlabs_key, voice_id, audio_path)

            # 3단계: 음성 길이 측정
            update_progress(0.3, "오디오 분석 중...")
            total_duration = get_audio_duration_elevenlabs(audio_path)
            st.info(f"🎵 생성된 음성 길이: {total_duration:.1f}초")

            # 4단계: Pexels 영상 검색 및 다운로드
            num_clips_needed = max(1, int(total_duration / 5))
            video_paths = []
            used_video_ids = set()

            update_progress(0.35, f"Pexels에서 영상 검색 중... (키워드: {len(keywords)}개)")

            for i, keyword in enumerate(keywords):
                if len(video_paths) >= num_clips_needed:
                    break

                progress_val = 0.35 + (i / len(keywords)) * 0.15
                update_progress(progress_val, f"'{keyword}' 영상 검색 중...")

                try:
                    videos = search_pexels_videos(keyword, pexels_key, per_page=3)
                    for video in videos:
                        if len(video_paths) >= num_clips_needed:
                            break
                        vid_id = video.get("id")
                        if vid_id in used_video_ids:
                            continue

                        vpath = session_dir / f"clip_{len(video_paths):02d}.mp4"
                        try:
                            download_pexels_video(video, vpath)
                            video_paths.append(vpath)
                            used_video_ids.add(vid_id)
                        except Exception as de:
                            st.warning(f"클립 다운로드 실패 (건너뜀): {de}")
                except Exception as se:
                    st.warning(f"'{keyword}' 검색 실패 (건너뜀): {se}")

            if not video_paths:
                raise RuntimeError(
                    "다운로드된 영상이 없습니다. "
                    "Pexels API 키와 인터넷 연결을 확인하세요."
                )

            st.info(f"📹 다운로드된 클립: {len(video_paths)}개")

            # 5단계: 영상 편집 및 합성
            output_path = session_dir / "final_shorts.mp4"
            create_shorts_video(
                video_paths=video_paths,
                audio_path=audio_path,
                output_path=output_path,
                script_sentences=sentences,
                total_duration=total_duration,
                progress_callback=update_progress,
            )

            # 완료
            update_progress(1.0, "✅ 완료!")
            st.session_state.generated_video_path = str(output_path)
            st.balloons()
            st.rerun()

        except ValueError as ve:
            st.session_state.generation_error = f"API 키 오류: {ve}"
            st.rerun()
        except RuntimeError as re_err:
            st.session_state.generation_error = f"생성 오류: {re_err}"
            st.rerun()
        except Exception as e:
            error_detail = traceback.format_exc()
            st.session_state.generation_error = (
                f"예상치 못한 오류가 발생했습니다: {e}\n\n"
                f"상세 내용:\n```\n{error_detail}\n```"
            )
            st.rerun()
        finally:
            progress_bar.empty()
            status_text.empty()

    # 하단 안내
    st.markdown("---")
    with st.expander("📖 사용 가이드"):
        st.markdown(
            """
### 시작하기

1. **API 키 설정**
   - 좌측 사이드바에 Pexels API Key와 ElevenLabs API Key를 입력합니다.
   - 또는 `.env` 파일에 키를 저장하면 자동으로 불러옵니다.

2. **스크립트 작성**
   - 생성하고 싶은 영상의 내용(나레이션)을 입력합니다.
   - 문장 부호(`.`, `!`, `?`)로 구분된 문장이 자막으로 표시됩니다.

3. **영상 생성**
   - `영상 생성하기` 버튼을 클릭하면 자동으로 처리됩니다.
   - 생성 시간: 스크립트 길이에 따라 1~5분 소요

### API 키 발급
- **Pexels**: [https://www.pexels.com/api/](https://www.pexels.com/api/) (무료)
- **ElevenLabs**: [https://elevenlabs.io/](https://elevenlabs.io/) (월 10,000자 무료)

### 주의사항
- FFmpeg가 설치되어 있어야 영상 합성이 가능합니다.
- 생성된 영상은 임시 폴더(`temp/`)에 저장됩니다.
"""
        )


if __name__ == "__main__":
    main()
