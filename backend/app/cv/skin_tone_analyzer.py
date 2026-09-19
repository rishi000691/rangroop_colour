"""
Skin Tone & Undertone Analyzer (Phase 1 AI Core - Rangroop)
==========================================================

This script performs precise skin tone analysis from a facial photograph using:
1. MediaPipe Face Mesh for facial landmark detection and region segmentation.
2. Targeted masking of forehead and cheek regions (excluding eyes, lips, hair, shadows, highlights).
3. CIE L*a*b* color space representation for illumination-robust color measurement.
4. K-Means clustering (k=1..3) to isolate the dominant skin pigment.
5. ITA (Individual Typology Angle) for skin depth / dermatological skin type.
6. Hue Angle (arctan(b*/a*)) for skin undertone classification (Warm, Cool, Neutral, Olive).

Why CIE L*a*b* Color Space Instead of RGB?
-----------------------------------------
- RGB space conflates luminance (brightness) and chrominance (color information) across all three channels (R, G, B). A change in lighting shifts R, G, and B non-linearly.
- CIE L*a*b* explicitly decouples Perceptual Lightness (L*, range 0 to 100) from opponent color axes:
  * a*: Green (-) to Red (+) axis
  * b*: Blue (-) to Yellow (+) axis
- Measuring skin tone in L*a*b* space allows separate evaluation of:
  * Lightness / Melanin content (via L* and b* in the ITA formula).
  * Redness vs. Yellowness axis (via a* and b* in the Hue Angle formula).

ITA (Individual Typology Angle) Formula & Physics:
-------------------------------------------------
  ITA = arctan((L* - 50) / b*) * (180 / pi)

- L* measures overall skin lightness (0 = pure black, 100 = pure white).
- b* measures yellow pigment contribution (higher = yellower/tanner).
- Subtracting 50 centers L* around medium lightness. The ratio (L* - 50) / b* reflects
  how light the skin is relative to its yellow pigmentation.
- Dermatological classification (Chardon et al., 1991):
  * ITA > 55°         : Very Light
  * 41° < ITA <= 55°  : Light
  * 28° < ITA <= 41°  : Intermediate
  * 10° < ITA <= 28°  : Tan
  * -30° < ITA <= 10° : Dark
  * ITA <= -30°       : Very Dark

Undertone (Hue Angle) Formula & Physics:
---------------------------------------
  Hue Angle (h_ab) = arctan2(b*, a*) * (180 / pi)

- ITA alone CANNOT distinguish warm from cool undertones because ITA ignores the a* (redness) axis.
  Two skin tones with identical L* and b* will have the exact same ITA, even if one is rosy (high a*) and the other is golden (moderate a*).
- Hue Angle measures the vector angle in the a*-b* chromaticity plane:
  * High Hue Angle (> 58°): Yellowness (b*) dominates over Redness (a*) -> WARM undertone.
  * Low Hue Angle (< 52°): Redness (a*) is prominent relative to Yellowness (b*) -> COOL undertone (pink/rosy).
  * Moderate Hue Angle (52° to 58°): Balanced red/yellow ratio -> NEUTRAL undertone.
  * Low Redness relative to total chroma or elevated Hue Angle with muted saturation -> OLIVE undertone.

Usage (CLI):
------------
  python3 skin_tone_analyzer.py path/to/image.jpg
  python3 skin_tone_analyzer.py path/to/image.jpg --k 3 --save-preview preview.jpg
"""

import sys
import json
import argparse
import math
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

import cv2
import numpy as np

# Protobuf 4/5/6 compatibility fix for MediaPipe in Python 3.9+
import google.protobuf.symbol_database
from google.protobuf import message_factory

if not hasattr(google.protobuf.symbol_database.SymbolDatabase, 'GetPrototype'):
    def _GetPrototype(self, descriptor):
        return message_factory.GetMessageClass(descriptor)
    google.protobuf.symbol_database.SymbolDatabase.GetPrototype = _GetPrototype

import mediapipe as mp
from sklearn.cluster import KMeans

try:
    from app.cv.palette_lookup import get_color_palette_from_analysis
except ImportError:
    from palette_lookup import get_color_palette_from_analysis


# MediaPipe 468 Face Mesh Landmark Indices for specific regions
# Forehead: Upper boundary + lower boundary above eyebrows
FOREHEAD_LANDMARKS = [
    10, 338, 297, 332, 284, 251, 21, 54, 103, 67, 109,  # Upper forehead line
    107, 66, 105, 63, 70, 300, 293, 334, 296, 336       # Above brows
]

# Left Cheek (Viewer's Left / Subject's Right)
LEFT_CHEEK_LANDMARKS = [
    116, 117, 118, 101, 205, 207, 187, 123, 147, 213, 192
]

# Right Cheek (Viewer's Right / Subject's Left)
RIGHT_CHEEK_LANDMARKS = [
    345, 346, 347, 330, 425, 427, 410, 352, 376, 433, 412
]


def classify_ita(ita: float) -> str:
    """
    Classify skin depth / type using standard dermatological ITA boundaries (Chardon et al., 1991).
    """
    if ita > 55.0:
        return "Very Light"
    elif ita > 41.0:
        return "Light"
    elif ita > 28.0:
        return "Intermediate"
    elif ita > 10.0:
        return "Tan"
    elif ita > -30.0:
        return "Dark"
    else:
        return "Very Dark"


def classify_undertone(a_star: float, b_star: float) -> Tuple[str, float]:
    """
    Classify skin undertone based on CIE L*a*b* chromaticity values (a*, b*).
    Returns (undertone_name, hue_angle_degrees).
    """
    # Calculate Hue Angle in degrees (0 to 360)
    # atan2(y, x) where y = b* (yellow), x = a* (red)
    rad = math.atan2(b_star, a_star)
    hue_angle = math.degrees(rad) % 360.0

    # Chroma (color saturation)
    chroma = math.sqrt(a_star**2 + b_star**2)

    # Ratio of redness to chroma
    red_chroma_ratio = a_star / chroma if chroma > 0 else 0.0

    # Classification logic:
    # Olive: Characterized by low relative redness (low a*) with greenish-yellow undertone,
    # or elevated hue angle with muted a* channel (a_star / chroma < 0.45 or low a* with b* > 10).
    #
    # Use a signed hue angle in (-180°, 180°] for threshold comparisons to correctly handle
    # wraparound near 0°/360°. For example, a raw hue of 356.68° is equivalent to -3.32°,
    # which correctly falls in the Cool range rather than Warm.
    signed_hue = hue_angle if hue_angle <= 180.0 else hue_angle - 360.0

    if red_chroma_ratio < 0.44 and b_star > 8.0:
        undertone = "Olive"
    elif signed_hue >= 58.0:
        undertone = "Warm"
    elif signed_hue <= 52.0:
        undertone = "Cool"
    else:
        undertone = "Neutral"

    return undertone, hue_angle


def estimate_illuminant_bias(
    image_bgr: np.ndarray,
    face_mask: np.ndarray,
) -> Tuple[float, float, float]:
    """
    Estimate scene illuminant bias using gray-world on background pixels
    (everything *outside* the face mask).

    Returns (da_star, db_star, chroma_bias) in CIE L*a*b*:
      - da_star  : mean a* deviation of background from neutral (0)
      - db_star  : mean b* deviation of background from neutral (0)
      - chroma_bias : sqrt(da*² + db*²) — scalar measure of colour cast strength

    A chroma_bias > 6.0 indicates the scene has a meaningful warm/cool cast
    that may have shifted the skin tone measurement.
    """
    h, w = face_mask.shape[:2]
    background_mask = (face_mask == 0).astype(np.uint8) * 255

    # Erode the background mask slightly to avoid face-edge bleed
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    background_mask = cv2.erode(background_mask, kernel, iterations=1)

    bg_pixel_count = int(np.sum(background_mask == 255))
    if bg_pixel_count < 100:
        # Not enough background to estimate — return zero bias
        return 0.0, 0.0, 0.0

    # Convert to Lab
    rgb_float = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    lab_float = cv2.cvtColor(rgb_float, cv2.COLOR_RGB2Lab)

    # Extract background Lab pixels
    bg_lab = lab_float[background_mask == 255]  # shape (N, 3)

    # Under a neutral (D65) illuminant the mean a* and b* of a diverse
    # background should be close to 0. Deviation from 0 is the illuminant bias.
    da_star = float(np.mean(bg_lab[:, 1]))  # mean a* of background
    db_star = float(np.mean(bg_lab[:, 2]))  # mean b* of background
    chroma_bias = math.sqrt(da_star ** 2 + db_star ** 2)

    return da_star, db_star, chroma_bias


def get_region_polygon(landmarks: List[Tuple[int, int]], indices: List[int]) -> np.ndarray:
    """Extract 2D pixel coordinates for given landmark indices and format as a OpenCV polygon."""
    pts = []
    for idx in indices:
        if idx < len(landmarks):
            pts.append(landmarks[idx])
    return np.array(pts, dtype=np.int32)


def extract_skin_mask(image_bgr: np.ndarray, landmarks_px: List[Tuple[int, int]]) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Create a clean binary mask covering forehead and cheek skin regions,
    filtering out specular highlights, shadows, and non-skin artifacts.
    """
    h, w, _ = image_bgr.shape
    combined_mask = np.zeros((h, w), dtype=np.uint8)

    # 1. Create ROI Polygons
    forehead_pts = get_region_polygon(landmarks_px, FOREHEAD_LANDMARKS)
    left_cheek_pts = get_region_polygon(landmarks_px, LEFT_CHEEK_LANDMARKS)
    right_cheek_pts = get_region_polygon(landmarks_px, RIGHT_CHEEK_LANDMARKS)

    # Draw convex hulls to form smooth skin patches
    if len(forehead_pts) > 3:
        cv2.fillConvexPoly(combined_mask, cv2.convexHull(forehead_pts), 255)
    if len(left_cheek_pts) > 3:
        cv2.fillConvexPoly(combined_mask, cv2.convexHull(left_cheek_pts), 255)
    if len(right_cheek_pts) > 3:
        cv2.fillConvexPoly(combined_mask, cv2.convexHull(right_cheek_pts), 255)

    # Slightly erode the mask to avoid edges near hair/eyes/background
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    eroded_mask = cv2.erode(combined_mask, kernel, iterations=1)

    # 2. Filter out extreme highlights (glare) and deep shadows
    # Convert image to LAB to evaluate L* channel lightness
    rgb_float = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    lab_float = cv2.cvtColor(rgb_float, cv2.COLOR_RGB2Lab)
    l_channel = lab_float[:, :, 0]

    # Skin pixels within initial mask
    masked_l = l_channel[eroded_mask == 255]

    if len(masked_l) == 0:
        return eroded_mask, {"valid_pixel_count": 0, "quality_warning": "Mask region empty after landmark poly fill"}

    # Exclude shadows (L* < 20) and highlights (L* > 92) or 5th-95th percentiles
    l_low = max(20.0, float(np.percentile(masked_l, 5)))
    l_high = min(92.0, float(np.percentile(masked_l, 95)))

    valid_lighting_mask = (l_channel >= l_low) & (l_channel <= l_high)
    final_mask = cv2.bitwise_and(eroded_mask, eroded_mask, mask=valid_lighting_mask.astype(np.uint8) * 255)

    valid_pixels_count = int(np.sum(final_mask == 255))
    info = {
        "valid_pixel_count": valid_pixels_count,
        "l_range": (round(l_low, 1), round(l_high, 1)),
        "forehead_pts": len(forehead_pts),
        "left_cheek_pts": len(left_cheek_pts),
        "right_cheek_pts": len(right_cheek_pts)
    }

    return final_mask, info


def analyze_skin_tone(
    image_path: str,
    k_clusters: int = 3,
    save_preview_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main function to analyze facial skin tone and undertone from an image path.

    Returns a JSON-serializable dictionary with:
    - dominant_lab: [L*, a*, b*]
    - ita_value: float
    - skin_type: str (Very Light .. Dark)
    - hue_angle: float
    - undertone: str (Warm, Cool, Neutral, Olive)
    - confidence_notes: str
    """
    path = Path(image_path)
    if not path.is_file():
        return {
            "error": "INVALID_IMAGE_PATH",
            "message": f"Image file not found: {image_path}"
        }

    # Load image using OpenCV
    image_bgr = cv2.imread(str(path))
    if image_bgr is None:
        return {
            "error": "INVALID_IMAGE_FORMAT",
            "message": f"Unable to decode image from path: {image_path}"
        }

    h, w, _ = image_bgr.shape
    if h < 60 or w < 60:
        return {
            "error": "POOR_IMAGE_QUALITY",
            "message": f"Image resolution too low ({w}x{h} px). Minimum resolution required is 60x60 px."
        }

    # Step 1: Detect face mesh landmarks with MediaPipe
    mp_face_mesh = mp.solutions.face_mesh
    with mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=2,
        refine_landmarks=False,
        min_detection_confidence=0.5
    ) as face_mesh:
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(image_rgb)

        if not results.multi_face_landmarks or len(results.multi_face_landmarks) == 0:
            return {
                "error": "NO_FACE_DETECTED",
                "message": "No face detected in the image. Ensure the face is clear, well-lit, and front-facing."
            }

        if len(results.multi_face_landmarks) > 1:
            return {
                "error": "MULTIPLE_FACES_DETECTED",
                "message": f"Detected {len(results.multi_face_landmarks)} faces. Please provide an image with a single face."
            }

        face_landmarks = results.multi_face_landmarks[0]
        landmarks_px = [
            (int(lm.x * w), int(lm.y * h)) for lm in face_landmarks.landmark
        ]

    # Step 2: Create skin mask for forehead and cheeks
    mask, mask_info = extract_skin_mask(image_bgr, landmarks_px)

    if mask_info["valid_pixel_count"] < 50:
        return {
            "error": "POOR_IMAGE_QUALITY",
            "message": "Insufficient valid skin pixels extracted. Face may be obscured, shadowy, or extreme angle."
        }

    # Save diagnostic preview image if requested
    if save_preview_path:
        preview = image_bgr.copy()
        # Draw landmarks overlay
        for pt in landmarks_px:
            cv2.circle(preview, pt, 1, (0, 255, 0), -1)
        # Highlight mask regions in semi-transparent blue
        mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        preview = cv2.addWeighted(preview, 0.7, mask_3ch, 0.3, 0)
        cv2.imwrite(save_preview_path, preview)

    # Step 3: Convert image to CIE L*a*b* space
    # Normalize RGB to [0, 1] float32 for standard CIE L*a*b* conversion (L: 0..100, a: -128..127, b: -128..127)
    rgb_float = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    lab_float = cv2.cvtColor(rgb_float, cv2.COLOR_RGB2Lab)

    # Extract masked skin pixels
    skin_lab_pixels = lab_float[mask == 255]  # Shape: (N, 3)

    # Step 4: Run K-Means Clustering on LAB pixels to find dominant skin color
    num_clusters = min(k_clusters, len(skin_lab_pixels))
    kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
    kmeans.fit(skin_lab_pixels)

    # Find dominant cluster (the cluster with largest number of pixel assignments)
    labels, counts = np.unique(kmeans.labels_, return_counts=True)
    dominant_cluster_idx = labels[np.argmax(counts)]
    dominant_lab = kmeans.cluster_centers_[dominant_cluster_idx]

    l_star, a_star, b_star = float(dominant_lab[0]), float(dominant_lab[1]), float(dominant_lab[2])

    # Step 5: Calculate ITA (Individual Typology Angle) for skin depth
    # ITA = arctan((L* - 50) / b*) * (180 / pi)
    # Avoid division by zero if b* is close to 0
    b_denom = b_star if abs(b_star) > 1e-6 else 1e-6
    ita_rad = math.atan((l_star - 50.0) / b_denom)
    ita_value = math.degrees(ita_rad)
    skin_type = classify_ita(ita_value)

    # Step 6: Calculate Hue Angle for Undertone classification
    undertone, hue_angle = classify_undertone(a_star, b_star)

    # Step 7: Estimate illuminant bias (Bug 3 — lighting normalisation)
    # Use gray-world on background pixels to detect warm/cool lighting cast.
    # A high chroma_bias means the scene illuminant is not neutral D65, which
    # means the raw a*/b* skin values may be shifted and undertone is unreliable.
    da_star, db_star, chroma_bias = estimate_illuminant_bias(image_bgr, mask)

    # Confidence threshold: chroma_bias > 6 ≈ noticeable warm/cool cast
    _ILLUMINANT_BIAS_THRESHOLD = 6.0
    if chroma_bias > _ILLUMINANT_BIAS_THRESHOLD:
        undertone_confidence = "low"
        confidence_suffix = (
            f" ⚠ Lighting cast detected (scene chroma bias {chroma_bias:.1f}, "
            f"da*={da_star:.1f}, db*={db_star:.1f}). "
            "Undertone result may be unreliable — retake photo in natural daylight."
        )
    else:
        undertone_confidence = "high"
        confidence_suffix = ""

    # Formulate confidence notes
    confidence_notes = (
        f"Analyzed {mask_info['valid_pixel_count']} skin pixels across forehead & cheeks. "
        f"Dominant cluster weight: {round(float(np.max(counts) / len(skin_lab_pixels) * 100), 1)}%. "
        f"Luminance Range: {mask_info['l_range'][0]} to {mask_info['l_range'][1]} L*."
        + confidence_suffix
    )

    base_result = {
        "success": True,
        "dominant_lab": [round(l_star, 2), round(a_star, 2), round(b_star, 2)],
        "ita_value": round(ita_value, 2),
        "skin_type": skin_type,
        "hue_angle": round(hue_angle, 2),
        "undertone": undertone,
        "undertone_confidence": undertone_confidence,
        "illuminant_bias": round(chroma_bias, 2),
        "confidence_notes": confidence_notes
    }

    return get_color_palette_from_analysis(base_result)


def main():
    parser = argparse.ArgumentParser(
        description="Rangroop CV Engine - Skin Tone & Undertone Analysis Script"
    )
    parser.add_argument(
        "image_path",
        nargs="?",
        help="Path to the input image file (e.g. photo.jpg)"
    )
    parser.add_argument(
        "--k",
        type=int,
        default=3,
        help="Number of K-Means clusters for dominant skin color extraction (default: 3)"
    )
    parser.add_argument(
        "--save-preview",
        type=str,
        default=None,
        help="Optional filepath to save diagnostic preview image with landmarks and mask"
    )
    parser.add_argument(
        "--batch-dir",
        type=str,
        default=None,
        help="Directory containing sample images to process in batch mode"
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        default=False,
        help=(
            "Print a human-readable audit report: sampled regions, normalised skin hex, "
            "illuminant bias, undertone confidence, and contrast scores for every palette colour."
        )
    )

    args = parser.parse_args()

    if args.batch_dir:
        batch_path = Path(args.batch_dir)
        if not batch_path.is_dir():
            print(f"Error: Batch directory '{args.batch_dir}' does not exist.", file=sys.stderr)
            sys.exit(1)

        image_files = list(batch_path.glob("*.jpg")) + list(batch_path.glob("*.png")) + list(batch_path.glob("*.jpeg"))
        print(f"Processing {len(image_files)} sample images in batch mode...\n")

        results = []
        for img_f in image_files:
            res = analyze_skin_tone(str(img_f), k_clusters=args.k)
            res["filename"] = img_f.name
            results.append(res)
            print(f"[{img_f.name}] -> Skin Type: {res.get('skin_type')}, Undertone: {res.get('undertone')} (ITA: {res.get('ita_value')}, Hue: {res.get('hue_angle')})")

        print("\nComplete Batch JSON:")
        print(json.dumps(results, indent=2))
        return

    if not args.image_path:
        parser.print_help()
        print("\nError: Please provide an image file path or specify --batch-dir.", file=sys.stderr)
        sys.exit(1)

    result = analyze_skin_tone(
        args.image_path,
        k_clusters=args.k,
        save_preview_path=args.save_preview
    )

    if args.test_mode and result.get("success"):
        # ── Test/Audit report (Bug 4) ─────────────────────────────────────────
        import math as _math

        def _lab_to_hex_approx(lab):
            """Quick Lab -> sRGB conversion for display (D65, sRGB)."""
            L, a, b = lab
            fy = (L + 16) / 116
            fx = a / 500 + fy
            fz = fy - b / 200
            def _finv(t): return t**3 if t > 0.206897 else (t - 16/116) / 7.787
            X = 0.95047 * _finv(fx)
            Y = 1.00000 * _finv(fy)
            Z = 1.08883 * _finv(fz)
            r =  3.2406*X - 1.5372*Y - 0.4986*Z
            g = -0.9689*X + 1.8758*Y + 0.0415*Z
            b2=  0.0557*X - 0.2040*Y + 1.0570*Z
            def _gamma(c): return max(0, min(1, 1.055*c**(1/2.4)-0.055 if c>0.0031308 else 12.92*c))
            r, g, b2 = _gamma(r), _gamma(g), _gamma(b2)
            return f"#{int(r*255):02X}{int(g*255):02X}{int(b2*255):02X}"

        def _de76(hex_c, skin_lab):
            """Inline CIE76 delta-E."""
            h = hex_c.lstrip('#')
            r,g,b = (int(h[i:i+2],16)/255 for i in (0,2,4))
            def _lin(c): return c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4
            r,g,b = _lin(r),_lin(g),_lin(b)
            X=r*0.4124564+g*0.3575761+b*0.1804375
            Y=r*0.2126729+g*0.7151522+b*0.0721750
            Z=r*0.0193339+g*0.1191920+b*0.9503041
            def _f(t): return t**(1/3) if t>0.008856 else 7.787*t+16/116
            cL=116*_f(Y/1.0)-16; ca=500*(_f(X/0.95047)-_f(Y/1.0)); cb=200*(_f(Y/1.0)-_f(Z/1.08883))
            return _math.sqrt((cL-skin_lab[0])**2+(ca-skin_lab[1])**2+(cb-skin_lab[2])**2)

        sep = "=" * 64
        skin_lab = result["dominant_lab"]
        skin_hex = _lab_to_hex_approx(skin_lab)

        print(sep)
        print("RANGROOP — TEST MODE AUDIT REPORT")
        print(sep)
        print(f"  Image          : {args.image_path}")
        print(f"  Skin Type      : {result['skin_type']}")
        print(f"  Undertone      : {result['undertone']}  (confidence: {result['undertone_confidence']})")
        print(f"  ITA            : {result['ita_value']:.2f}°")
        print(f"  Dominant Lab   : L*={skin_lab[0]}  a*={skin_lab[1]}  b*={skin_lab[2]}")
        print(f"  Approx skin hex: {skin_hex}")
        print(f"  Illuminant bias: {result['illuminant_bias']:.2f} (threshold 6.0)")
        print(f"  Hue angle      : {result['hue_angle']:.2f}°")
        print()

        # Mask / region info is inside confidence_notes (pixel counts)
        print("  Sampling:")
        print(f"    {result['confidence_notes']}")
        print()

        print(sep)
        print("  FULL JSON RESULT:")
        print(sep)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

