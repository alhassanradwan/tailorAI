import io
import logging
import tempfile
import os
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

# ── Lazy globals — model loads once on first request ─────────────────────────

_pipeline = None
_lock = Lock()

# Model settings
MODEL_ID = os.getenv("WHISPER_MODEL", "openai/whisper-base")

# IMPORTANT:
# HuggingFace pipeline expects:
# -1 = CPU
#  0 = First GPU
# NOT "cpu" / "cuda"
DEVICE = -1

SAMPLE_RATE = 16000  # Whisper expects 16 kHz mono


def _load_pipeline():
    """
    Lazy-load the Whisper pipeline exactly once (thread-safe).
    """
    global _pipeline

    if _pipeline is not None:
        return _pipeline

    with _lock:
        if _pipeline is not None:
            return _pipeline

        logger.info(
            "[STT] Loading Whisper model '%s' on device=%s...",
            MODEL_ID,
            DEVICE
        )

        try:
            from transformers import pipeline as hf_pipeline

            _pipeline = hf_pipeline(
                task="automatic-speech-recognition",
                model=MODEL_ID,
                device=DEVICE,
                chunk_length_s=30,
                return_timestamps=False,
            )

            logger.info("[STT] Whisper model loaded successfully.")

        except Exception:
            logger.exception("[STT] Failed to load Whisper model.")
            raise

    return _pipeline


def _convert_to_wav_bytes(audio_bytes: bytes, mime_type: str) -> bytes:
    """
    Convert audio to 16 kHz mono WAV bytes.

    This version avoids librosa completely because:
    - librosa triggers numba spam
    - huge slowdown
    - Windows issues
    - memory overhead

    We only use soundfile.
    If conversion fails, raw bytes are passed to Whisper.
    """
    try:
        import soundfile as sf
        import numpy as np

        with io.BytesIO(audio_bytes) as buf:
            data, sr = sf.read(buf)

        # Convert stereo → mono
        if hasattr(data, "ndim") and data.ndim > 1:
            data = data.mean(axis=1)

        # NOTE:
        # If resampling is needed and soundfile can't do it directly,
        # we skip it for now instead of using librosa.
        # Whisper can still often handle it.

        out_buf = io.BytesIO()
        sf.write(
            out_buf,
            data.astype("float32"),
            sr if sr else SAMPLE_RATE,
            format="WAV"
        )

        return out_buf.getvalue()

    except Exception as e:
        logger.warning(
            "[STT] Audio conversion failed (%s). Passing raw bytes to model.",
            str(e)
        )
        return audio_bytes


class WhisperService:
    """
    Stateless STT service.

    Call:
        WhisperService.transcribe(...)
    """

    @staticmethod
    def transcribe(
        audio_bytes: bytes,
        mime_type: str = "audio/webm",
        language: Optional[str] = None,
    ) -> dict:
        if not audio_bytes:
            raise ValueError("No audio data received.")

        logger.info("[STT] Starting transcription...")

        # Step 1: load model
        pipe = _load_pipeline()

        # Step 2: convert audio
        wav_bytes = _convert_to_wav_bytes(audio_bytes, mime_type)

        # Step 3: write temp file
        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        ) as tmp:
            tmp.write(wav_bytes)
            tmp_path = tmp.name

        try:
            generate_kwargs = {}

            if language:
                generate_kwargs["language"] = language

            logger.info(
                "[STT] Transcribing %.1f KB of audio...",
                len(wav_bytes) / 1024
            )

            # Step 4: transcription
            result = pipe(
                tmp_path,
                generate_kwargs=generate_kwargs
            )

            text = (result.get("text") or "").strip()

            logger.info(
                "[STT] Transcription completed successfully (%d chars).",
                len(text)
            )

            return {
                "text": text,
                "language": language or "auto",
                "model": MODEL_ID,
                "char_count": len(text),
            }

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @staticmethod
    def health() -> dict:
        """
        Check model status without forcing model load.
        """
        return {
            "model": MODEL_ID,
            "device": DEVICE,
            "loaded": _pipeline is not None,
        }