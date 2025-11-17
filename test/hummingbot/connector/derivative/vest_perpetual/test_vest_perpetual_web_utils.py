from unittest import TestCase
from urllib.parse import parse_qs, urlparse

from hummingbot.connector.derivative.vest_perpetual import vest_perpetual_constants as CONSTANTS
from hummingbot.connector.derivative.vest_perpetual import vest_perpetual_web_utils as web_utils


class VestPerpetualWebUtilsTests(TestCase):
    def test_public_rest_url_builds_correctly(self):
        """Test that public REST URLs are built correctly for default domain."""
        url = web_utils.public_rest_url(CONSTANTS.EXCHANGE_INFO_PATH)
        expected = "https://server-prod.hz.vestmarkets.com/v2/exchangeInfo"
        self.assertEqual(expected, url)

    def test_public_rest_url_builds_correctly_for_testnet(self):
        """Test that public REST URLs are built correctly for testnet domain."""
        url = web_utils.public_rest_url(CONSTANTS.EXCHANGE_INFO_PATH, domain=CONSTANTS.TESTNET_DOMAIN)
        expected = "https://server-dev.hz.vestmarkets.com/v2/exchangeInfo"
        self.assertEqual(expected, url)

    def test_private_rest_url_builds_correctly(self):
        """Test that private REST URLs are built correctly."""
        url = web_utils.private_rest_url(CONSTANTS.ORDERS_PATH)
        expected = "https://server-prod.hz.vestmarkets.com/v2/orders"
        self.assertEqual(expected, url)

    def test_public_ws_url_contains_version_and_websocketserver_params(self):
        """Test that public WebSocket URLs contain required query parameters."""
        account_group = 0
        url = web_utils.public_ws_url(CONSTANTS.DEFAULT_DOMAIN, account_group)

        # Parse URL
        parsed = urlparse(url)
        self.assertEqual("wss", parsed.scheme)
        self.assertEqual("ws-prod.hz.vestmarkets.com", parsed.netloc)
        self.assertEqual("/ws-api", parsed.path)

        # Parse query parameters
        query_params = parse_qs(parsed.query)
        self.assertIn("version", query_params)
        self.assertEqual(["1.0"], query_params["version"])
        self.assertIn("websocketserver", query_params)
        self.assertEqual([f"restserver{account_group}"], query_params["websocketserver"])

    def test_public_ws_url_testnet(self):
        """Test that testnet WebSocket URL is built correctly."""
        url = web_utils.public_ws_url(CONSTANTS.TESTNET_DOMAIN, account_group=0)

        parsed = urlparse(url)
        self.assertEqual("ws-dev.hz.vestmarkets.com", parsed.netloc)

    def test_private_ws_url_contains_listen_key(self):
        """Test that private WebSocket URLs contain listenKey parameter."""
        listen_key = "test_listen_key_abc123"
        account_group = 0
        url = web_utils.private_ws_url(listen_key, CONSTANTS.DEFAULT_DOMAIN, account_group)

        # Parse URL
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        # Check that all required parameters are present
        self.assertIn("version", query_params)
        self.assertEqual(["1.0"], query_params["version"])
        self.assertIn("websocketserver", query_params)
        self.assertEqual([f"restserver{account_group}"], query_params["websocketserver"])
        self.assertIn("listenKey", query_params)
        self.assertEqual([listen_key], query_params["listenKey"])

    def test_private_ws_url_with_non_zero_account_group(self):
        """Test that account_group parameter is correctly included."""
        listen_key = "test_key"
        account_group = 5
        url = web_utils.private_ws_url(listen_key, CONSTANTS.DEFAULT_DOMAIN, account_group)

        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        self.assertEqual([f"restserver{account_group}"], query_params["websocketserver"])

    def test_is_exchange_information_valid_returns_true_for_trading_status(self):
        """Test that is_exchange_information_valid returns True for TRADING status."""
        exchange_info = {"status": "TRADING", "symbol": "BTC-PERP"}
        self.assertTrue(web_utils.is_exchange_information_valid(exchange_info))

    def test_is_exchange_information_valid_returns_false_for_non_trading_status(self):
        """Test that is_exchange_information_valid returns False for non-TRADING status."""
        exchange_info = {"status": "HALTED", "symbol": "BTC-PERP"}
        self.assertFalse(web_utils.is_exchange_information_valid(exchange_info))

    def test_is_exchange_information_valid_returns_false_for_missing_status(self):
        """Test that is_exchange_information_valid returns False when status is missing."""
        exchange_info = {"symbol": "BTC-PERP"}
        self.assertFalse(web_utils.is_exchange_information_valid(exchange_info))

    def test_create_throttler_returns_throttler_with_rate_limits(self):
        """Test that create_throttler returns a properly configured throttler."""
        throttler = web_utils.create_throttler()
        self.assertIsNotNone(throttler)
        # The throttler should have rate limits defined
        self.assertTrue(len(throttler._rate_limits) > 0)
