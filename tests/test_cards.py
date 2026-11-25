import unittest
import xml.etree.ElementTree as ET

from tools import cards


class ProfileCardTests(unittest.TestCase):
    def test_transcript_has_approved_content_and_no_private_or_unwanted_metrics(self):
        for name, theme in cards.THEMES.items():
            with self.subTest(theme=name):
                width, height, body = cards.transcript(theme, 3682)
                root = ET.fromstring(cards.svg(width, height, body, theme["bg"]))
                text = " ".join((node.text or "") for node in root.iter()
                                 if node.tag.endswith("text") or node.tag.endswith("tspan"))
                self.assertIn("data engineer", text)
                self.assertIn("tech lead @ retize", text)
                self.assertIn("airflow · dbt · bigquery · k8s · python", text)
                self.assertIn("cadumagalhaes.dev", text)
                self.assertIn("3,682", text)
                self.assertNotIn("contact@", text)
                self.assertNotIn("followers", text)
                self.assertNotIn("repositories", text)
                self.assertEqual(width, 396)
                self.assertLessEqual(width, 400)

    def test_cube_initials_are_sticker_polygons_not_overlaid_text(self):
        theme = cards.THEMES["dark"]
        body, _, _ = cards.cube(26, 54, 122, theme["cube"])
        root = ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{body}</svg>')
        polygons = list(root.iter("{http://www.w3.org/2000/svg}polygon"))
        accent_stickers = [p for p in polygons if p.attrib["fill"] == theme["cube"]["accent"]]
        texts = list(root.iter("{http://www.w3.org/2000/svg}text"))
        self.assertEqual(len(polygons), 27)
        self.assertEqual(len(accent_stickers), 14)  # 7-sticker C + 7-sticker M
        self.assertEqual(texts, [])

    def test_fallback_value_matches_generated_svg(self):
        _, _, body = cards.transcript(cards.THEMES["dark"], cards.FALLBACK_CONTRIBUTIONS)
        self.assertIn("3,682", body)


if __name__ == "__main__":
    unittest.main()
