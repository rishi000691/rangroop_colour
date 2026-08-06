"""
Unit Tests for Palette Lookup Module (Phase 2)
===============================================

Tests coverage:
1. ITA-to-depth bucketing (three-tier collapse from six ITA categories).
2. Season mapping for all 12 combinations (4 undertones × 3 depths).
3. Full palette output schema validation (required keys, hex format, list lengths).
4. Error handling for unrecognized undertone and missing Phase 1 fields.
5. Integration: get_color_palette_from_analysis with mock Phase 1 output.
"""

import unittest
import re

from backend.app.cv.palette_lookup import (
    get_color_palette,
    get_color_palette_from_analysis,
    get_season,
    _ita_to_depth_bucket,
    SEASON_PALETTES,
    SEASON_MAP,
)


HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class TestDepthBucketing(unittest.TestCase):
    """Verify ITA value → depth bucket mapping."""

    def test_very_light_maps_to_light(self):
        self.assertEqual(_ita_to_depth_bucket(60.0), "light")

    def test_light_maps_to_light(self):
        self.assertEqual(_ita_to_depth_bucket(45.0), "light")

    def test_boundary_41_is_light(self):
        # ITA > 41 → light
        self.assertEqual(_ita_to_depth_bucket(41.01), "light")

    def test_boundary_41_exact_is_medium(self):
        # ITA = 41.0 → medium (41.0 is NOT > 41.0)
        self.assertEqual(_ita_to_depth_bucket(41.0), "medium")

    def test_intermediate_maps_to_medium(self):
        self.assertEqual(_ita_to_depth_bucket(35.0), "medium")

    def test_tan_maps_to_medium(self):
        self.assertEqual(_ita_to_depth_bucket(20.0), "medium")

    def test_boundary_10_exact_is_deep(self):
        # ITA = 10.0 → deep (10.0 is NOT > 10.0)
        self.assertEqual(_ita_to_depth_bucket(10.0), "deep")

    def test_dark_maps_to_deep(self):
        self.assertEqual(_ita_to_depth_bucket(0.0), "deep")

    def test_very_dark_maps_to_deep(self):
        self.assertEqual(_ita_to_depth_bucket(-35.0), "deep")


class TestSeasonMapping(unittest.TestCase):
    """Verify all 12 undertone × depth → season mappings."""

    def test_warm_light(self):
        self.assertEqual(get_season("Warm", 50.0), "Light Spring")

    def test_warm_medium(self):
        self.assertEqual(get_season("Warm", 30.0), "True Spring")

    def test_warm_deep(self):
        self.assertEqual(get_season("Warm", -5.0), "Deep Autumn")

    def test_cool_light(self):
        self.assertEqual(get_season("Cool", 50.0), "Light Summer")

    def test_cool_medium(self):
        self.assertEqual(get_season("Cool", 30.0), "True Summer")

    def test_cool_deep(self):
        self.assertEqual(get_season("Cool", -5.0), "Deep Winter")

    def test_neutral_light(self):
        self.assertEqual(get_season("Neutral", 50.0), "Bright Spring")

    def test_neutral_medium(self):
        self.assertEqual(get_season("Neutral", 30.0), "Soft Summer")

    def test_neutral_deep(self):
        self.assertEqual(get_season("Neutral", -5.0), "Bright Winter")

    def test_olive_light(self):
        self.assertEqual(get_season("Olive", 50.0), "Soft Autumn")

    def test_olive_medium(self):
        self.assertEqual(get_season("Olive", 30.0), "True Autumn")

    def test_olive_deep(self):
        self.assertEqual(get_season("Olive", -5.0), "True Winter")

    def test_case_insensitive_undertone(self):
        self.assertEqual(get_season("warm", 50.0), "Light Spring")
        self.assertEqual(get_season("COOL", 30.0), "True Summer")

    def test_invalid_undertone_raises(self):
        with self.assertRaises(ValueError):
            get_season("Unknown", 50.0)


class TestPaletteDataIntegrity(unittest.TestCase):
    """Validate structure and content of all 12 season palette entries."""

    def test_all_12_seasons_present(self):
        # Collect all season names from the mapping
        all_seasons = set()
        for depths in SEASON_MAP.values():
            all_seasons.update(depths.values())
        self.assertEqual(len(all_seasons), 12)

        # Every mapped season must have palette data
        for season_name in all_seasons:
            self.assertIn(season_name, SEASON_PALETTES, f"Missing palette for {season_name}")

    def test_recommended_colors_count(self):
        for season, palette in SEASON_PALETTES.items():
            count = len(palette["recommended_colors"])
            self.assertGreaterEqual(count, 6, f"{season}: expected ≥6 recommended, got {count}")
            self.assertLessEqual(count, 8, f"{season}: expected ≤8 recommended, got {count}")

    def test_avoid_colors_count(self):
        for season, palette in SEASON_PALETTES.items():
            count = len(palette["avoid_colors"])
            self.assertGreaterEqual(count, 2, f"{season}: expected ≥2 avoid, got {count}")
            self.assertLessEqual(count, 3, f"{season}: expected ≤3 avoid, got {count}")

    def test_all_colors_are_valid_hex(self):
        for season, palette in SEASON_PALETTES.items():
            for hex_code in palette["recommended_colors"] + palette["avoid_colors"]:
                self.assertRegex(
                    hex_code, HEX_PATTERN,
                    f"{season}: invalid hex code '{hex_code}'"
                )

    def test_explanations_are_nonempty(self):
        for season, palette in SEASON_PALETTES.items():
            self.assertIsInstance(palette["explanation"], str)
            self.assertGreater(len(palette["explanation"]), 50, f"{season}: explanation too short")


class TestGetColorPalette(unittest.TestCase):
    """Test the main get_color_palette function output schema."""

    def test_output_has_required_keys(self):
        result = get_color_palette("Warm", 45.0)
        required_keys = {
            "season", "depth_bucket", "skin_type", "undertone",
            "recommended_colors", "avoid_colors", "explanation"
        }
        self.assertEqual(required_keys, set(result.keys()))

    def test_season_field_matches(self):
        result = get_color_palette("Cool", -10.0)
        self.assertEqual(result["season"], "Deep Winter")

    def test_depth_bucket_field(self):
        result = get_color_palette("Warm", 45.0)
        self.assertEqual(result["depth_bucket"], "light")

    def test_skin_type_field(self):
        result = get_color_palette("Warm", 45.0)
        self.assertEqual(result["skin_type"], "Light")

    def test_undertone_echoed(self):
        result = get_color_palette("Olive", 30.0)
        self.assertEqual(result["undertone"], "Olive")


class TestGetColorPaletteFromAnalysis(unittest.TestCase):
    """Test the Phase 1 integration wrapper."""

    def test_valid_phase1_output(self):
        phase1 = {
            "success": True,
            "dominant_lab": [65.0, 12.5, 18.3],
            "ita_value": 38.5,
            "skin_type": "Intermediate",
            "hue_angle": 55.6,
            "undertone": "Neutral",
            "confidence_notes": "Analyzed 5000 pixels..."
        }
        result = get_color_palette_from_analysis(phase1)

        # Should have Phase 1 fields merged in
        self.assertEqual(result["dominant_lab"], [65.0, 12.5, 18.3])
        self.assertEqual(result["hue_angle"], 55.6)
        self.assertEqual(result["confidence_notes"], "Analyzed 5000 pixels...")

        # Plus Phase 2 palette fields
        self.assertEqual(result["season"], "Soft Summer")
        self.assertIn("recommended_colors", result)
        self.assertIn("avoid_colors", result)
        self.assertIn("explanation", result)

    def test_phase1_error_passthrough(self):
        phase1_error = {
            "error": "NO_FACE_DETECTED",
            "message": "No face detected."
        }
        result = get_color_palette_from_analysis(phase1_error)
        self.assertEqual(result["error"], "NO_FACE_DETECTED")
        self.assertNotIn("season", result)

    def test_missing_undertone_key(self):
        bad_phase1 = {"ita_value": 45.0}
        result = get_color_palette_from_analysis(bad_phase1)
        self.assertEqual(result["error"], "MISSING_PHASE1_FIELDS")

    def test_missing_ita_key(self):
        bad_phase1 = {"undertone": "Warm"}
        result = get_color_palette_from_analysis(bad_phase1)
        self.assertEqual(result["error"], "MISSING_PHASE1_FIELDS")


if __name__ == "__main__":
    unittest.main()
