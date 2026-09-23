"""
Seasonal Color Palette Lookup (Phase 2 — Rangroop)
===================================================

Maps Phase 1's output (undertone + ITA skin depth) to a recommended clothing
color palette using the 12-season personal color analysis system.

The 12-Season System
--------------------
The four classical seasons (Spring, Summer, Autumn, Winter) are each divided
into three subtypes based on the dominant characteristic of the palette:

  Spring  → Light Spring, True (Warm) Spring, Bright Spring
  Summer  → Light Summer, True (Cool) Summer, Soft Summer
  Autumn  → Soft Autumn, True (Warm) Autumn, Deep Autumn
  Winter  → Bright Winter, True (Cool) Winter, Deep Winter

Each subtype has a curated palette of clothing colors that harmonize with
the skin's undertone and depth.

Season Mapping Logic (Undertone × Depth)
----------------------------------------
The mapping from (undertone, skin_depth) to a season subtype follows
conventional color-analysis heuristics:

  ┌──────────┬─────────────────┬─────────────────┬─────────────────┐
  │ Undertone│  Light Depth    │  Medium Depth   │  Deep Depth     │
  │          │ (VLight/Light)  │ (Intermed/Tan)  │ (Dark/VDark)    │
  ├──────────┼─────────────────┼─────────────────┼─────────────────┤
  │ Warm     │ Light Spring    │ True Spring     │ Deep Autumn     │
  │ Cool     │ Light Summer    │ True Summer     │ Deep Winter     │
  │ Neutral  │ Bright Spring   │ Soft Summer     │ Bright Winter   │
  │ Olive    │ Soft Autumn     │ True Autumn     │ True Winter     │
  └──────────┴─────────────────┴─────────────────┴─────────────────┘

⚠️  ASSUMPTION FLAGS (review against professional color-analysis references):

  1. DEPTH BUCKETING: ITA's six dermatological categories (Very Light, Light,
     Intermediate, Tan, Dark, Very Dark) are collapsed into three buckets:
       • "light"  = Very Light + Light         (ITA > 41°)
       • "medium" = Intermediate + Tan         (10° < ITA ≤ 41°)
       • "deep"   = Dark + Very Dark           (ITA ≤ 10°)
     These cut-points are a reasonable first pass but may need refinement,
     especially the medium/deep boundary at ITA 10°.

  2. OLIVE UNDERTONE MAPPING: Olive is mapped to the Autumn family (Soft
     Autumn for light, True Autumn for medium, Deep Autumn for deep). This
     follows the common color-analysis convention that olive skin has warm-
     muted undertones, but some analysts place light-olive skin into Soft
     Summer instead. Verify with real test subjects.

  3. NEUTRAL UNDERTONE MAPPING: Neutrals are assigned to the "bright" or
     "true" categories that sit at the warm/cool boundary (Bright Spring for
     light, Soft Summer for medium, True Winter for deep). Some analysts
     would swap light-neutral to Light Summer or Bright Winter depending on
     the person's contrast level. This needs human calibration.

  4. HEX CODE ACCURACY: Hex codes are sourced from widely-referenced online
     12-season palette guides (Cardigan Empire, Spicemarketcolour, etc.),
     not from a single authoritative standard. Expect to adjust ±1–2 values
     per palette after visual review.

  5. BRIGHT SPRING vs. BRIGHT WINTER: Both are high-contrast, saturated
     palettes. Bright Spring leans warmer, Bright Winter leans cooler. The
     distinction is subtle and may need Hue Angle fine-tuning for edge cases.

Usage
-----
  from app.cv.palette_lookup import get_color_palette

  # Direct call with Phase 1 output fields
  result = get_color_palette(undertone="Warm", ita_value=45.0)

  # Or pass the entire Phase 1 result dict
  from app.cv.skin_tone_analyzer import analyze_skin_tone
  phase1 = analyze_skin_tone("photo.jpg")
  result = get_color_palette_from_analysis(phase1)
"""

import math
from typing import Dict, Any, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Contrast & colour utilities
# ─────────────────────────────────────────────────────────────────────────────

# Minimum CIE76 delta-E a recommended colour must have against the measured
# skin tone. Below this, the colour is too similar to the skin to be useful.
_MIN_RECOMMENDED_DELTA_E: float = 25.0

# L* threshold above which a colour is considered "near-white". Near-whites
# are excellent for deep skin tones and must never appear on an avoid list.
_NEAR_WHITE_L_THRESHOLD: float = 90.0


def _hex_to_lab(hex_color: str) -> tuple:
    """
    Convert a hex colour string (e.g. '#FF0000') to CIE L*a*b* (D65).
    Uses the standard IEC 61966-2-1 sRGB → XYZ → Lab pipeline.
    """
    h = hex_color.lstrip('#')
    r, g, b = (int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))

    # sRGB gamma expansion (IEC 61966-2-1)
    def _linearise(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _linearise(r), _linearise(g), _linearise(b)

    # Linear sRGB → CIE XYZ (D65 illuminant)
    X = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    Y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    Z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    # CIE XYZ → L*a*b* (D65 white point: Xn=0.95047, Yn=1.0, Zn=1.08883)
    def _f(t: float) -> float:
        return t ** (1.0 / 3.0) if t > 0.008856 else (7.787 * t + 16.0 / 116.0)

    fx, fy, fz = _f(X / 0.95047), _f(Y / 1.0), _f(Z / 1.08883)
    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b2 = 200.0 * (fy - fz)
    return (L, a, b2)


def delta_e_lab(hex_color: str, skin_lab: List[float]) -> float:
    """
    Compute CIE76 delta-E between a hex colour and a skin Lab triple.

    Parameters
    ----------
    hex_color : str
        Hex colour to evaluate (e.g. '#8B7355').
    skin_lab : list
        [L*, a*, b*] of the measured skin tone (from Phase 1 dominant_lab).

    Returns
    -------
    float
        CIE76 colour difference. Values < 25 indicate the colour is too
        close to the skin tone for a useful clothing recommendation.
    """
    cL, ca, cb = _hex_to_lab(hex_color)
    sL, sa, sb = skin_lab[0], skin_lab[1], skin_lab[2]
    return math.sqrt((cL - sL) ** 2 + (ca - sa) ** 2 + (cb - sb) ** 2)


def is_near_white(hex_color: str) -> bool:
    """Return True if the colour's L* is above the near-white threshold."""
    L, _, _ = _hex_to_lab(hex_color)
    return L > _NEAR_WHITE_L_THRESHOLD



# ─────────────────────────────────────────────────────────────────────────────
# 12-Season Palette Data
# ─────────────────────────────────────────────────────────────────────────────

SEASON_PALETTES: Dict[str, Dict[str, Any]] = {

    # ── SPRING FAMILY ────────────────────────────────────────────────────

    "Light Spring": {
        "recommended_colors": [
            "#F5C6A0",  # Warm Peach
            "#FFD700",  # Golden Yellow
            "#98D8C8",  # Mint Green
            "#87CEEB",  # Light Sky Blue
            "#F7CAC9",  # Rose Quartz Pink
            "#FFFDD0",  # Cream
            "#C5E17A",  # Yellow-Green
            "#E8B87E",  # Caramel
        ],
        "avoid_colors": [
            "#000000",  # Jet Black
            "#36013F",  # Deep Purple
            "#800020",  # Burgundy
        ],
        "explanation": (
            "Light Spring complexions have a warm undertone paired with fair to "
            "light skin, giving a delicate, sunlit quality. These palettes "
            "emphasize warm yet gentle colors — soft peach, golden yellow, "
            "warm pastels, and light greens — that echo the warmth in the skin "
            "without overwhelming the lightness. Heavy darks like black, deep "
            "purple, and burgundy create too stark a contrast and can make the "
            "complexion look washed-out or sallow."
        ),
    },

    "True Spring": {
        "recommended_colors": [
            "#FF6347",  # Tomato Red
            "#FF8C00",  # Dark Orange
            "#FFD700",  # Golden Yellow
            "#32CD32",  # Lime Green
            "#40E0D0",  # Turquoise
            "#FF7F50",  # Coral
            "#F0E68C",  # Khaki / Warm Sand
            "#E2725B",  # Terra Cotta
        ],
        "avoid_colors": [
            "#000000",  # Jet Black
            "#808080",  # Medium Grey
            "#C8A2C8",  # Lilac / Cool Lavender
        ],
        "explanation": (
            "True Spring (also called Warm Spring) skin has a distinctly warm, "
            "golden undertone at medium depth, with visible warmth in the cheeks. "
            "Saturated warm hues — coral, tomato red, golden yellow, turquoise, "
            "and lime green — harmonize with the skin's natural warmth and "
            "create a vibrant, healthy glow. Cool muted tones like lilac, flat "
            "grey, and stark black fight against the inherent warmth, making "
            "the complexion appear dull or yellowed."
        ),
    },

    "Bright Spring": {
        "recommended_colors": [
            "#FF1493",  # Deep Pink
            "#00BFFF",  # Deep Sky Blue
            "#7FFF00",  # Chartreuse
            "#FF4500",  # Orange-Red
            "#FFD700",  # Gold
            "#00CED1",  # Dark Turquoise
            "#FF69B4",  # Hot Pink
            "#ADFF2F",  # Green-Yellow
        ],
        "avoid_colors": [
            "#808080",  # Grey
            "#8B4513",  # Muted Brown
            "#556B2F",  # Dusty Olive
        ],
        "explanation": (
            "Bright Spring complexions are light-skinned with a neutral (neither "
            "strongly warm nor cool) undertone and high natural contrast — often "
            "bright eyes or vivid features. These palettes prioritize clear, "
            "saturated, high-chroma colors like deep pink, sky blue, chartreuse, "
            "and orange-red that match the skin's clarity and vibrancy. Muted, "
            "dusty, or washed-out tones like grey, muted brown, and dusty olive "
            "flatten the complexion and make it look lifeless."
        ),
    },

    # ── SUMMER FAMILY ────────────────────────────────────────────────────

    "Light Summer": {
        "recommended_colors": [
            "#B0C4DE",  # Light Steel Blue
            "#DDA0DD",  # Plum / Soft Lavender
            "#FFB6C1",  # Light Pink
            "#E6E6FA",  # Lavender
            "#C0D6E4",  # Powder Blue
            "#D8BFD8",  # Thistle
            "#ACE1AF",  # Celadon Green
            "#F0E0E0",  # Soft Rose
            "#C05077",  # Deep Rose
            "#2C7273",  # Spruce Green
        ],
        "avoid_colors": [
            "#FF4500",  # Orange-Red
            "#FFD700",  # Bright Gold
            "#000000",  # Jet Black
        ],
        "explanation": (
            "Light Summer complexions have a cool undertone with fair, porcelain-"
            "like skin depth. Soft, muted cool tones — powder blue, lavender, "
            "soft pink, and celadon — complement the cool, delicate quality of "
            "the skin without adding harshness. Bright warm colors like orange-"
            "red and gold clash with the cool undertone, while jet black creates "
            "excessive contrast that overpowers the complexion's softness."
        ),
    },

    "True Summer": {
        "recommended_colors": [
            "#4682B4",  # Steel Blue
            "#BC8F8F",  # Rosy Brown
            "#6B8E9B",  # Dusty Teal
            "#C08081",  # Dusty Rose
            "#708090",  # Slate Grey
            "#9370DB",  # Medium Purple
            "#5F9EA0",  # Cadet Blue
            "#D2B48C",  # Soft Taupe
        ],
        "avoid_colors": [
            "#FF8C00",  # Dark Orange
            "#FFD700",  # Gold
            "#FF0000",  # Bright Red
        ],
        "explanation": (
            "True Summer (Cool Summer) skin has a definitively cool, pink or "
            "blue undertone at medium depth. The palette centers on cool, muted, "
            "mid-value hues — steel blue, dusty rose, medium purple, and slate "
            "grey — that mirror the skin's natural cool softness. Highly "
            "saturated warm colors like orange, gold, and bright red create a "
            "jarring discord with the cool undertone and can make the skin look "
            "ruddy or flushed."
        ),
    },

    "Soft Summer": {
        "recommended_colors": [
            "#778899",  # Light Slate Grey
            "#8FBC8F",  # Dark Sea Green
            "#C4AEAD",  # Dusty Mauve
            "#9DB4C0",  # Muted Sky Blue
            "#A09B8C",  # Warm Greige
            "#B8A9C9",  # Muted Lilac
            "#8B8589",  # Taupe Grey
            "#7A9A7E",  # Sage Green
        ],
        "avoid_colors": [
            "#FF1493",  # Deep Pink / Neon Pink
            "#FF4500",  # Orange-Red
            "#FFFF00",  # Bright Yellow
        ],
        "explanation": (
            "Soft Summer complexions are medium-depth with a neutral undertone "
            "that leans slightly cool. They have low contrast and a muted, "
            "smoky quality. The palette emphasizes dusty, greyed, and softened "
            "tones — sage green, dusty mauve, greige, and muted lilac — that "
            "blend with the skin's natural subtlety. Vivid, electric, or neon "
            "colors like hot pink, orange-red, and bright yellow overwhelm the "
            "complexion and make it look faded by comparison."
        ),
    },

    # ── AUTUMN FAMILY ────────────────────────────────────────────────────

    "Soft Autumn": {
        "recommended_colors": [
            "#C2B280",  # Sand / Dark Khaki
            "#BC8F8F",  # Rosy Brown
            "#8B7D6B",  # Warm Taupe
            "#A0522D",  # Sienna
            "#9CAF88",  # Muted Sage
            "#C5A880",  # Warm Camel
            "#D4A76A",  # Soft Mustard
            "#967969",  # Cocoa
            "#C04000",  # Mahogany
            "#4A5D23",  # Deep Olive
        ],
        "avoid_colors": [
            "#FF1493",  # Hot Pink
            "#00FFFF",  # Cyan / Electric Blue
            "#000000",  # Jet Black
        ],
        "explanation": (
            "Soft Autumn complexions — often light-skinned with olive undertones — "
            "have warm but muted coloring with low contrast between hair, skin, and "
            "eyes. Earthy, desaturated warm tones like camel, sienna, sage, and "
            "cocoa harmonize with the skin's warm mutedness without adding harshness. "
            "Bright, electric colors like hot pink and cyan overpower the soft "
            "coloring, and stark black creates too much contrast, making the skin "
            "look sallow."
        ),
    },

    "True Autumn": {
        "recommended_colors": [
            "#D2691E",  # Chocolate
            "#B8860B",  # Dark Goldenrod
            "#CD853F",  # Peru / Warm Tan
            "#8B4513",  # Saddle Brown
            "#556B2F",  # Dark Olive Green
            "#CC5500",  # Burnt Orange
            "#DAA520",  # Goldenrod
            "#A0522D",  # Sienna
        ],
        "avoid_colors": [
            "#FF69B4",  # Hot Pink
            "#E6E6FA",  # Lavender
            "#87CEEB",  # Light Sky Blue
        ],
        "explanation": (
            "True Autumn (Warm Autumn) skin has a distinctly warm, olive or "
            "golden undertone at medium depth. Rich, earthy warm tones — "
            "chocolate, burnt orange, goldenrod, olive green, and sienna — "
            "amplify the skin's natural warmth and create a rich, grounded "
            "look. Cool, light, or pastel shades like lavender, light sky blue, "
            "and hot pink conflict with the warm undertone and can make the "
            "complexion appear greenish or ashy."
        ),
    },

    "Deep Autumn": {
        "recommended_colors": [
            "#8B0000",  # Dark Red
            "#B8860B",  # Dark Goldenrod
            "#2E8B57",  # Sea Green
            "#704214",  # Dark Bronze
            "#800020",  # Burgundy
            "#CC5500",  # Burnt Orange
            "#4E6E4E",  # Forest Green
            "#C04000",  # Mahogany
        ],
        "avoid_colors": [
            "#FFFF00",  # Bright Yellow
            "#FFB6C1",  # Light Pink
            "#E6E6FA",  # Lavender
        ],
        "explanation": (
            "Deep Autumn complexions are deep-skinned with warm or olive undertones, "
            "exhibiting high warmth and rich depth. Bold, saturated warm darks — "
            "dark red, burgundy, forest green, burnt orange, and bronze — "
            "complement the deep warmth of the skin and create a powerful, "
            "harmonious effect. Pale, cool, or icy shades like bright yellow, "
            "light pink, and lavender lack sufficient depth and warmth, and can "
            "look incongruous against the rich skin tone."
        ),
    },

    # ── WINTER FAMILY ────────────────────────────────────────────────────

    "Bright Winter": {
        "recommended_colors": [
            "#FF0000",  # Pure Red
            "#0000FF",  # Royal Blue
            "#FF00FF",  # Magenta / Fuchsia
            "#00FF00",  # Emerald Green (bright)
            "#FFFFFF",  # Crisp White
            "#FF1493",  # Deep Pink
            "#00CED1",  # Dark Turquoise
            "#FFFF00",  # Bright Lemon Yellow
        ],
        "avoid_colors": [
            "#8B7D6B",  # Warm Taupe
            "#D2B48C",  # Tan / Muted Beige
            "#808080",  # Medium Grey
        ],
        "explanation": (
            "Bright Winter is a high-contrast type — the placeholder for cool-"
            "leaning or neutral-leaning individuals who can carry intense, "
            "saturated colors. Vivid primary and jewel tones — pure red, royal "
            "blue, magenta, emerald, and crisp white — resonate with the "
            "complexion's clarity. Muted, warm, or earthy tones like taupe, "
            "tan, and medium grey drain the vibrancy and make the skin look "
            "flat or muddy."
        ),
    },

    "True Winter": {
        "recommended_colors": [
            "#191970",  # Midnight Blue
            "#DC143C",  # Crimson
            "#2F4F4F",  # Dark Slate Grey
            "#4B0082",  # Indigo
            "#FFFFFF",  # Crisp White
            "#008080",  # Teal
            "#800080",  # Purple
            "#C0C0C0",  # Silver
        ],
        "avoid_colors": [
            "#FF8C00",  # Orange
            "#F5DEB3",  # Wheat / Warm Cream
            "#DEB887",  # Burlywood / Warm Beige
        ],
        "explanation": (
            "True Winter (Cool Winter) complexions are deep-skinned with a "
            "neutral undertone, featuring strong contrast between skin, hair, "
            "and features. Icy, bold, high-contrast cool tones — midnight blue, "
            "crimson, indigo, teal, and stark white — mirror the skin's "
            "dramatic cool depth. Warm earth tones like orange, wheat, and warm "
            "cream clash with the cool undertone and soften the natural high-"
            "contrast appearance in an unflattering way."
        ),
    },

    "Deep Winter": {
        "recommended_colors": [
            "#000080",  # Navy Blue
            "#8B0000",  # Dark Red
            "#006400",  # Dark Green
            "#4B0082",  # Indigo
            "#2F4F4F",  # Dark Slate Grey
            "#800020",  # Burgundy
            "#191970",  # Midnight Blue
            "#FFFFFF",  # Stark White (for contrast)
        ],
        "avoid_colors": [
            "#FFD700",  # Gold
            "#FF8C00",  # Orange
            "#F5C6A0",  # Warm Peach
        ],
        "explanation": (
            "Deep Winter complexions have cool undertones at the darkest skin "
            "depths — rich, cool, and dramatic. Bold, deep cool tones — navy, "
            "dark red, dark green, indigo, and burgundy — harmonize with the "
            "skin's inherent depth and coolness while maintaining a striking "
            "presence. Warm and light hues like gold, orange, and peach lack "
            "the depth to complement the complexion and can appear jarring "
            "against the dramatic cool richness of the skin."
        ),
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Mapping Logic: (undertone, depth_bucket) → season subtype
# ─────────────────────────────────────────────────────────────────────────────

# ⚠️  ASSUMPTION: Depth is bucketed into three tiers from ITA's six categories.
#     See docstring at top for full rationale and flags.

SEASON_MAP: Dict[str, Dict[str, str]] = {
    #             light depth         medium depth       deep depth
    "Warm":    {"light": "Light Spring",   "medium": "True Spring",    "deep": "Deep Autumn"},
    "Cool":    {"light": "Light Summer",   "medium": "True Summer",    "deep": "Deep Winter"},
    "Neutral": {"light": "Bright Spring",  "medium": "Soft Summer",    "deep": "Bright Winter"},
    "Olive":   {"light": "Soft Autumn",    "medium": "True Autumn",    "deep": "True Winter"},
}
# ⚠️  ASSUMPTION: Olive/deep → True Winter. Deep olive skin has a greenish
#     cast that reads cool enough for Winter family palettes. Some analysts
#     would place this in Deep Autumn instead. Verify with test subjects.
# ⚠️  ASSUMPTION: Neutral/deep → Bright Winter. High-contrast neutrals at
#     deep skin depth can carry bold, saturated jewel tones. Some analysts
#     prefer True Winter here. Calibrate with real photos.


def _ita_to_depth_bucket(ita_value: float) -> str:
    """
    Collapse ITA's 6 dermatological categories into 3 depth buckets.

    ⚠️  ASSUMPTION: Boundaries at ITA 41° (light/medium) and 10° (medium/deep).
        These align with standard ITA cut-points but may need adjustment
        based on real-world palette testing.

    Mapping:
        ITA > 41°   → "light"   (Very Light + Light)
        10° < ITA ≤ 41° → "medium"  (Intermediate + Tan)
        ITA ≤ 10°   → "deep"    (Dark + Very Dark)
    """
    if ita_value > 41.0:
        return "light"
    elif ita_value > 10.0:
        return "medium"
    else:
        return "deep"


def _ita_to_skin_type(ita_value: float) -> str:
    """Mirror of Phase 1's classify_ita, kept here to avoid import dependency."""
    if ita_value > 55.0:
        return "Very Light"
    elif ita_value > 41.0:
        return "Light"
    elif ita_value > 28.0:
        return "Intermediate"
    elif ita_value > 10.0:
        return "Tan"
    elif ita_value > -30.0:
        return "Dark"
    else:
        return "Very Dark"


def get_season(undertone: str, ita_value: float) -> str:
    """
    Determine the 12-season subtype from undertone and ITA value.

    Parameters
    ----------
    undertone : str
        One of "Warm", "Cool", "Neutral", "Olive" (from Phase 1).
    ita_value : float
        ITA angle in degrees (from Phase 1).

    Returns
    -------
    str
        Season subtype name, e.g. "Light Spring", "Deep Winter".

    Raises
    ------
    ValueError
        If the undertone is not recognized.
    """
    undertone_cap = undertone.strip().capitalize()
    if undertone_cap not in SEASON_MAP:
        raise ValueError(
            f"Unrecognized undertone '{undertone}'. "
            f"Expected one of: {list(SEASON_MAP.keys())}"
        )

    depth_bucket = _ita_to_depth_bucket(ita_value)
    return SEASON_MAP[undertone_cap][depth_bucket]


def get_color_palette(
    undertone: str,
    ita_value: float,
) -> Dict[str, Any]:
    """
    Main lookup function: maps undertone + ITA to a full palette result.

    Parameters
    ----------
    undertone : str
        One of "Warm", "Cool", "Neutral", "Olive".
    ita_value : float
        ITA angle in degrees.

    Returns
    -------
    dict
        {
            "season": str,
            "depth_bucket": str,            # "light" | "medium" | "deep"
            "skin_type": str,               # ITA classification label
            "undertone": str,               # Echo back for convenience
            "recommended_colors": [str],    # 6–8 hex codes
            "avoid_colors": [str],          # 2–3 hex codes
            "explanation": str              # Why these colors work
        }
    """
    season = get_season(undertone, ita_value)
    depth_bucket = _ita_to_depth_bucket(ita_value)
    palette = SEASON_PALETTES[season]

    return {
        "season": season,
        "depth_bucket": depth_bucket,
        "skin_type": _ita_to_skin_type(ita_value),
        "undertone": undertone,
        "recommended_colors": palette["recommended_colors"],
        "avoid_colors": palette["avoid_colors"],
        "explanation": palette["explanation"],
    }


def get_color_palette_from_analysis(phase1_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience wrapper that accepts the full Phase 1 JSON dict directly.

    In addition to the season lookup, this function applies two post-processing
    filters to the raw palette data:

    1. **Contrast filter (Bug 1)**: Any recommended colour with CIE76 delta-E
       < 25 against the measured skin tone is removed, because such colours
       appear washed-out or invisible against the person's complexion.
       Removed entries are reported in ``low_contrast_removed``.

    2. **Near-white avoid filter (Bug 2)**: For deep skin tones (ITA ≤ 10°),
       any near-white colour (L* > 90) is removed from the avoid list, because
       white / near-white provides excellent contrast on deep skin and should
       never be discouraged.
       Removed entries are reported in ``near_white_removed_from_avoid``.

    Parameters
    ----------
    phase1_result : dict
        The output dict from `skin_tone_analyzer.analyze_skin_tone()`.
        Must contain keys ``undertone``, ``ita_value``, and ``dominant_lab``.
        If the dict contains an ``error`` key, it is returned as-is.

    Returns
    -------
    dict
        Combined Phase 1 analysis + Phase 2 palette recommendation, with
        contrast scores and filter audit fields appended.
    """
    # Pass through Phase 1 errors unchanged
    if "error" in phase1_result:
        return phase1_result

    undertone = phase1_result.get("undertone")
    ita_value = phase1_result.get("ita_value")
    skin_lab: Optional[List[float]] = phase1_result.get("dominant_lab")

    if undertone is None or ita_value is None:
        return {
            "error": "MISSING_PHASE1_FIELDS",
            "message": (
                "Phase 1 result must contain 'undertone' and 'ita_value' keys. "
                f"Got keys: {list(phase1_result.keys())}"
            ),
        }

    palette_result = get_color_palette(undertone, ita_value)

    # ── Bug 1: Contrast filter ────────────────────────────────────────────────
    # Remove recommended colours that are too similar to the skin tone.
    low_contrast_removed: List[str] = []
    if skin_lab is not None and len(skin_lab) == 3:
        filtered_recommended: List[str] = []
        for color in palette_result["recommended_colors"]:
            de = delta_e_lab(color, skin_lab)
            if de >= _MIN_RECOMMENDED_DELTA_E:
                filtered_recommended.append(color)
            else:
                low_contrast_removed.append(color)
        palette_result = dict(palette_result)  # make a mutable copy
        palette_result["recommended_colors"] = filtered_recommended

    # ── Bug 2: Near-white avoid filter ───────────────────────────────────────
    # For deep skin tones, near-whites are excellent (high contrast) and must
    # never appear on the avoid list.
    near_white_removed_from_avoid: List[str] = []
    depth_bucket = _ita_to_depth_bucket(ita_value)
    if depth_bucket == "deep":
        filtered_avoid: List[str] = []
        for color in palette_result["avoid_colors"]:
            if is_near_white(color):
                near_white_removed_from_avoid.append(color)
            else:
                filtered_avoid.append(color)
        palette_result["avoid_colors"] = filtered_avoid

    # ── Audit fields ──────────────────────────────────────────────────────────
    # Report what was filtered so results are transparent and testable.
    audit: Dict[str, Any] = {}
    if low_contrast_removed:
        audit["low_contrast_removed"] = low_contrast_removed
    if near_white_removed_from_avoid:
        audit["near_white_removed_from_avoid"] = near_white_removed_from_avoid

    # Add contrast scores for every recommended colour (for test/debug use)
    if skin_lab is not None and len(skin_lab) == 3:
        audit["recommended_contrast_scores"] = {
            c: round(delta_e_lab(c, skin_lab), 1)
            for c in palette_result["recommended_colors"]
        }

    # Merge Phase 1 fields + palette + audit into the final result
    combined = {**phase1_result, **palette_result}
    if audit:
        combined["audit"] = audit
    return combined


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point for standalone testing
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 3:
        print(
            "Usage: python palette_lookup.py <undertone> <ita_value>\n"
            "  undertone : Warm | Cool | Neutral | Olive\n"
            "  ita_value : float (ITA angle in degrees)\n\n"
            "Example:\n"
            "  python palette_lookup.py Warm 45.0\n"
            "  python palette_lookup.py Cool -5.0"
        )
        sys.exit(1)

    ut = sys.argv[1]
    ita = float(sys.argv[2])

    result = get_color_palette(ut, ita)
    print(json.dumps(result, indent=2))
