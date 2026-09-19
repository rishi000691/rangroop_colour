import io
import os
import logging
from fastapi import APIRouter, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import tempfile

from app.cv.skin_tone_analyzer import analyze_skin_tone
from app.cv.clothing_matcher import match_clothing

router = APIRouter()
logger = logging.getLogger("rangroop")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/tiff",
}

_CLIENT_ERRORS = {
    "NO_FACE_DETECTED",
    "MULTIPLE_FACES_DETECTED",
    "POOR_IMAGE_QUALITY",
    "INVALID_IMAGE_FORMAT",
}


def _decode_upload(data: bytes) -> np.ndarray:
    """Decode raw bytes into an OpenCV BGR image array."""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img


def _write_temp_image(data: bytes, suffix: str) -> str:
    """
    Write image bytes to a NamedTemporaryFile and return the path.
    The caller is responsible for deleting the file afterwards.
    """
    ext = suffix if suffix.startswith(".") else f".{suffix}"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tmp.write(data)
    tmp.flush()
    tmp.close()
    return tmp.name


@router.post(
    "/analyze",
    summary="Analyze skin tone and return palette recommendation",
    response_description="Combined Phase 1 + Phase 2 + Phase 3 analysis result",
)
async def analyze(
    file: UploadFile = File(..., description="Portrait image (JPEG/PNG/WebP, max 10 MB)"),
):
    # ── 1. Validate content-type ─────────────────────────────────────────────
    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_CONTENT_TYPE",
                "message": (
                    f"Unsupported file type '{content_type}'. "
                    f"Accepted types: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}."
                ),
            },
        )

    # ── 2. Read & validate size ──────────────────────────────────────────────
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "FILE_TOO_LARGE",
                "message": (
                    f"Uploaded file is {len(data) // (1024*1024):.1f} MB. "
                    f"Maximum allowed size is {MAX_UPLOAD_BYTES // (1024*1024)} MB."
                ),
            },
        )

    # ── 3. Validate that bytes actually decode as an image ───────────────────
    img_check = _decode_upload(data)
    if img_check is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_IMAGE_FORMAT",
                "message": "File could not be decoded as an image. Ensure it is a valid image file.",
            },
        )

    # ── 4. Write to a temp file (skin_tone_analyzer expects a file path) ─────
    ext = (file.filename or "upload.jpg").rsplit(".", 1)[-1].lower()
    tmp_path = _write_temp_image(data, suffix=ext)

    try:
        logger.info("Analyzing image: %s (%d bytes)", file.filename, len(data))

        # Phase 1 & 2: skin tone + undertone + palette lookup
        result = analyze_skin_tone(tmp_path)

        # Phase 3: clothing catalog matching (only if previous steps succeeded)
        if "error" not in result:
            result["recommended_clothing"] = match_clothing(result)

    except Exception as exc:
        logger.exception("Unexpected error during analysis: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ANALYSIS_FAILED",
                "message": "An unexpected error occurred during analysis. Please try again.",
            },
        )
    finally:
        # Always clean up the temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # ── 5. Map errors to appropriate HTTP status codes ───────────────
    if "error" in result:
        error_code = result.get("error", "")
        if error_code in _CLIENT_ERRORS:
            # 422 for face/quality issues, 400 for format issues
            http_status = (
                status.HTTP_400_BAD_REQUEST
                if error_code == "INVALID_IMAGE_FORMAT"
                else status.HTTP_400_BAD_REQUEST
            )
            # The prompt requested 400 for no face detected, so we'll use 400 for all client errors here
            # to meet the requirement: "No face detected -> 400 with clear message"
        else:
            http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

        raise HTTPException(status_code=http_status, detail=result)

    return JSONResponse(content=result)
