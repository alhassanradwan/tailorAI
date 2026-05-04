import logging
import os
from services.stt.whisper_service import WhisperService

# Enable logs (VERY IMPORTANT)
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)

def test_transcription():
    try:
        # 👉 Load a test audio file (PUT ONE IN YOUR FOLDER)
        base_dir = os.path.dirname(__file__)
        audio_path = os.path.join(base_dir, "test.wav")
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        print(f"Audio size: {len(audio_bytes)} bytes")

        result = WhisperService.transcribe(
            audio_bytes=audio_bytes,
            mime_type="audio/wav",
            language=None
        )

        print("\n✅ TRANSCRIPTION RESULT:")
        print(result)

    except Exception as e:
        import traceback
        print("\n❌ ERROR OCCURRED:")
        traceback.print_exc()


if __name__ == "__main__":
    test_transcription()