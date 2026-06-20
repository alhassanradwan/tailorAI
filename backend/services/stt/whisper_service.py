"""
services/stt/whisper_service.py

Speech-to-Text using Hugging Face Inference API (Whisper).

No local model loading. Uses remote inference via API.

Requires:
    pip install huggingface_hub

Env:
    HF_TOKEN=your_huggingface_token
"""

import io
import logging
import tempfile
import os
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────
MODEL_ID = os.getenv("WHISPER_MODEL", "openai/whisper-large-v3")
HF_TOKEN = Config.HUGGINGFACE_API_TOKEN

if not HF_TOKEN:
    raise ValueError("HF_TOKEN environment variable is not set.")


_client = None


def _get_client():
    global _client
    if _client is None:
        from huggingface_hub import InferenceClient

        logger.info("[STT] Initializing Hugging Face Inference Client...")
        _client = InferenceClient(
            provider="fal-ai",   # same as your example
            api_key=HF_TOKEN,
        )
    return _client


def _convert_to_wav_bytes(audio_bytes: bytes, mime_type: str) -> bytes:
    """
    Convert audio to 16 kHz mono WAV (same as before).
    """
    try:
        import soundfile as sf
        import numpy as np

        with io.BytesIO(audio_bytes) as buf:
            try:
                data, sr = sf.read(buf)
            except Exception:
                import librosa
                buf.seek(0)
                data, sr = librosa.load(buf, sr=None, mono=True)

        if data.ndim > 1:
            data = data.mean(axis=1)

        if sr != 16000:
            import librosa
            data = librosa.resample(data, orig_sr=sr, target_sr=16000)

        out_buf = io.BytesIO()
        sf.write(out_buf, data.astype("float32"), 16000, format="WAV")
        return out_buf.getvalue()

    except Exception as e:
        logger.warning("[STT] Audio conversion failed (%s), sending raw audio.", e)
        return audio_bytes


class WhisperService:

    @staticmethod
    def transcribe(
        audio_bytes: bytes,
        mime_type: str = "audio/webm",
        language: Optional[str] = None,
    ) -> dict:

        if not audio_bytes:
            raise ValueError("No audio data received.")

        client = _get_client()

        # Convert audio
        wav_bytes = _convert_to_wav_bytes(audio_bytes, mime_type)

        # Save temp file (API expects file path or file-like)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes)
            tmp_path = tmp.name

        try:
            logger.info("[STT] Sending audio to Hugging Face API...")

            # API call
            result = client.automatic_speech_recognition(
                tmp_path,
                model=MODEL_ID,
            )

            # HF sometimes returns string OR dict depending on backend
            if isinstance(result, dict):
                text = (result.get("text") or "").strip()
            else:
                text = str(result).strip()

            logger.info("[STT] Transcription done: %d chars", len(text))

            return {
                "text": text,
                "language": language or "auto",
                "model": MODEL_ID,
                "char_count": len(text),
            }

        finally:
            os.unlink(tmp_path)

    @staticmethod
    def health() -> dict:
        return {
            "model": MODEL_ID,
            "provider": "huggingface-api",
            "loaded": True,  # always "ready" since no local model
        }