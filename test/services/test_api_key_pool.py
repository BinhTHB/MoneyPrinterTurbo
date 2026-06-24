import time
import unittest
from unittest.mock import patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestApiKeyPool(unittest.TestCase):
    def test_single_key_returns_same_key(self):
        from app.services.api_key_pool import ApiKeyPool

        pool = ApiKeyPool(["key1"])
        self.assertEqual(pool.get(), "key1")
        self.assertEqual(pool.get(), "key1")

    def test_round_robin_cycles_through_keys(self):
        from app.services.api_key_pool import ApiKeyPool

        pool = ApiKeyPool(["key1", "key2", "key3"])
        self.assertEqual(pool.get(), "key1")
        self.assertEqual(pool.get(), "key2")
        self.assertEqual(pool.get(), "key3")
        self.assertEqual(pool.get(), "key1")

    def test_mark_rate_limited_advances_to_next_key(self):
        from app.services.api_key_pool import ApiKeyPool

        pool = ApiKeyPool(["key1", "key2", "key3"])
        self.assertEqual(pool.get(), "key1")
        pool.mark_rate_limited("key1")
        self.assertEqual(pool.get(), "key2")

    def test_mark_rate_limited_all_keys_returns_none(self):
        from app.services.api_key_pool import ApiKeyPool

        pool = ApiKeyPool(["key1", "key2"])
        self.assertEqual(pool.get(), "key1")
        pool.mark_rate_limited("key1")
        pool.mark_rate_limited("key2")
        self.assertIsNone(pool.get())

    def test_cooldown_expires_allows_key_reuse(self):
        from app.services.api_key_pool import ApiKeyPool

        pool = ApiKeyPool(["key1", "key2"], cooldown_seconds=0.1)
        self.assertEqual(pool.get(), "key1")
        pool.mark_rate_limited("key1")
        self.assertEqual(pool.get(), "key2")
        pool.mark_rate_limited("key2")
        self.assertIsNone(pool.get())
        time.sleep(0.15)
        self.assertEqual(pool.get(), "key1")

    def test_from_config_returns_pool_or_none(self):
        from app.services.api_key_pool import ApiKeyPool

        with patch.dict("app.config.config.app", {"gemini_api_keys": ["k1", "k2"], "gemini_api_key": ""}):
            pool = ApiKeyPool.from_config("gemini")
            self.assertIsNotNone(pool)
            self.assertEqual(pool.get(), "k1")

        with patch.dict("app.config.config.app", {"gemini_api_keys": [], "gemini_api_key": ""}, clear=False):
            pool = ApiKeyPool.from_config("gemini")
            self.assertIsNone(pool)

    def test_from_config_fallback_to_single_key(self):
        from app.services.api_key_pool import ApiKeyPool

        with patch.dict("app.config.config.app", {"gemini_api_key": "single_key"}):
            pool = ApiKeyPool.from_config("gemini")
            self.assertIsNotNone(pool)
            self.assertEqual(pool.get(), "single_key")

    def test_is_rate_limit_error_detects_common_patterns(self):
        from app.services.api_key_pool import is_rate_limit_error

        self.assertTrue(is_rate_limit_error(Exception("429 You exceeded your current quota")))
        self.assertTrue(is_rate_limit_error(Exception("RESOURCE_EXHAUSTED")))
        self.assertTrue(is_rate_limit_error(Exception("rate_limit_exceeded")))
        self.assertTrue(is_rate_limit_error(Exception("insufficient_quota")))
        self.assertFalse(is_rate_limit_error(Exception("network timeout")))
        self.assertFalse(is_rate_limit_error(Exception("invalid api key")))


if __name__ == "__main__":
    unittest.main()
