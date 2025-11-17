from decimal import Decimal
from unittest import TestCase

from hummingbot.connector.derivative.vest_perpetual import vest_perpetual_utils as utils


class VestPerpetualUtilsTests(TestCase):
    def test_default_fees_structure(self):
        """Test that DEFAULT_FEES has the expected structure."""
        fees = utils.DEFAULT_FEES
        self.assertIsInstance(fees.maker_percent_fee_decimal, Decimal)
        self.assertIsInstance(fees.taker_percent_fee_decimal, Decimal)
        self.assertTrue(fees.buy_percent_fee_deducted_from_returns)

    def test_config_map_contains_expected_fields(self):
        """Test that VestPerpetualConfigMap has all required fields."""
        config_map = utils.VestPerpetualConfigMap.model_construct(
            vest_perpetual_api_key="test_api_key",
            vest_perpetual_signing_private_key="0xabc123",
            vest_perpetual_account_group=0
        )

        self.assertEqual("vest_perpetual", config_map.connector)
        self.assertEqual("test_api_key", config_map.vest_perpetual_api_key.get_secret_value())
        self.assertEqual("0xabc123", config_map.vest_perpetual_signing_private_key.get_secret_value())
        self.assertEqual(0, config_map.vest_perpetual_account_group)

    def test_convert_to_exchange_trading_pair_crypto(self):
        """Test conversion of crypto trading pairs to Vest format."""
        # BTC perpetual
        self.assertEqual("BTC-PERP", utils.convert_to_exchange_trading_pair("BTC-USDC"))
        self.assertEqual("BTC-PERP", utils.convert_to_exchange_trading_pair("BTC-USDT"))

        # ETH perpetual
        self.assertEqual("ETH-PERP", utils.convert_to_exchange_trading_pair("ETH-USDC"))

        # SOL perpetual
        self.assertEqual("SOL-PERP", utils.convert_to_exchange_trading_pair("SOL-USDC"))

    def test_convert_to_exchange_trading_pair_stock(self):
        """Test conversion of stock trading pairs to Vest format."""
        # Stock perpetuals should use BASE-USD-PERP format
        self.assertEqual("AAPL-USD-PERP", utils.convert_to_exchange_trading_pair("AAPL-USDC"))
        self.assertEqual("TSLA-USD-PERP", utils.convert_to_exchange_trading_pair("TSLA-USDC"))

    def test_convert_from_exchange_trading_pair_crypto(self):
        """Test conversion of Vest crypto symbols to Hummingbot format."""
        self.assertEqual("BTC-USDC", utils.convert_from_exchange_trading_pair("BTC-PERP"))
        self.assertEqual("ETH-USDC", utils.convert_from_exchange_trading_pair("ETH-PERP"))
        self.assertEqual("SOL-USDC", utils.convert_from_exchange_trading_pair("SOL-PERP"))

    def test_convert_from_exchange_trading_pair_stock(self):
        """Test conversion of Vest stock symbols to Hummingbot format."""
        self.assertEqual("AAPL-USDC", utils.convert_from_exchange_trading_pair("AAPL-USD-PERP"))
        self.assertEqual("TSLA-USDC", utils.convert_from_exchange_trading_pair("TSLA-USD-PERP"))

    def test_convert_roundtrip_crypto(self):
        """Test that conversion roundtrips correctly for crypto pairs."""
        hb_pair = "BTC-USDC"
        exchange_symbol = utils.convert_to_exchange_trading_pair(hb_pair)
        roundtrip = utils.convert_from_exchange_trading_pair(exchange_symbol)
        self.assertEqual(hb_pair, roundtrip)

    def test_convert_roundtrip_stock(self):
        """Test that conversion roundtrips correctly for stock pairs."""
        hb_pair = "AAPL-USDC"
        exchange_symbol = utils.convert_to_exchange_trading_pair(hb_pair)
        roundtrip = utils.convert_from_exchange_trading_pair(exchange_symbol)
        self.assertEqual(hb_pair, roundtrip)

    def test_convert_to_exchange_returns_unchanged_for_no_dash(self):
        """Test that symbols without dashes are returned unchanged."""
        symbol = "BTCPERP"
        self.assertEqual(symbol, utils.convert_to_exchange_trading_pair(symbol))

    def test_convert_from_exchange_returns_unchanged_for_non_perp(self):
        """Test that symbols without -PERP are returned unchanged."""
        symbol = "BTC-USDC"
        self.assertEqual(symbol, utils.convert_from_exchange_trading_pair(symbol))
