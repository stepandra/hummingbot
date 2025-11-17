from unittest import TestCase

from hummingbot.connector.derivative.vest_perpetual import vest_perpetual_constants as CONSTANTS


class VestPerpetualConstantsTests(TestCase):
    def test_exchange_name_defined(self):
        self.assertEqual("vest_perpetual", CONSTANTS.EXCHANGE_NAME)

    def test_default_domain_defined(self):
        self.assertEqual("vest_perpetual", CONSTANTS.DEFAULT_DOMAIN)

    def test_testnet_domain_defined(self):
        self.assertEqual("vest_perpetual_testnet", CONSTANTS.TESTNET_DOMAIN)

    def test_rest_urls_defined(self):
        self.assertEqual(
            "https://server-prod.hz.vestmarkets.com/v2",
            CONSTANTS.PERPETUAL_BASE_URL
        )
        self.assertEqual(
            "https://server-dev.hz.vestmarkets.com/v2",
            CONSTANTS.TESTNET_BASE_URL
        )

    def test_ws_urls_defined(self):
        self.assertEqual(
            "wss://ws-prod.hz.vestmarkets.com/ws-api",
            CONSTANTS.PERPETUAL_WS_URL
        )
        self.assertEqual(
            "wss://ws-dev.hz.vestmarkets.com/ws-api",
            CONSTANTS.TESTNET_WS_URL
        )

    def test_all_required_paths_defined(self):
        """Verify that all required API paths are defined."""
        required_paths = [
            "EXCHANGE_INFO_PATH",
            "DEPTH_PATH",
            "TICKER_LATEST_PATH",
            "TICKER_24HR_PATH",
            "FUNDING_HISTORY_PATH",
            "ACCOUNT_PATH",
            "ACCOUNT_NONCE_PATH",
            "ACCOUNT_LEVERAGE_PATH",
            "ORDERS_PATH",
            "ORDERS_CANCEL_PATH",
            "LP_PATH",
            "LP_QUERY_PATH",
            "TRANSFER_WITHDRAW_PATH",
            "TRANSFER_QUERY_PATH",
            "LISTEN_KEY_PATH",
        ]
        for path_name in required_paths:
            self.assertTrue(
                hasattr(CONSTANTS, path_name),
                f"{path_name} should be defined in constants"
            )
            path_value = getattr(CONSTANTS, path_name)
            self.assertIsInstance(path_value, str)
            self.assertTrue(path_value.startswith("/"), f"{path_name} should start with '/'")

    def test_ws_channels_defined(self):
        """Verify that WebSocket channel templates are defined."""
        self.assertIn("{symbol}", CONSTANTS.WS_ORDERBOOK_DEPTH_CHANNEL)
        self.assertIn("{symbol}", CONSTANTS.WS_TRADES_CHANNEL)
        self.assertIn("{symbol}", CONSTANTS.WS_KLINE_CHANNEL)
        self.assertIn("{interval}", CONSTANTS.WS_KLINE_CHANNEL)
        self.assertEqual("account_private", CONSTANTS.WS_ACCOUNT_PRIVATE_CHANNEL)

    def test_rate_limits_include_key_endpoints(self):
        """Verify that rate limits are defined for key endpoints."""
        limit_ids = [rl.limit_id for rl in CONSTANTS.RATE_LIMITS]

        required_limits = [
            CONSTANTS.EXCHANGE_INFO_PATH,
            CONSTANTS.DEPTH_PATH,
            CONSTANTS.ORDERS_PATH,
            CONSTANTS.ACCOUNT_PATH,
            CONSTANTS.LISTEN_KEY_PATH,
        ]

        for limit_id in required_limits:
            self.assertIn(
                limit_id,
                limit_ids,
                f"Rate limit for {limit_id} should be defined"
            )

    def test_order_state_mapping_defined(self):
        """Verify that order state mapping exists and contains expected states."""
        self.assertIn("NEW", CONSTANTS.ORDER_STATE)
        self.assertIn("FILLED", CONSTANTS.ORDER_STATE)
        self.assertIn("CANCELED", CONSTANTS.ORDER_STATE)
        self.assertIn("REJECTED", CONSTANTS.ORDER_STATE)
