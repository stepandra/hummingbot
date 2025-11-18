import asyncio
import sys
import types
from decimal import Decimal
from enum import Enum

import pytest
from bidict import bidict

if "hummingbot.core.data_type.order_book" not in sys.modules:
    order_book_module = types.ModuleType("hummingbot.core.data_type.order_book")

    class _StubOrderBook:
        def __init__(self):
            self.snapshot = ({}, {})
            self.last_applied_trade = 0
            self.last_trade_price_rest_updated = 0

        def apply_snapshot(self, bids, asks, update_id):
            pass

        def apply_diffs(self, bids, asks, update_id):
            pass

        def apply_trade(self, trade_type, price, amount):
            pass

    order_book_module.OrderBook = _StubOrderBook
    sys.modules["hummingbot.core.data_type.order_book"] = order_book_module

if "hummingbot.core.data_type.limit_order" not in sys.modules:
    limit_order_module = types.ModuleType("hummingbot.core.data_type.limit_order")

    class _StubLimitOrder:
        def __init__(self, *args, **kwargs):
            self.price = kwargs.get("price")
            self.quantity = kwargs.get("quantity")

    limit_order_module.LimitOrder = _StubLimitOrder
    sys.modules["hummingbot.core.data_type.limit_order"] = limit_order_module

if "hummingbot.connector.exchange_base" not in sys.modules:
    exchange_base_module = types.ModuleType("hummingbot.connector.exchange_base")

    class _StubExchangeBase:
        def __init__(self, balance_asset_limit=None):
            self._balance_asset_limit = balance_asset_limit
            self._last_timestamp = 0

        def _set_current_timestamp(self, timestamp: float):
            self._last_timestamp = timestamp

        def current_timestamp(self):
            return self._last_timestamp

        def _set_order_book_tracker(self, order_book_tracker):
            self._order_book_tracker = order_book_tracker

    exchange_base_module.ExchangeBase = _StubExchangeBase
    sys.modules["hummingbot.connector.exchange_base"] = exchange_base_module

if "hummingbot.connector.trading_rule" not in sys.modules:
    trading_rule_module = types.ModuleType("hummingbot.connector.trading_rule")

    class TradingRule:
        def __init__(
            self,
            trading_pair: str,
            min_order_size: Decimal = Decimal("0"),
            max_order_size: Decimal = Decimal("0"),
            min_price_increment: Decimal = Decimal("0"),
            min_base_amount_increment: Decimal = Decimal("0"),
            min_quote_amount_increment: Decimal = Decimal("0"),
            min_notional_size: Decimal = Decimal("0"),
            max_price_significant_digits: Decimal = Decimal("0"),
            supports_limit_orders: bool = True,
            supports_market_orders: bool = True,
            buy_order_collateral_token: str = "",
            sell_order_collateral_token: str = "",
        ):
            self.trading_pair = trading_pair
            self.min_order_size = min_order_size
            self.max_order_size = max_order_size
            self.min_price_increment = min_price_increment
            self.min_base_amount_increment = min_base_amount_increment
            self.min_quote_amount_increment = min_quote_amount_increment
            self.min_notional_size = min_notional_size
            self.max_price_significant_digits = max_price_significant_digits
            self.supports_limit_orders = supports_limit_orders
            self.supports_market_orders = supports_market_orders
            self.buy_order_collateral_token = buy_order_collateral_token
            self.sell_order_collateral_token = sell_order_collateral_token

    trading_rule_module.TradingRule = TradingRule
    sys.modules["hummingbot.connector.trading_rule"] = trading_rule_module

if "hummingbot.core.network_iterator" not in sys.modules:
    network_module = types.ModuleType("hummingbot.core.network_iterator")

    class NetworkStatus(Enum):
        NOT_CONNECTED = 0
        CONNECTED = 1

    network_module.NetworkStatus = NetworkStatus
    sys.modules["hummingbot.core.network_iterator"] = network_module

from hummingbot.connector.derivative.position import Position
from hummingbot.connector.derivative.vest_perpetual.vest_perpetual_derivative import VestPerpetualDerivative
from hummingbot.connector.derivative.vest_perpetual.vest_perpetual_utils import DEFAULT_FEES
from hummingbot.connector.perpetual_trading import PerpetualTrading
from hummingbot.core.data_type.common import PositionMode, PositionSide


@pytest.fixture
def connector():
    instance = VestPerpetualDerivative.__new__(VestPerpetualDerivative)
    instance._trading_pairs = ["BTC-PERP"]
    instance._trading_rules = {}
    instance._trading_pair_symbol_map = bidict()
    instance._trading_fees = {}
    instance._position_mode = PositionMode.ONEWAY
    instance._trading_required = True
    instance._perpetual_trading = PerpetualTrading(instance._trading_pairs)
    return instance


@pytest.fixture
def sample_exchange_info():
    return {
        "symbols": [
            {
                "symbol": "BTC-PERP",
                "status": "TRADING",
                "quoteAsset": "USDC",
                "minQty": "0.001",
                "maxQty": "5",
                "tickSize": "0.5",
                "stepSize": "0.001",
                "minNotional": "10",
                "orderTypes": ["LIMIT", "MARKET"],
            },
            {
                "symbol": "ETH-PERP",
                "status": "HALT",
            },
        ]
    }


def test_format_trading_rules_returns_active_pairs(connector, sample_exchange_info):
    rules = asyncio.run(connector._format_trading_rules(sample_exchange_info))

    assert len(rules) == 1
    rule = rules[0]
    assert rule.trading_pair == "BTC-PERP"
    assert rule.min_order_size == Decimal("0.001")
    assert rule.min_price_increment == Decimal("0.5")
    assert rule.min_quote_amount_increment == Decimal("0.0005")
    assert rule.buy_order_collateral_token == "USDC"


def test_initialize_trading_pair_symbol_map(connector, sample_exchange_info):
    connector._initialize_trading_pair_symbols_from_exchange_info(sample_exchange_info)

    assert connector._trading_pair_symbol_map["BTC-PERP"] == "BTC-PERP"
    assert "ETH-PERP" not in connector._trading_pair_symbol_map


def test_trading_pair_position_mode_validation(connector):
    success, message = asyncio.run(connector._trading_pair_position_mode_set(PositionMode.ONEWAY, "BTC-PERP"))
    assert success
    assert message == ""

    success, message = asyncio.run(connector._trading_pair_position_mode_set(PositionMode.HEDGE, "BTC-PERP"))
    assert not success
    assert "oneway" in message.lower()


def test_set_trading_pair_leverage_validation(connector):
    success, message = asyncio.run(connector._set_trading_pair_leverage("BTC-PERP", 5))
    assert success
    assert message == ""

    success, message = asyncio.run(connector._set_trading_pair_leverage("BTC-PERP", 0))
    assert not success
    assert "leverage" in message.lower()


def test_update_trading_fees_assigns_default_schema(connector):
    asyncio.run(connector._update_trading_fees())

    fee_schema = connector._trading_fees["BTC-PERP"]
    assert fee_schema.maker_percent_fee_decimal == DEFAULT_FEES.maker_percent_fee_decimal
    assert fee_schema.taker_percent_fee_decimal == DEFAULT_FEES.taker_percent_fee_decimal


def test_update_positions_clears_cached_positions(connector):
    key = connector._perpetual_trading.position_key("BTC-PERP", PositionSide.LONG)
    connector._perpetual_trading.set_position(
        key,
        Position(
            trading_pair="BTC-PERP",
            position_side=PositionSide.LONG,
            unrealized_pnl=Decimal("0"),
            entry_price=Decimal("20000"),
            amount=Decimal("1"),
            leverage=Decimal("5"),
        ),
    )

    asyncio.run(connector._update_positions())

    assert connector.account_positions == {}


def test_fetch_last_fee_payment_returns_placeholder(connector):
    timestamp, rate, payment = asyncio.run(connector._fetch_last_fee_payment("BTC-PERP"))

    assert timestamp == 0
    assert rate == Decimal("-1")
    assert payment == Decimal("-1")
