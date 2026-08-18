"""
Full Pipeline: Photo -> Skin Analysis -> Palette Recommendation -> Visual Report
----------------------------------------------------------------------------------
Runs skin_tone_analyzer.py on a photo, looks up the matching palette in
palette_lookup.json, and generates a simple HTML file with actual color
swatches so you can show real people the result (not just hex codes).

Usage:
    python get_recommendation.py ../samples/friend1.jpg
"""

import subprocess
import json
import sys
import os

def run_skin_analysis(image_path):
    """Run the Phase 1 analyzer and capture its JSON output."""
    result = subprocess.run(
    [sys.executable, "app/cv/skin_tone_analyzer.py", image_path],
    capture_output=True, text=True
)

    # Extract JSON block from stdout (there's log noise mixed in)
    output = result.stdout
    start = output.find("{")
    end = output.rfind("}") + 1
    if start == -1 or end == 0:
        print("Could not find JSON output. Raw output was:")
        print(output)
        print(result.stderr)
        return None
    try:
        return json.loads(output[start:end])
    except json.JSONDecodeError:
        print("Failed to parse JSON. Raw output was:")
        print(output[start:end])
        return None

def get_palette(skin_type, undertone, palette_path="data/palette_lookup.json"):
    with open(palette_path, "r") as f:
        data = json.load(f)
    key = f"{skin_type}|{undertone}"
    return data["palettes"].get(key)

def generate_html_report(image_path, analysis, palette, output_path):
    def swatch_html(colors, label):
        swatches = "".join(
            f'<div style="display:inline-block; text-align:center; margin:8px;">'
            f'<div style="width:80px; height:80px; background:{c}; border-radius:8px; '
            f'border:1px solid #ccc;"></div>'
            f'<div style="font-size:12px; margin-top:4px;">{c}</div></div>'
            for c in colors
        )
        return f'<h3>{label}</h3><div>{swatches}</div>'

    html = f"""
    <html>
    <head><title>rangroop — Color Recommendation</title></head>
    <body style="font-family: sans-serif; max-width: 700px; margin: 40px auto;">
        <h1>Your Color Profile</h1>
        <p><b>Photo:</b> {os.path.basename(image_path)}</p>
        <p><b>Skin Type:</b> {analysis.get('skin_type')}</p>
        <p><b>Undertone:</b> {analysis.get('undertone')}</p>
        <p style="color:#666; font-size:14px;">{analysis.get('confidence_notes', '')}</p>
        <hr>
        {swatch_html(palette['recommended_colors'], 'Recommended Colors') if palette else '<p>No palette found for this combination.</p>'}
        {swatch_html(palette['avoid_colors'], 'Colors to Avoid') if palette else ''}
        <p style="margin-top:20px;">{palette['explanation'] if palette else ''}</p>
        <hr>
        <p style="color:#999; font-size:12px;">
            This is a suggestion based on color theory, not a definitive rule.
            Lighting and camera quality can affect the analysis.
        </p>
    </body>
    </html>
    """
    with open(output_path, "w") as f:
        f.write(html)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_recommendation.py <path_to_photo>")
        sys.exit(1)

    image_path = sys.argv[1]
    print(f"Analyzing {image_path}...")

    analysis = run_skin_analysis(image_path)
    if not analysis or not analysis.get("success"):
        print("Analysis failed:", analysis)
        sys.exit(1)

    skin_type = analysis["skin_type"]
    undertone = analysis["undertone"]
    print(f"Skin Type: {skin_type} | Undertone: {undertone}")

    palette = get_palette(skin_type, undertone)
    if not palette:
        print(f"No palette entry found for '{skin_type}|{undertone}'")
        sys.exit(1)

    print("Recommended colors:", palette["recommended_colors"])
    print("Avoid colors:", palette["avoid_colors"])

    output_name = os.path.splitext(os.path.basename(image_path))[0]
    output_path = f"../results_{output_name}.html"
    generate_html_report(image_path, analysis, palette, output_path)
    print(f"\nVisual report saved to: {output_path}")
    print("Open this file in your browser to show your friend the actual colors.")