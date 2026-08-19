"""
Clothing Matcher (Phase 3 — Rangroop)
======================================
Given the combined Phase 1 + Phase 2 analysis result, find and rank clothing
catalog items that best match the recommended seasonal palette.

Matching algorithm
------------------
1. For each catalog item, compute CIE76 delta-E between the item's ``color_hex``
   and EACH of the recommended palette colours.
2. An item *matches* if ``min(delta-E vs palette) < PALETTE_MATCH_THRESHOLD`` (15).
   This accepts items whose colour is close to ANY palette colour.
3. A matched item is rejected if its CIE76 delta-E against the measured skin Lab
   is below ``SKIN_CONTRAST_MIN`` (25) — low-contrast items would wash out
   against the person's complexion.
4. Surviving matches are ranked by ascending ``min_palette_de`` (best palette fit
   first) and returned grouped by category.
"""

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


# ─── Thresholds ──────────────────────────────────────────────────────────────

# Max delta-E between item colour and nearest palette colour to count as a match
PALETTE_MATCH_THRESHOLD: float = 15.0

# Min delta-E between item colour and the person's skin — below this the colour
# is too similar to the complexion and is excluded from recommendations
SKIN_CONTRAST_MIN: float = 25.0

# Default catalog path (relative to this file's location)
_DEFAULT_CATALOG_PATH = Path(__file__).parent.parent / "data" / "clothing_items.json"


# ─── Colour math ─────────────────────────────────────────────────────────────

def _hex_to_lab(hex_color: str) -> tuple:
    """Convert hex colour to CIE L*a*b* (D65, sRGB pipeline)."""
    h = hex_color.lstrip('#')
    r, g, b = (int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))

    def _lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _lin(r), _lin(g), _lin(b)
    X = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    Y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    Z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    def _f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    L = 116 * _f(Y / 1.0) - 16
    a = 500 * (_f(X / 0.95047) - _f(Y / 1.0))
    b2 = 200 * (_f(Y / 1.0) - _f(Z / 1.08883))
    return (L, a, b2)


def _de76(lab1: tuple, lab2: tuple) -> float:
    """CIE76 delta-E between two Lab tuples."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(lab1, lab2)))


# ─── Catalog loading ─────────────────────────────────────────────────────────

def _load_catalog(catalog_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load and return the clothing catalog item list."""
    path = Path(catalog_path) if catalog_path else _DEFAULT_CATALOG_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["items"]


# ─── Main matching function ───────────────────────────────────────────────────

def match_clothing(
    analysis_result: Dict[str, Any],
    top_n: int = 12,
    catalog_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Find and rank clothing items that match the recommended palette.

    Parameters
    ----------
    analysis_result : dict
        The combined Phase 1 + Phase 2 result from
        ``get_color_palette_from_analysis()``. Must contain:
        - ``recommended_colors``  : list of hex strings
        - ``dominant_lab``        : [L*, a*, b*] of measured skin tone
    top_n : int
        Maximum number of total matches to return (default 12).
    catalog_path : str | None
        Optional path override for the clothing catalog JSON.

    Returns
    -------
    dict with keys:
        ``matched_items``       : list of matched item dicts, ranked by palette fit
        ``grouped_by_category`` : same items grouped by category
        ``total_matched``       : count before top_n cap
        ``skin_contrast_rejected``: items that matched palette but failed contrast check
    """
    recommended_colors: List[str] = analysis_result.get("recommended_colors", [])
    skin_lab_raw = analysis_result.get("dominant_lab")

    if not recommended_colors:
        return {
            "matched_items": [],
            "grouped_by_category": {},
            "total_matched": 0,
            "skin_contrast_rejected": [],
            "error_note": "No recommended colours available — run Phase 2 first.",
        }

    # Pre-compute Lab for all recommended palette colours
    palette_labs: List[tuple] = [_hex_to_lab(c) for c in recommended_colors]
    skin_lab: Optional[tuple] = tuple(skin_lab_raw) if skin_lab_raw else None

    catalog = _load_catalog(catalog_path)

    matched: List[Dict[str, Any]] = []
    rejected_contrast: List[Dict[str, Any]] = []

    for item in catalog:
        item_hex = item.get("color_hex", "")
        if not item_hex:
            continue

        try:
            item_lab = _hex_to_lab(item_hex)
        except (ValueError, IndexError):
            continue  # skip malformed hex

        # 1. Distance to each palette colour
        palette_distances = [_de76(item_lab, p_lab) for p_lab in palette_labs]
        min_de = min(palette_distances)
        closest_palette_idx = palette_distances.index(min_de)
        closest_palette_color = recommended_colors[closest_palette_idx]

        # 2. Palette match gate
        if min_de > PALETTE_MATCH_THRESHOLD:
            continue

        # 3. Skin contrast gate
        skin_de: Optional[float] = None
        if skin_lab:
            skin_de = _de76(item_lab, skin_lab)
            if skin_de < SKIN_CONTRAST_MIN:
                rejected_contrast.append({
                    **item,
                    "min_palette_de": round(min_de, 1),
                    "skin_de": round(skin_de, 1),
                    "rejection_reason": "low_contrast_vs_skin",
                })
                continue

        matched.append({
            **item,
            "min_palette_de": round(min_de, 1),
            "closest_palette_color": closest_palette_color,
            "skin_de": round(skin_de, 1) if skin_de is not None else None,
        })

    # Sort by best palette fit
    matched.sort(key=lambda x: x["min_palette_de"])
    total_matched = len(matched)
    matched = matched[:top_n]

    # Group by category
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in matched:
        cat = item.get("category", "other")
        grouped.setdefault(cat, []).append(item)

    return {
        "matched_items": matched,
        "grouped_by_category": grouped,
        "total_matched": total_matched,
        "skin_contrast_rejected": rejected_contrast,
    }
