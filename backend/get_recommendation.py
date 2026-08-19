"""
Full Pipeline: Photo -> Skin Analysis -> Palette Recommendation -> Clothing Match -> Visual Report
--------------------------------------------------------------------------------------------------
Runs the Phase 1 skin analyser, Phase 2 palette lookup (with contrast
filtering), and Phase 3 clothing catalog matching through the canonical
pipeline functions.

Usage:
    python3 get_recommendation.py ../samples/sample_friend.jpg
"""

import json
import sys
import os

from app.cv.skin_tone_analyzer import analyze_skin_tone
from app.cv.palette_lookup import get_color_palette_from_analysis
from app.cv.clothing_matcher import match_clothing


def run_pipeline(image_path: str) -> dict:
    """
    Run Phase 1 + Phase 2 + Phase 3 through the canonical fixed pipeline.
    Returns the combined result dict including recommended_clothing.
    """
    phase1 = analyze_skin_tone(image_path)
    palette_result = get_color_palette_from_analysis(phase1)
    if "error" not in palette_result:
        clothing = match_clothing(palette_result)
        palette_result["recommended_clothing"] = clothing
    return palette_result


def generate_html_report(image_path: str, result: dict, output_path: str) -> None:
    """Generate a colour-swatch + clothing-grid HTML report."""

    def swatch_html(colors: list, label: str) -> str:
        if not colors:
            return f"<h3>{label}</h3><p><em>None</em></p>"
        swatches = "".join(
            f'<div style="display:inline-block; text-align:center; margin:8px;">'
            f'<div style="width:80px; height:80px; background:{c}; border-radius:8px; '
            f'border:1px solid #ccc;"></div>'
            f'<div style="font-size:12px; margin-top:4px;">{c}</div></div>'
            for c in colors
        )
        return f"<h3>{label}</h3><div>{swatches}</div>"

    def clothing_grid_html(clothing_result: dict) -> str:
        items = clothing_result.get("matched_items", [])
        if not items:
            return "<p><em>No matching clothing items found for this palette.</em></p>"
        cards = ""
        for item in items:
            color = item.get("color_hex", "#ccc")
            name = item.get("name", "")
            category = item.get("category", "").capitalize()
            de_palette = item.get("min_palette_de", "")
            closest = item.get("closest_palette_color", "")
            skin_de = item.get("skin_de", "")
            cards += (
                f'<div style="display:inline-block;width:140px;vertical-align:top;'
                f'margin:8px;border:1px solid #e0e0e0;border-radius:10px;'
                f'padding:10px;box-shadow:0 2px 6px rgba(0,0,0,0.07);text-align:center;">'
                f'<div style="width:100%;height:80px;background:{color};border-radius:6px;'
                f'margin-bottom:8px;"></div>'
                f'<div style="font-size:13px;font-weight:600;margin-bottom:2px;">{name}</div>'
                f'<div style="font-size:11px;color:#888;">{category}</div>'
                f'<div style="font-size:11px;color:#555;margin-top:4px;">{color}</div>'
                f'<div style="font-size:10px;color:#aaa;margin-top:2px;">'
                f'Palette ΔE={de_palette}'
                f'<span style="display:inline-block;width:10px;height:10px;'
                f'background:{closest};border:1px solid #ccc;border-radius:2px;'
                f'vertical-align:middle;margin-left:4px;"></span>'
                f'</div>'
                f'<div style="font-size:10px;color:#aaa;">Skin ΔE={skin_de}</div>'
                f'</div>'
            )
        total = clothing_result.get("total_matched", len(items))
        header = (
            f"<h2>Matching Clothing Items</h2>"
            f"<p style='color:#555;font-size:13px;'>{len(items)} shown of {total} matches "
            f"(palette ΔE &lt; 15, skin contrast ΔE &ge; 25)</p>"
        )
        return header + f"<div>{cards}</div>"

    audit = result.get("audit", {})
    contrast_scores = audit.get("recommended_contrast_scores", {})
    removed_rec = audit.get("low_contrast_removed", [])
    removed_avoid = audit.get("near_white_removed_from_avoid", [])

    confidence_badge = ""
    if result.get("undertone_confidence") == "low":
        confidence_badge = (
            '<p style="color:#c0392b; background:#fdf2f2; padding:8px; border-radius:4px;">'
            "⚠ Undertone confidence is <b>LOW</b>. Warm lighting may have shifted the reading. "
            "Retake photo in natural daylight for a reliable result.</p>"
        )

    score_rows = ""
    for c, de in contrast_scores.items():
        score_rows += (
            f'<tr><td><span style="display:inline-block;width:20px;height:20px;'
            f'background:{c};border:1px solid #ccc;border-radius:3px;vertical-align:middle;"></span>'
            f" {c}</td><td>{de}</td></tr>"
        )
    score_table = ""
    if score_rows:
        score_table = (
            "<h3>Contrast Scores (delta-E vs skin)</h3>"
            "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;font-size:13px;'>"
            "<tr><th>Colour</th><th>delta-E (min 25)</th></tr>"
            + score_rows
            + "</table>"
        )

    removed_note = ""
    if removed_rec:
        removed_note += (
            f'<p style="color:#888;font-size:13px;">🚫 Removed from recommended (low contrast): '
            f"{', '.join(removed_rec)}</p>"
        )
    if removed_avoid:
        removed_note += (
            f'<p style="color:#888;font-size:13px;">✅ Removed from avoid list (near-white, fine for deep skin): '
            f"{', '.join(removed_avoid)}</p>"
        )

    clothing_html = ""
    if "recommended_clothing" in result:
        clothing_html = "<hr>" + clothing_grid_html(result["recommended_clothing"])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>rangroop — Color Recommendation</title></head>
<body style="font-family: sans-serif; max-width: 900px; margin: 40px auto; line-height:1.6;">
    <h1>Your Color Profile</h1>
    <p><b>Photo:</b> {os.path.basename(image_path)}</p>
    <p><b>Skin Type:</b> {result.get("skin_type")} &nbsp;|&nbsp;
       <b>Season:</b> {result.get("season", "—")} &nbsp;|&nbsp;
       <b>Depth:</b> {result.get("depth_bucket", "—")}</p>
    <p><b>Undertone:</b> {result.get("undertone")}
       (confidence: <b>{result.get("undertone_confidence", "—")}</b>,
       illuminant bias: {result.get("illuminant_bias", "—")})</p>
    {confidence_badge}
    <p style="color:#555; font-size:13px;">{result.get("confidence_notes", "")}</p>
    <hr>
    {swatch_html(result.get("recommended_colors", []), "Recommended Colors")}
    {swatch_html(result.get("avoid_colors", []), "Colors to Avoid")}
    <p style="margin-top:16px;">{result.get("explanation", "")}</p>
    {clothing_html}
    <hr>
    {score_table}
    {removed_note}
    <hr>
    <p style="color:#999; font-size:12px;">
        This is a suggestion based on colour theory, not a definitive rule.
        Lighting and camera quality can affect the analysis.
    </p>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 get_recommendation.py <path_to_photo>")
        sys.exit(1)

    image_path = sys.argv[1]
    print(f"Analyzing {image_path}...")

    # Run the full fixed pipeline
    result = run_pipeline(image_path)

    if "error" in result:
        print("Analysis failed:", result)
        sys.exit(1)

    # Print human-readable summary
    print(f"Skin Type : {result['skin_type']}  |  Undertone: {result['undertone']}"
          f"  (confidence: {result.get('undertone_confidence', '?')})")
    print(f"Season    : {result.get('season', '—')}  |  ITA: {result.get('ita_value')}")
    print(f"Illuminant bias: {result.get('illuminant_bias', '?')} (threshold 6.0)")
    print()
    print("Recommended colors:", result.get("recommended_colors"))
    print("Avoid colors      :", result.get("avoid_colors"))

    audit = result.get("audit", {})
    if audit.get("low_contrast_removed"):
        print("Removed (low contrast)       :", audit["low_contrast_removed"])
    if audit.get("near_white_removed_from_avoid"):
        print("Removed from avoid (near-white):", audit["near_white_removed_from_avoid"])
    if audit.get("recommended_contrast_scores"):
        print("\nContrast scores (delta-E vs skin):")
        for color, score in audit["recommended_contrast_scores"].items():
            flag = "✓" if score >= 25 else "⚠ FAIL"
            print(f"  {color}  dE={score}  {flag}")

    clothing = result.get("recommended_clothing", {})
    matched_items = clothing.get("matched_items", [])
    if matched_items:
        print(f"\nMatching clothing items ({len(matched_items)} shown, "
              f"{clothing.get('total_matched', len(matched_items))} total):")
        for item in matched_items:
            print(f"  [{item['category']:8s}] {item['name']:40s}  "
                  f"{item['color_hex']}  palette ΔE={item['min_palette_de']}  "
                  f"skin ΔE={item.get('skin_de', '—')}")
    rejected = clothing.get("skin_contrast_rejected", [])
    if rejected:
        print(f"\nSkin-contrast rejected ({len(rejected)} items):")
        for item in rejected:
            print(f"  {item['name']}  skin ΔE={item['skin_de']} (< 25)")

    output_name = os.path.splitext(os.path.basename(image_path))[0]
    output_path = f"../results_{output_name}.html"
    generate_html_report(image_path, result, output_path)
    print(f"\nVisual report saved to: {output_path}")