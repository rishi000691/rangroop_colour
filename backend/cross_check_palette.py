"""
Palette Cross-Check Script
---------------------------
Sanity-checks our rule-based palette_lookup.json against the real
experimental finding from the St Andrews clothing color study
(Perrett & Sprengelmeyer, 2021):

  - Fair/light skin -> participants preferred COOL blue hues
  - Tanned/darker skin -> participants preferred WARM orange/red hues

This is NOT a rigorous statistical validation (their study only covers
White women, fair vs. tanned, no undertone variable). It's a directional
sanity check: does our palette agree with the *general direction* of a
real finding, or does it contradict it?
"""

import json
import colorsys

def hex_to_hue(hex_color):
    """Convert a hex color to its hue angle (0-360) in HSV space."""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360

def is_cool_hue(hue):
    """St Andrews study definition: cool = 90-270 degrees."""
    return 90 <= hue <= 270

def is_warm_hue(hue):
    """Warm = the remainder of the circle (270-360 and 0-90)."""
    return not is_cool_hue(hue)

def check_palette_direction(palette_path):
    with open(palette_path, 'r') as f:
        data = json.load(f)

    palettes = data['palettes']

    print("=" * 70)
    print("CROSS-CHECK: Our palette vs. St Andrews study direction")
    print(f"Checking all {len(palettes)} palette entries")
    print("=" * 70)
    print()
    print("Study finding: fair/light skin -> cool blue hues preferred")
    print("               tanned/dark skin -> warm orange/red hues preferred")
    print()
    print("Note: Neutral/Olive entries are reported but not flagged either way —")
    print("they're expected to mix warm and cool, so a strict pass/fail doesn't apply.")
    print()

    flagged = []
    passed = []
    skipped = []

    # Sort keys for consistent, readable output order
    for key in sorted(palettes.keys()):
        undertone = key.split("|")[1] if "|" in key else ""
        colors = palettes[key]['recommended_colors']
        hues = [hex_to_hue(c) for c in colors]
        cool_count = sum(1 for h in hues if is_cool_hue(h))
        warm_count = sum(1 for h in hues if is_warm_hue(h))

        print(f"[{key}]")
        print(f"  Recommended colors: {colors}")
        print(f"  Cool-hue count: {cool_count} / {len(colors)}")
        print(f"  Warm-hue count: {warm_count} / {len(colors)}")

        if undertone == "Cool":
            if cool_count < warm_count:
                print(f"  ⚠️  FLAG: labeled Cool but has more warm-hue colors than cool ones")
                flagged.append(key)
            else:
                print(f"  ✅  Direction consistent with label")
                passed.append(key)
        elif undertone == "Warm":
            if warm_count < cool_count:
                print(f"  ⚠️  FLAG: labeled Warm but has more cool-hue colors than warm ones")
                flagged.append(key)
            else:
                print(f"  ✅  Direction consistent with label")
                passed.append(key)
        else:
            # Neutral / Olive — no strict pass/fail, just report the mix
            print(f"  ℹ️  {undertone} entry — mixed warm/cool expected, not flagged")
            skipped.append(key)
        print()

    print("=" * 70)
    print("SUMMARY")
    print(f"  Passed:  {len(passed)} / {len(passed) + len(flagged)} checkable entries")
    print(f"  Flagged: {len(flagged)}")
    if flagged:
        print(f"    -> {', '.join(flagged)}")
    print(f"  Not checked (Neutral/Olive): {len(skipped)}")
    print("=" * 70)
    print("NOTE: This only checks internal consistency (does 'Cool' actually")
    print("contain cool-hued colors) — it does NOT prove our thresholds match")
    print("real human preference. That still requires Phase 5 real-user testing.")
    print("=" * 70)


if __name__ == "__main__":
    check_palette_direction("data/palette_lookup.json")