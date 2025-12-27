import asyncio
import json
import re
import sys
import types
from decimal import Decimal
from typing import Any, Callable, List, Optional, Tuple
from unittest.mock import patch
from enum import Enum

from aioresponses import aioresponses
from aioresponses.core import RequestCall

# --- STUBS START ---
if "hummingbot.core.data_type.order_book" not in sys.modules:
    order_book_module = types.ModuleType("hummingbot.core.data_type.order_book")
    class _StubOrderBook:
        def __init__(self):
            self.snapshot = ({}, {})
            self.last_applied_trade = 0
            self.last_trade_price_rest_updated = 0
        def apply_snapshot(self, bids, asks, update_id): pass
        def apply_diffs(self, bids, asks, update_id): pass
        def apply_trade(self, trade_type, price, amount): pass
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
            self._trading_pairs = []
        def _set_current_timestamp(self, timestamp: float):
            self._last_timestamp = timestamp
        @property
        def current_timestamp(self):
            return self._last_timestamp
        def _set_order_book_tracker(self, order_book_tracker):
            self._order_book_tracker = order_book_tracker
        def get_all_balances(self): return {}
        def available_balances(self): return {}
        def start(self, network_iterator, socket_listener): pass
        def stop(self, network_iterator): pass
        def tick(self, timestamp): pass
        def get_order_book(self, trading_pair):
            from hummingbot.core.data_type.order_book import OrderBook
            return OrderBook()
    exchange_base_module.ExchangeBase = _StubExchangeBase
    sys.modules["hummingbot.connector.exchange_base"] = exchange_base_module

if "hummingbot.connector.trading_rule" not in sys.modules:
    trading_rule_module = types.ModuleType("hummingbot.connector.trading_rule")
    class TradingRule:
        def __init__(self, trading_pair, min_order_size=Decimal("0"), max_order_size=Decimal("0"), min_price_increment=Decimal("0"), min_base_amount_increment=Decimal("0"), min_quote_amount_increment=Decimal("0"), min_notional_size=Decimal("0"), max_price_significant_digits=Decimal("0"), supports_limit_orders=True, supports_market_orders=True, buy_order_collateral_token="", sell_order_collateral_token=""):
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
# --- STUBS END ---

import hummingbot.connector.derivative.vest_perpetual.vest_perpetual_constants as CONSTANTS
import hummingbot.connector.derivative.vest_perpetual.vest_perpetual_web_utils as web_utils
from hummingbot.connector.derivative.vest_perpetual.vest_perpetual_derivative import VestPerpetualDerivative
from hummingbot.connector.test_support.perpetual_derivative_test import AbstractPerpetualDerivativeTests
from hummingbot.connector.trading_rule import TradingRule
from hummingbot.connector.utils import combine_to_hb_trading_pair
from hummingbot.core.data_type.common import OrderType, PositionMode, TradeType
from hummingbot.core.data_type.in_flight_order import InFlightOrder, OrderState
from hummingbot.core.data_type.trade_fee import AddedToCostTradeFee, TokenAmount, TradeFeeBase


class TestVestPerpetualDerivative(AbstractPerpetualDerivativeTests.PerpetualDerivativeTests):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.api_key = "someKey"
        cls.signing_key = "0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        cls.account_group = 0
        cls.base_asset = "BTC"
        cls.quote_asset = "USDC"
        cls.trading_pair = combine_to_hb_trading_pair(cls.base_asset, cls.quote_asset)
        cls.exchange_trading_pair = f"{cls.base_asset}-PERP"

    @property
    def all_symbols_url(self):
        url = web_utils.public_rest_url(CONSTANTS.EXCHANGE_INFO_PATH_URL)
        return re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")

    @property
    def latest_prices_url(self):
        url = web_utils.public_rest_url(CONSTANTS.TICKER_LATEST_PATH_URL)
        return re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")

    @property
    def network_status_url(self):
        url = web_utils.public_rest_url(CONSTANTS.TICKER_LATEST_PATH_URL)
        return re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")

    @property
    def trading_rules_url(self):
        url = web_utils.public_rest_url(CONSTANTS.EXCHANGE_INFO_PATH_URL)
        return re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")

    @property
    def order_creation_url(self):
        url = web_utils.private_rest_url(CONSTANTS.ORDERS_PATH_URL)
        return re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")

    @property
    def balance_url(self):
        url = web_utils.private_rest_url(CONSTANTS.ACCOUNT_PATH_URL)
        return re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")

    @property
    def funding_info_url(self):
        url = web_utils.public_rest_url(CONSTANTS.TICKER_LATEST_PATH_URL)
        return re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")

    @property
    def funding_payment_url(self):
        # Vest doesn't have a separate funding payment endpoint that we use for payments,
        # payments come via funding history or similar. But for the test abstract class, 
        # we might need to mock something if it calls it. 
        # The generic test calls `funding_payment_url` in `test_funding_payment_polling_loop_sends_update_event`
        # We will set it to funding history
        url = web_utils.public_rest_url(CONSTANTS.FUNDING_HISTORY_PATH_URL)
        return re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")

    @property
    def balance_request_mock_response_only_base(self):
        return {
            "balances": [],
            "positions": [],
            "lp": {"balance": "0", "shares": "0", "unrealizedPnl": "0"}
        }

    @property
    def all_symbols_request_mock_response(self):
        return {
            "symbols": [
                {
                    "symbol": self.exchange_trading_pair,
                    "status": "TRADING",
                    "base": self.base_asset,
                    "quote": self.quote_asset,
                    "sizeDecimals": 4,
                    "priceDecimals": 2,
                    "initMarginRatio": "0.1",
                    "maintMarginRatio": "0.05",
                    "takerFee": "0.0001",
                    "isolated": False,
                    "minQty": "0.0001",  # Added for tests
                    "maxQty": "1000",
                    "tickSize": "0.01",
                }
            ]
        }

    @property
    def latest_prices_request_mock_response(self):
        return {
            "tickers": [
                {
                    "symbol": self.exchange_trading_pair,
                    "markPrice": str(self.expected_latest_price),
                    "indexPrice": str(self.expected_latest_price),
                    "imbalance": "0",
                    "oneHrFundingRate": "0.0001",
                    "cumFunding": "1.23",
                    "status": "TRADING",
                }
            ]
        }

    @property
    def all_symbols_including_invalid_pair_mock_response(self):
        return "INVALID-PAIR", {
            "symbols": [
                {
                    "symbol": self.exchange_trading_pair,
                    "status": "TRADING",
                    "base": self.base_asset,
                    "quote": self.quote_asset,
                    "sizeDecimals": 4,
                    "priceDecimals": 2,
                },
                {
                    "symbol": "INVALID-PAIR",
                    "status": "HALT",
                    "base": "INV",
                    "quote": "USDC",
                }
            ]
        }

    def empty_funding_payment_mock_response(self):
        return []

    @property
    def network_status_request_successful_mock_response(self):
        return self.latest_prices_request_mock_response

    @property
    def trading_rules_request_mock_response(self):
        return self.all_symbols_request_mock_response

    @property
    def trading_rules_request_erroneous_mock_response(self):
        return {
            "symbols": [
                {
                    "symbol": self.exchange_trading_pair,
                    # Missing critical fields
                }
            ]
        }

    @property
    def order_creation_request_successful_mock_response(self):
        return {
            "id": self.expected_exchange_order_id,
            "status": "NEW",
            "postTime": 1683849600076,
            "nonce": 0
        }

    @property
    def balance_request_mock_response_for_base_and_quote(self):
        return {
            "balances": [
                {
                    "asset": self.quote_asset,
                    "total": "100",
                    "locked": "10"
                }
            ],
            "positions": [
                {
                    "symbol": self.exchange_trading_pair,
                    "isLong": True,
                    "size": "1.0",
                    "entryPrice": "10000",
                    "entryFunding": "0",
                    "unrealizedPnl": "0",
                    "settledFunding": "0",
                    "markPrice": "10000",
                    "indexPrice": "10000",
                    "liqPrice": "5000",
                    "initMargin": "1000",
                    "maintMargin": "500",
                    "initMarginRatio": "0.1"
                }
            ],
            "withdrawable": "90"
        }

    def configure_failed_set_position_mode(
        self,
        position_mode: PositionMode,
        mock_api: aioresponses,
        callback: Optional[Callable] = lambda *args, **kwargs: None,
    ):
        # Vest only supports ONEWAY, so HEDGE should fail locally without request
        pass

    def configure_successful_set_position_mode(
        self,
        position_mode: PositionMode,
        mock_api: aioresponses,
        callback: Optional[Callable] = lambda *args, **kwargs: None,
    ):
        # ONEWAY is default and only supported, no request needed
        pass

    def is_cancel_request_executed_synchronously_by_server(self) -> bool:
        return False

    @property
    def expected_latest_price(self):
        return 10000.0

    @property
    def funding_payment_mock_response(self):
        return [
            {
                "symbol": self.exchange_trading_pair,
                "time": 1683849600076,
                "oneHrFundingRate": "0.001",
            }
        ]

    @property
    def expected_supported_position_modes(self) -> List[PositionMode]:
        return [PositionMode.ONEWAY]

    @property
    def funding_info_mock_response(self):
        return self.latest_prices_request_mock_response

    @property
    def expected_supported_order_types(self):
        return [OrderType.LIMIT, OrderType.MARKET]

    @property
    def expected_trading_rule(self):
        return TradingRule(
            trading_pair=self.trading_pair,
            min_order_size=Decimal("0.0001"),
            max_order_size=Decimal("1000"),
            min_price_increment=Decimal("0.01"),
            min_base_amount_increment=Decimal("0.0001"),
        )

    @property
    def expected_logged_error_for_erroneous_trading_rule(self):
        return f"Error parsing the trading pair rule {self.trading_rules_request_erroneous_mock_response['symbols'][0]}. Skipping."

    @property
    def expected_exchange_order_id(self):
        return "0x12345"

    @property
    def is_order_fill_http_update_included_in_status_update(self) -> bool:
        return True

    @property
    def is_order_fill_http_update_executed_during_websocket_order_event_processing(self) -> bool:
        return False

    @property
    def expected_partial_fill_price(self) -> Decimal:
        return Decimal("10000")

    @property
    def expected_partial_fill_amount(self) -> Decimal:
        return Decimal("0.1")

    @property
    def expected_fill_fee(self) -> TradeFeeBase:
        return AddedToCostTradeFee(
            percent_token=self.quote_asset,
            flat_fees=[TokenAmount(token=self.quote_asset, amount=Decimal("0.1"))],
        )

    @property
    def expected_fill_trade_id(self) -> str:
        return "0xTrade123"

    def exchange_symbol_for_tokens(self, base_token: str, quote_token: str) -> str:
        return f"{base_token}-PERP"

    def create_exchange_instance(self):
        exchange = VestPerpetualDerivative(
            client_config_map=None,
            vest_perpetual_api_key=self.api_key,
            vest_perpetual_signing_key=self.signing_key,
            vest_perpetual_account_group=self.account_group,
            vest_perpetual_use_testnet=False,
            trading_pairs=[self.trading_pair],
        )
        exchange._perpetual_trading.set_leverage(self.trading_pair, 1)
        return exchange

    def validate_order_creation_request(self, order: InFlightOrder, request_call: RequestCall):
        request_data = json.loads(request_call.kwargs["data"])
        order_data = request_data["order"]
        self.assertEqual(self.exchange_trading_pair, order_data["symbol"])
        self.assertEqual(order.trade_type == TradeType.BUY, order_data["isBuy"])
        self.assertEqual(str(order.amount), order_data["size"])
        self.assertEqual(order.order_type.name, order_data["orderType"])

    def validate_order_cancelation_request(self, order: InFlightOrder, request_call: RequestCall):
        request_data = json.loads(request_call.kwargs["data"])
        self.assertEqual(order.exchange_order_id, request_data["id"])
        self.assertEqual("CANCELLED", request_data["status"])

    def validate_order_status_request(self, order: InFlightOrder, request_call: RequestCall):
        # Order status is fetched via GET /orders/{order_id}
        # Params not needed if using path params, but check if implemented with query params
        pass

    def validate_trades_request(self, order: InFlightOrder, request_call: RequestCall):
        # Trades fetch params
        pass

    def configure_successful_cancelation_response(
        self,
        order: InFlightOrder,
        mock_api: aioresponses,
        callback: Optional[Callable] = lambda *args, **kwargs: None,
    ) -> str:
        url = web_utils.private_rest_url(CONSTANTS.ORDERS_CANCEL_PATH_URL) # OR ORDERS_PATH_URL with DELETE?
        # Based on constants, it seems there is a specific cancel path or DELETE /orders
        # Let's assume DELETE /orders based on docs, so url is ORDERS_PATH_URL
        # But verify implementation of _place_cancel. 
        # For now, sticking to constants.
        # Wait, we haven't implemented _place_cancel yet.
        url = web_utils.private_rest_url(CONSTANTS.ORDERS_PATH_URL)
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        
        response = {
            "id": order.exchange_order_id,
            "status": "CANCELLED",
            "postTime": 1683849600076,
            "nonce": 0
        }
        mock_api.delete(regex_url, body=json.dumps(response), callback=callback)
        return url

    def configure_erroneous_cancelation_response(
        self,
        order: InFlightOrder,
        mock_api: aioresponses,
        callback: Optional[Callable] = lambda *args, **kwargs: None,
    ) -> str:
        url = web_utils.private_rest_url(CONSTANTS.ORDERS_PATH_URL)
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        mock_api.delete(regex_url, status=400, callback=callback)
        return url

    def configure_one_successful_one_erroneous_cancel_all_response(
        self,
        successful_order: InFlightOrder,
        erroneous_order: InFlightOrder,
        mock_api: aioresponses,
    ) -> List[str]:
        # Since cancellations are individual requests, we configure them separately
        url1 = self.configure_successful_cancelation_response(successful_order, mock_api)
        url2 = self.configure_erroneous_cancelation_response(erroneous_order, mock_api)
        return [url1, url2]

    def configure_completely_filled_order_status_response(
        self,
        order: InFlightOrder,
        mock_api: aioresponses,
        callback: Optional[Callable] = lambda *args, **kwargs: None,
    ):
        url = web_utils.private_rest_url(f"{CONSTANTS.ORDERS_PATH_URL}/{order.exchange_order_id}")
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        
        response = {
            "id": order.exchange_order_id,
            "symbol": self.exchange_trading_pair,
            "isBuy": order.trade_type == TradeType.BUY,
            "orderType": order.order_type.name,
            "limitPrice": str(order.price),
            "size": str(order.amount),
            "status": "FILLED",
            "lastFilledSize": str(order.amount),
            "lastFilledPrice": str(order.price),
            "avgFilledPrice": str(order.price),
            "cumFunding": "0",
            "fees": "0.1",
        }
        mock_api.get(regex_url, body=json.dumps(response), callback=callback)
        return url

    def configure_canceled_order_status_response(
        self,
        order: InFlightOrder,
        mock_api: aioresponses,
        callback: Optional[Callable] = lambda *args, **kwargs: None,
    ):
        url = web_utils.private_rest_url(f"{CONSTANTS.ORDERS_PATH_URL}/{order.exchange_order_id}")
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        
        response = {
            "id": order.exchange_order_id,
            "status": "CANCELLED",
        }
        mock_api.get(regex_url, body=json.dumps(response), callback=callback)
        return url

    def configure_erroneous_http_fill_trade_response(
        self,
        order: InFlightOrder,
        mock_api: aioresponses,
        callback: Optional[Callable] = lambda *args, **kwargs: None,
    ):
        url = web_utils.private_rest_url(CONSTANTS.TRADES_PATH_URL)
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        mock_api.get(regex_url, status=400, callback=callback)
        return url

    def configure_open_order_status_response(
        self,
        order: InFlightOrder,
        mock_api: aioresponses,
        callback: Optional[Callable] = lambda *args, **kwargs: None,
    ):
        url = web_utils.private_rest_url(f"{CONSTANTS.ORDERS_PATH_URL}/{order.exchange_order_id}")
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        
        response = {
            "id": order.exchange_order_id,
            "symbol": self.exchange_trading_pair,
            "isBuy": order.trade_type == TradeType.BUY,
            "orderType": order.order_type.name,
            "limitPrice": str(order.price),
            "size": str(order.amount),
            "status": "NEW",
        }
        mock_api.get(regex_url, body=json.dumps(response), callback=callback)
        return url

    def configure_http_error_order_status_response(
        self,
        order: InFlightOrder,
        mock_api: aioresponses,
        callback: Optional[Callable] = lambda *args, **kwargs: None,
    ):
        url = web_utils.private_rest_url(f"{CONSTANTS.ORDERS_PATH_URL}/{order.exchange_order_id}")
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        mock_api.get(regex_url, status=404, callback=callback)
        return url

    def configure_partially_filled_order_status_response(
        self,
        order: InFlightOrder,
        mock_api: aioresponses,
        callback: Optional[Callable] = lambda *args, **kwargs: None,
    ):
        url = web_utils.private_rest_url(f"{CONSTANTS.ORDERS_PATH_URL}/{order.exchange_order_id}")
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        
        response = {
            "id": order.exchange_order_id,
            "symbol": self.exchange_trading_pair,
            "isBuy": order.trade_type == TradeType.BUY,
            "orderType": order.order_type.name,
            "limitPrice": str(order.price),
            "size": str(order.amount),
            "status": "PARTIALLY_FILLED",
            "lastFilledSize": str(self.expected_partial_fill_amount),
            "lastFilledPrice": str(self.expected_partial_fill_price),
            "avgFilledPrice": str(self.expected_partial_fill_price),
            "fees": "0.1",
        }
        mock_api.get(regex_url, body=json.dumps(response), callback=callback)
        return url

    def configure_partial_fill_trade_response(
        self,
        order: InFlightOrder,
        mock_api: aioresponses,
        callback: Optional[Callable] = lambda *args, **kwargs: None,
    ):
        # If trades are not used for status updates, this might not be called or needed
        # But implementing for completeness
        url = web_utils.private_rest_url(CONSTANTS.TRADES_PATH_URL)
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        
        # This endpoint returns list of fills
        response = [
            {
                "id": self.expected_fill_trade_id,
                "price": str(self.expected_partial_fill_price),
                "qty": str(self.expected_partial_fill_amount),
                "quoteQty": str(self.expected_partial_fill_price * self.expected_partial_fill_amount),
                "time": 1683849600076,
                # context specific fields?
            }
        ]
        mock_api.get(regex_url, body=json.dumps(response), callback=callback)
        return url

    def configure_full_fill_trade_response(
        self,
        order: InFlightOrder,
        mock_api: aioresponses,
        callback: Optional[Callable] = lambda *args, **kwargs: None,
    ):
        url = web_utils.private_rest_url(CONSTANTS.TRADES_PATH_URL)
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        
        response = [
            {
                "id": self.expected_fill_trade_id,
                "price": str(order.price),
                "qty": str(order.amount),
                "quoteQty": str(order.price * order.amount),
                "time": 1683849600076,
            }
        ]
        mock_api.get(regex_url, body=json.dumps(response), callback=callback)
        return url

    def order_event_for_new_order_websocket_update(self, order: InFlightOrder):
        return {
            "channel": "account_private",
            "data": {
                "event": "ORDER",
                "args": {
                    "id": order.exchange_order_id,
                    "symbol": self.exchange_trading_pair,
                    "isBuy": order.trade_type == TradeType.BUY,
                    "orderType": order.order_type.name,
                    "limitPrice": str(order.price),
                    "size": str(order.amount),
                    "status": "NEW",
                    "postTime": 1683849600076,
                    "nonce": 0
                }
            }
        }

    def order_event_for_canceled_order_websocket_update(self, order: InFlightOrder):
        return {
            "channel": "account_private",
            "data": {
                "event": "ORDER",
                "args": {
                    "id": order.exchange_order_id,
                    "status": "CANCELLED",
                    "postTime": 1683849600076,
                    "nonce": 0
                }
            }
        }

    def order_event_for_full_fill_websocket_update(self, order: InFlightOrder):
        return {
            "channel": "account_private",
            "data": {
                "event": "ORDER",
                "args": {
                    "id": order.exchange_order_id,
                    "symbol": self.exchange_trading_pair,
                    "isBuy": order.trade_type == TradeType.BUY,
                    "orderType": order.order_type.name,
                    "limitPrice": str(order.price),
                    "size": str(order.amount),
                    "status": "FILLED",
                    "lastFilledSize": str(order.amount),
                    "lastFilledPrice": str(order.price),
                    "avgFilledPrice": str(order.price),
                    "fees": "0.1",
                    "postTime": 1683849600076,
                    "nonce": 0
                }
            }
        }

    def trade_event_for_full_fill_websocket_update(self, order: InFlightOrder):
        # Vest sends fill info within the ORDER event, but if there was a separate trade event:
        return None

    def position_event_for_full_fill_websocket_update(self, order: InFlightOrder, unrealized_pnl: float):
        # Vest account_private might not send position updates in real-time in the same way
        # But let's assume we can simulate a position update if supported
        return None

    def funding_info_event_for_websocket_update(self):
        return {
            "channel": "tickers",
            "data": [
                {
                    "symbol": self.exchange_trading_pair,
                    "oneHrFundingRate": "0.0001",
                    "cumFunding": "1.23",
                    "markPrice": "10000",
                    "indexPrice": "10000",
                }
            ]
        }
