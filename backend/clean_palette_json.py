"""
One-off script: Clean palette_lookup.json in-place.

For each palette entry:
  - Remove recommended colours whose CIE76 delta-E against the TYPICAL skin Lab
    of that depth bucket is < 25 (low contrast).
  - Remove near-white colours (L* > 90) from the avoid list of DEEP skin entries
    (Dark / Very Dark).

Depth bucket → typical skin Lab used for contrast check:
  light   (Very Light, Light)       → L*=75, a*=14, b*=18  (approx median light skin)
  medium  (Intermediate, Tan)       → L*=55, a*=14, b*=22  (approx median medium skin)
  deep    (Dark, Very Dark)         → L*=32, a*=12, b*=14  (approx median deep skin)

Run once from backend/:
    python3 clean_palette_json.py
"""

import json
import math
import copy

PALETTE_PATH = "data/palette_lookup.json"
MIN_DELTA_E  = 25.0
NEAR_WHITE_L = 90.0

# Typical Lab per ITA depth bucket (conservative median estimates)
TYPICAL_SKIN_LAB = {
    "light":  (75.0, 14.0, 18.0),
    "medium": (55.0, 14.0, 22.0),
    "deep":   (32.0, 12.0, 14.0),
}

# Map skin_type label → depth bucket
DEPTH_MAP = {
    "Very Light": "light",
    "Light":      "light",
    "Intermediate": "medium",
    "Tan":        "medium",
    "Dark":       "deep",
    "Very Dark":  "deep",
}


def _hex_to_lab(hex_color: str) -> tuple:
    h = hex_color.lstrip('#')
    r, g, b = (int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    def _lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = _lin(r), _lin(g), _lin(b)
    X = r*0.4124564 + g*0.3575761 + b*0.1804375
    Y = r*0.2126729 + g*0.7151522 + b*0.0721750
    Z = r*0.0193339 + g*0.1191920 + b*0.9503041
    def _f(t): return t**(1/3) if t > 0.008856 else 7.787*t + 16/116
    L = 116*_f(Y/1.0) - 16
    a = 500*(_f(X/0.95047) - _f(Y/1.0))
    b2 = 200*(_f(Y/1.0) - _f(Z/1.08883))
    return (L, a, b2)


def _de76(hex_color: str, skin_lab: tuple) -> float:
    cL, ca, cb = _hex_to_lab(hex_color)
    return math.sqrt((cL-skin_lab[0])**2 + (ca-skin_lab[1])**2 + (cb-skin_lab[2])**2)


def _is_near_white(hex_color: str) -> bool:
    L, _, _ = _hex_to_lab(hex_color)
    return L > NEAR_WHITE_L


def clean(data: dict) -> dict:
    data = copy.deepcopy(data)
    palettes = data["palettes"]
    total_rec_removed  = []
    total_avoid_removed = []

    for key, entry in palettes.items():
        skin_type, undertone = key.split("|", 1)
        depth = DEPTH_MAP[skin_type]
        skin_lab = TYPICAL_SKIN_LAB[depth]

        # 1. Filter recommended colours
        kept, removed_rec = [], []
        for c in entry["recommended_colors"]:
            de = _de76(c, skin_lab)
            if de >= MIN_DELTA_E:
                kept.append(c)
            else:
                removed_rec.append((c, round(de, 1)))
        entry["recommended_colors"] = kept

        # 2. Filter avoid colours (near-white only for deep)
        kept_avoid, removed_avoid = [], []
        for c in entry["avoid_colors"]:
            if depth == "deep" and _is_near_white(c):
                removed_avoid.append(c)
            else:
                kept_avoid.append(c)
        entry["avoid_colors"] = kept_avoid

        if removed_rec:
            print(f"  [{key}] removed recommended (low contrast): {removed_rec}")
            total_rec_removed.extend(removed_rec)
        if removed_avoid:
            print(f"  [{key}] removed from avoid (near-white): {removed_avoid}")
            total_avoid_removed.extend(removed_avoid)

    print(f"\nTotal recommended removed : {len(total_rec_removed)}")
    print(f"Total avoid removed       : {len(total_avoid_removed)}")
    return data


if __name__ == "__main__":
    with open(PALETTE_PATH, "r") as f:
        original = json.load(f)

    print(f"Cleaning {PALETTE_PATH} ...")
    cleaned = clean(original)

    with open(PALETTE_PATH, "w") as f:
        json.dump(cleaned, f, indent=2)
    print(f"\n{PALETTE_PATH} updated in-place.")
