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
    if red_chroma_ratio < 0.44 and b_star > 8.0:
        undertone = "Olive"
    elif hue_angle >= 58.0:
        undertone = "Warm"
    elif hue_angle <= 52.0:
        undertone = "Cool"
    else:
        undertone = "Neutral"

    return undertone, hue_angle


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

    # Formulate confidence notes
    confidence_notes = (
        f"Analyzed {mask_info['valid_pixel_count']} skin pixels across forehead & cheeks. "
        f"Dominant cluster weight: {round(float(np.max(counts) / len(skin_lab_pixels) * 100), 1)}%. "
        f"Luminance Range: {mask_info['l_range'][0]} to {mask_info['l_range'][1]} L*."
    )

    return {
        "success": True,
        "dominant_lab": [round(l_star, 2), round(a_star, 2), round(b_star, 2)],
        "ita_value": round(ita_value, 2),
        "skin_type": skin_type,
        "hue_angle": round(hue_angle, 2),
        "undertone": undertone,
        "confidence_notes": confidence_notes
    }


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

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
