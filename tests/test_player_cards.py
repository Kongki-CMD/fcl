import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from concurrent.futures import ThreadPoolExecutor

from backend import player_cards

FIXTURE = Path(__file__).parent / "fixtures" / "official-player-card.html"


class OfficialCardTests(unittest.TestCase):
    def setUp(self):
        player_cards._cache.clear()

    def test_current_datacenter_selects_portrait_not_background(self):
        card = player_cards.parse_official_card(FIXTURE.read_text(), 844273018)
        self.assertTrue(card["background_url"].endswith("/card/25TOTS.png"))
        self.assertTrue(card["portrait_url"].endswith("/playersActionHigh/p844273018_25.png"))
        self.assertEqual(card["season_class"], "_25TOTS")
        self.assertEqual(card["player_name"], "안드레이 산투스")
        self.assertEqual(card["position"], "CM")
        self.assertNotIn("?", card["portrait_url"])

    def test_legacy_datacenter_card(self):
        html = (Path(__file__).parents[1] / "backend/player_price_debug.html").read_text()
        card = player_cards.parse_official_card(html, 844273018)
        self.assertIn("playersActionHigh", card["portrait_url"])
        self.assertTrue(card["background_url"].endswith("/25TOTS.png"))

    def test_missing_or_untrusted_assets_rejected(self):
        with self.assertRaises(ValueError):
            player_cards.parse_official_card("<p>Maintenance</p>", 844273018)
        for value in ["javascript:alert(1)", "https://evil.example/card.png", "http://ssl.nexon.com/card.png"]:
            self.assertEqual(player_cards.official_asset_url(value), "")

    def test_concurrent_requests_share_one_official_fetch(self):
        response = Mock(text=FIXTURE.read_text())
        with patch.object(player_cards.httpx, "get", return_value=response) as get:
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(player_cards.get_official_card, [844273018] * 4))
            self.assertEqual(get.call_count, 1)
            self.assertTrue(all(result == results[0] for result in results))

    def test_failure_is_not_cached(self):
        with patch.object(player_cards.httpx, "get", return_value=Mock(text="maintenance")):
            with self.assertRaises(ValueError):
                player_cards.get_official_card(844273018)
        self.assertNotIn(844273018, player_cards._cache)


if __name__ == "__main__":
    unittest.main()
