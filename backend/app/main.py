"""
Rangroop API — FastAPI Application
====================================
Single-endpoint pipeline that chains Phase 1 (skin tone analysis) and
Phase 2 (palette lookup) and returns a combined JSON result.

Endpoint
--------
POST /analyze
    Accepts: multipart/form-data with an image file field named "file"
    Returns: JSON combining Phase 1 skin/undertone analysis and Phase 2
             palette recommendation.
"""

import io
import os
import logging

from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import cv2
import numpy as np

from app.cv.skin_tone_analyzer import analyze_skin_tone
from app.cv.palette_lookup import get_color_palette_from_analysis

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/tiff",
}

# Errors from Phase 1 that map to 400 vs 422 vs 500
_CLIENT_ERRORS = {
    "NO_FACE_DETECTED",
    "MULTIPLE_FACES_DETECTED",
    "POOR_IMAGE_QUALITY",
    "INVALID_IMAGE_FORMAT",
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rangroop")

# ─────────────────────────────────────────────────────────────────────────────
# App & CORS
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Rangroop API",
    description="Skin tone analysis and clothing palette recommendation API.",
    version="0.1.0",
)

# Allow any localhost / 127.0.0.1 port so a dev React frontend can call freely.
# In production, replace the wildcard with the actual frontend origin.
_CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

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
    import tempfile
    ext = suffix if suffix.startswith(".") else f".{suffix}"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tmp.write(data)
    tmp.flush()
    tmp.close()
    return tmp.name


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}


@app.post(
    "/analyze",
    summary="Analyze skin tone and return palette recommendation",
    response_description="Combined Phase 1 + Phase 2 analysis result",
)
async def analyze(
    file: UploadFile = File(..., description="Portrait image (JPEG/PNG/WebP, max 10 MB)"),
):
    """
    Accepts a single portrait image, runs the Phase 1 skin/undertone
    analyzer and the Phase 2 seasonal palette lookup, then returns the
    combined result.

    **Error codes returned in the JSON body:**

    | HTTP | `error` field              | Meaning                                     |
    |------|----------------------------|---------------------------------------------|
    | 400  | `INVALID_CONTENT_TYPE`     | Uploaded file is not a supported image type |
    | 400  | `FILE_TOO_LARGE`           | File exceeds the 10 MB limit                |
    | 400  | `INVALID_IMAGE_FORMAT`     | File content could not be decoded as image  |
    | 422  | `NO_FACE_DETECTED`         | No face found in the image                  |
    | 422  | `MULTIPLE_FACES_DETECTED`  | More than one face found                    |
    | 422  | `POOR_IMAGE_QUALITY`       | Image too small or skin mask too sparse     |
    | 500  | `ANALYSIS_FAILED`          | Unexpected internal error                   |
    """
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
            status_code=status.HTTP_400_BAD_REQUEST,
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

        # Phase 1: skin tone + undertone
        phase1 = analyze_skin_tone(tmp_path)

        # Phase 2: palette lookup (handles phase1 errors internally)
        result = get_color_palette_from_analysis(phase1)

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

    # ── 5. Map Phase 1 errors to appropriate HTTP status codes ───────────────
    if "error" in result:
        error_code = result.get("error", "")
        if error_code in _CLIENT_ERRORS:
            # 422 for face/quality issues, 400 for format issues
            http_status = (
                status.HTTP_400_BAD_REQUEST
                if error_code == "INVALID_IMAGE_FORMAT"
                else status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        else:
            http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

        raise HTTPException(status_code=http_status, detail=result)

    return JSONResponse(content=result)
