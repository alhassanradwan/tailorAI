import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from services.stt.whisper_service import WhisperService

logger   = logging.getLogger(__name__)
stt_bp   = Blueprint("stt", __name__)

# Max upload size: 25 MB  (browser MediaRecorder chunks are usually < 5 MB)
MAX_AUDIO_BYTES = 25 * 1024 * 1024


@stt_bp.route("/transcribe", methods=["POST"])
@jwt_required()
def transcribe():
    """
    Transcribe a voice recording to text.

    Accepts multipart/form-data:
        file      : audio file  (required)
        language  : "en" | "ar" | … (optional — default: auto-detect)

    Returns
    -------
    {
        "success":    true,
        "text":       "the transcribed sentence",
        "language":   "en",
        "model":      "openai/whisper-base",
        "char_count": 42
    }
    """
    # ── 1. Validate file presence ─────────────────────────────────────────────
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No audio file provided. Send as 'file' field."}), 400

    audio_file = request.files["file"]
    mime_type  = audio_file.content_type or "audio/webm"
    language   = (request.form.get("language") or "").strip() or None

    audio_bytes = audio_file.read()

    if not audio_bytes:
        return jsonify({"success": False, "error": "Uploaded file is empty."}), 400

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        return jsonify({
            "success": False,
            "error":   f"File too large. Maximum is {MAX_AUDIO_BYTES // (1024*1024)} MB."
        }), 413

    # ── 2. Transcribe ─────────────────────────────────────────────────────────
    try:
        result = WhisperService.transcribe(
            audio_bytes = audio_bytes,
            mime_type   = mime_type,
            language    = language,
        )

        if not result.get("text"):
            return jsonify({
                "success": False,
                "error":   "Could not transcribe audio. Please speak clearly and try again."
            }), 422

        return jsonify({"success": True, **result}), 200

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error("[STT] Transcription error: %s", e, exc_info=True)
        return jsonify({"success": False, "error": "Transcription failed. Please try again."}), 500


@stt_bp.route("/health", methods=["GET"])
def health():
    """No auth — returns model load status."""
    return jsonify({"success": True, **WhisperService.health()}), 200
