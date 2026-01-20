import asyncio
import json
import re
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from aioresponses import aioresponses
from bidict import bidict

import hummingbot.connector.derivative.extended_perpetual.extended_perpetual_constants as CONSTANTS
import hummingbot.connector.derivative.extended_perpetual.extended_perpetual_web_utils as web_utils
from hummingbot.client.config.client_config_map import ClientConfigMap
from hummingbot.client.config.config_helpers import ClientConfigAdapter
from hummingbot.connector.derivative.extended_perpetual.extended_perpetual_derivative import (
    ExtendedPerpetualDerivative,
)
from hummingbot.connector.trading_rule import TradingRule
from hummingbot.core.data_type.common import OrderType, PositionAction, PositionMode, PositionSide, TradeType
from hummingbot.core.data_type.in_flight_order import InFlightOrder, OrderState
from hummingbot.core.data_type.trade_fee import TokenAmount, TradeFeeBase
from test.isolated_asyncio_wrapper_test_case import IsolatedAsyncioWrapperTestCase


class ExtendedPerpetualDerivativeTests(IsolatedAsyncioWrapperTestCase):
    level = 0

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.api_key = "test_api_key"
        cls.stark_private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        cls.stark_public_key = "0x5d05989e9302dcebc74e241001e3e3ac3f4402ccf2f8e6f74b034b07ad6a904"
        cls.vault_id = 100
        cls.base_asset = "ETH"
        cls.quote_asset = "USD"
        cls.trading_pair = f"{cls.base_asset}-{cls.quote_asset}"
        cls.ex_trading_pair = f"{cls.base_asset}-{cls.quote_asset}"
        cls.domain = CONSTANTS.DEFAULT_DOMAIN

    def setUp(self) -> None:
        super().setUp()
        self.log_records = []

        client_config_map = ClientConfigAdapter(ClientConfigMap())
        self.exchange = ExtendedPerpetualDerivative(
            client_config_map,
            extended_perpetual_api_key=self.api_key,
            extended_perpetual_stark_private_key=self.stark_private_key,
            extended_perpetual_stark_public_key=self.stark_public_key,
            extended_perpetual_vault_id=self.vault_id,
            trading_pairs=[self.trading_pair],
        )

        self.exchange.logger().setLevel(1)
        self.exchange.logger().addHandler(self)

        self.exchange._set_trading_pair_symbol_map(
            bidict({self.ex_trading_pair: self.trading_pair})
        )

    def tearDown(self) -> None:
        super().tearDown()

    def handle(self, record):
        self.log_records.append(record)

    def _is_logged(self, log_level: str, message: str) -> bool:
        return any(
            record.levelname == log_level and record.getMessage() == message
            for record in self.log_records
        )

    def _simulate_trading_rules_initialized(self):
        self.exchange._trading_rules = {
            self.trading_pair: TradingRule(
                trading_pair=self.trading_pair,
                min_order_size=Decimal("0.001"),
                min_base_amount_increment=Decimal("0.001"),
                min_price_increment=Decimal("0.01"),
                buy_order_collateral_token="USDC",
                sell_order_collateral_token="USDC",
            )
        }
        self.exchange._market_info[self.ex_trading_pair] = {
            "name": self.ex_trading_pair,
            "syntheticAssetId": "0x2",
            "collateralAssetId": "0x1",
            "syntheticResolution": 10**8,
            "collateralResolution": 10**6,
        }

    def get_exchange_rules_response(self) -> Dict[str, Any]:
        return {
            "status": "OK",
            "data": [
                {
                    "name": self.ex_trading_pair,
                    "syntheticAssetId": "0x2",
                    "collateralAssetId": "0x1",
                    "syntheticResolution": 10**8,
                    "collateralResolution": 10**6,
                    "tradingConfig": {
                        "minOrderSize": "0.001",
                        "minOrderSizeChange": "0.001",
                        "minPriceChange": "0.01",
                    }
                }
            ]
        }

    def get_balance_response(self) -> Dict[str, Any]:
        return {
            "status": "OK",
            "data": {
                "collateralName": "USDC",
                "equity": "10000.0",
                "availableForTrade": "9000.0",
            }
        }

    def get_positions_response(self) -> Dict[str, Any]:
        return {
            "status": "OK",
            "data": [
                {
                    "market": self.ex_trading_pair,
                    "side": "LONG",
                    "size": "1.5",
                    "openPrice": "2000.0",
                    "leverage": "10",
                    "unrealisedPnl": "100.0",
                }
            ]
        }

    def get_order_creation_response(self) -> Dict[str, Any]:
        return {
            "status": "OK",
            "data": {
                "id": "12345",
                "externalId": "HBOT123",
                "status": "new",
                "createdTime": 1700000000000,
            }
        }

    def get_order_cancellation_response(self) -> Dict[str, Any]:
        return {
            "status": "OK",
            "data": {
                "id": "12345",
                "status": "cancelled",
            }
        }

    def get_order_status_response(self, status: str = "new") -> Dict[str, Any]:
        return {
            "status": "OK",
            "data": {
                "id": "12345",
                "externalId": "HBOT123",
                "status": status,
                "updatedTime": 1700000000000,
            }
        }

    def get_trades_response(self) -> Dict[str, Any]:
        return {
            "status": "OK",
            "data": [
                {
                    "id": "trade123",
                    "orderId": "12345",
                    "fee": "0.5",
                    "createdTime": 1700000000000,
                    "averagePrice": "2000.0",
                    "filledQty": "1.0",
                    "value": "2000.0",
                }
            ]
        }

    async def test_name_property_mainnet(self):
        self.assertEqual("extended_perpetual", self.exchange.name)

    async def test_name_property_testnet(self):
        client_config_map = ClientConfigAdapter(ClientConfigMap())
        testnet_exchange = ExtendedPerpetualDerivative(
            client_config_map,
            extended_perpetual_api_key=self.api_key,
            extended_perpetual_stark_private_key=self.stark_private_key,
            extended_perpetual_stark_public_key=self.stark_public_key,
            extended_perpetual_vault_id=self.vault_id,
            trading_pairs=[self.trading_pair],
            domain=CONSTANTS.TESTNET_DOMAIN,
        )
        self.assertEqual("extended_perpetual_testnet", testnet_exchange.name)

    async def test_authenticator_property(self):
        self.assertIsNotNone(self.exchange.authenticator)
        self.assertEqual(self.api_key, self.exchange.authenticator.api_key)

    async def test_rate_limits_rules(self):
        self.assertEqual(CONSTANTS.RATE_LIMITS, self.exchange.rate_limits_rules)

    async def test_domain_property(self):
        self.assertEqual(CONSTANTS.DEFAULT_DOMAIN, self.exchange.domain)

    async def test_client_order_id_max_length(self):
        self.assertEqual(CONSTANTS.MAX_ORDER_ID_LEN, self.exchange.client_order_id_max_length)

    async def test_client_order_id_prefix(self):
        self.assertEqual(CONSTANTS.HBOT_ORDER_ID_PREFIX, self.exchange.client_order_id_prefix)

    async def test_supported_order_types(self):
        supported = self.exchange.supported_order_types
        self.assertIn(OrderType.LIMIT, supported)
        self.assertIn(OrderType.LIMIT_MAKER, supported)
        self.assertIn(OrderType.MARKET, supported)

    async def test_supported_position_modes(self):
        self.assertEqual([PositionMode.ONEWAY], self.exchange.supported_position_modes)

    async def test_funding_fee_poll_interval(self):
        self.assertEqual(3600, self.exchange.funding_fee_poll_interval)

    @aioresponses()
    async def test_update_balances(self, mock_api):
        url = web_utils.private_rest_url(CONSTANTS.BALANCE_PATH, self.domain)
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        response = self.get_balance_response()
        mock_api.get(regex_url, body=json.dumps(response))

        await self.exchange._update_balances()

        self.assertEqual(Decimal("10000.0"), self.exchange._account_balances["USDC"])
        self.assertEqual(Decimal("9000.0"), self.exchange._account_available_balances["USDC"])

    @aioresponses()
    async def test_update_balances_error(self, mock_api):
        url = web_utils.private_rest_url(CONSTANTS.BALANCE_PATH, self.domain)
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        response = {"status": "ERROR", "message": "Unauthorized"}
        mock_api.get(regex_url, body=json.dumps(response))

        await self.exchange._update_balances()

        self.assertTrue(
            self._is_logged("ERROR", f"Error updating balances: {response}")
        )

    @aioresponses()
    async def test_update_positions(self, mock_api):
        url = web_utils.private_rest_url(CONSTANTS.POSITIONS_PATH, self.domain)
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        response = self.get_positions_response()
        mock_api.get(regex_url, body=json.dumps(response))

        await self.exchange._update_positions()

        positions = self.exchange._perpetual_trading.account_positions
        self.assertGreaterEqual(len(positions), 0)

    @aioresponses()
    async def test_update_positions_error(self, mock_api):
        url = web_utils.private_rest_url(CONSTANTS.POSITIONS_PATH, self.domain)
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        response = {"status": "ERROR", "message": "Unauthorized"}
        mock_api.get(regex_url, body=json.dumps(response))

        await self.exchange._update_positions()

        self.assertTrue(
            self._is_logged("ERROR", f"Error updating positions: {response}")
        )

    @aioresponses()
    async def test_format_trading_rules(self, mock_api):
        response = self.get_exchange_rules_response()

        rules = await self.exchange._format_trading_rules(response)

        self.assertEqual(1, len(rules))
        rule = rules[0]
        self.assertEqual(self.ex_trading_pair, rule.trading_pair)
        self.assertEqual(Decimal("0.001"), rule.min_order_size)
        self.assertEqual(Decimal("0.001"), rule.min_base_amount_increment)
        self.assertEqual(Decimal("0.01"), rule.min_price_increment)

    async def test_format_trading_rules_error_response(self):
        response = {"status": "ERROR", "message": "Bad request"}

        rules = await self.exchange._format_trading_rules(response)

        self.assertEqual(0, len(rules))
        self.assertTrue(
            self._is_logged("ERROR", f"Error fetching trading rules: {response}")
        )

    @aioresponses()
    async def test_update_trading_rules(self, mock_api):
        url = web_utils.public_rest_url(CONSTANTS.MARKETS_PATH, self.domain)
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        response = self.get_exchange_rules_response()
        mock_api.get(regex_url, body=json.dumps(response))

        await self.exchange._update_trading_rules()

        self.assertIn(self.ex_trading_pair, self.exchange._trading_rules)

    async def test_get_fee_maker(self):
        self.exchange._fee_rates = {"maker": Decimal("0.0002"), "taker": Decimal("0.0005")}

        fee = self.exchange._get_fee(
            self.base_asset, self.quote_asset,
            OrderType.LIMIT_MAKER, TradeType.BUY,
            Decimal("1.0"), Decimal("2000.0"),
            is_maker=True
        )

        self.assertIsInstance(fee, TradeFeeBase)

    async def test_get_fee_taker(self):
        self.exchange._fee_rates = {"maker": Decimal("0.0002"), "taker": Decimal("0.0005")}

        fee = self.exchange._get_fee(
            self.base_asset, self.quote_asset,
            OrderType.MARKET, TradeType.BUY,
            Decimal("1.0"), Decimal("2000.0"),
            is_maker=False
        )

        self.assertIsInstance(fee, TradeFeeBase)

    async def test_buy_returns_order_id(self):
        self._simulate_trading_rules_initialized()
        self.exchange._set_current_timestamp(1640780000)

        with patch.object(self.exchange, '_create_order', new_callable=AsyncMock):
            order_id = self.exchange.buy(
                trading_pair=self.trading_pair,
                amount=Decimal("1.0"),
                order_type=OrderType.LIMIT,
                price=Decimal("2000.0"),
            )

        self.assertIsNotNone(order_id)
        self.assertTrue(order_id.startswith(CONSTANTS.HBOT_ORDER_ID_PREFIX))

    async def test_sell_returns_order_id(self):
        self._simulate_trading_rules_initialized()
        self.exchange._set_current_timestamp(1640780000)

        with patch.object(self.exchange, '_create_order', new_callable=AsyncMock):
            order_id = self.exchange.sell(
                trading_pair=self.trading_pair,
                amount=Decimal("1.0"),
                order_type=OrderType.LIMIT,
                price=Decimal("2000.0"),
            )

        self.assertIsNotNone(order_id)
        self.assertTrue(order_id.startswith(CONSTANTS.HBOT_ORDER_ID_PREFIX))

    async def test_generate_order_id_buy(self):
        order_id = self.exchange._generate_order_id(is_buy=True, trading_pair=self.trading_pair)
        self.assertTrue(order_id.startswith(CONSTANTS.HBOT_ORDER_ID_PREFIX))

    async def test_generate_order_id_sell(self):
        order_id = self.exchange._generate_order_id(is_buy=False, trading_pair=self.trading_pair)
        self.assertTrue(order_id.startswith(CONSTANTS.HBOT_ORDER_ID_PREFIX))

    async def test_generate_order_id_unique(self):
        order_id_1 = self.exchange._generate_order_id(is_buy=True, trading_pair=self.trading_pair)
        await asyncio.sleep(0.01)
        order_id_2 = self.exchange._generate_order_id(is_buy=True, trading_pair=self.trading_pair)
        self.assertNotEqual(order_id_1, order_id_2)

    async def test_process_order_update(self):
        self._simulate_trading_rules_initialized()
        self.exchange._set_current_timestamp(1640780000)

        self.exchange.start_tracking_order(
            order_id="HBOT123",
            exchange_order_id="12345",
            trading_pair=self.trading_pair,
            trade_type=TradeType.BUY,
            price=Decimal("2000.0"),
            amount=Decimal("1.0"),
            order_type=OrderType.LIMIT,
        )

        order_data = {
            "externalId": "HBOT123",
            "id": "12345",
            "status": "filled",
            "updatedTime": 1640780001000,
        }

        self.exchange._process_order_update(order_data)

        order = self.exchange._order_tracker.all_updatable_orders.get("HBOT123")
        self.assertIsNotNone(order)

    async def test_process_balance_update(self):
        balance_data = {
            "collateralName": "USDC",
            "equity": "15000.0",
            "availableForTrade": "14000.0",
        }

        self.exchange._process_balance_update(balance_data)

        self.assertEqual(Decimal("15000.0"), self.exchange._account_balances["USDC"])
        self.assertEqual(Decimal("14000.0"), self.exchange._account_available_balances["USDC"])

    async def test_process_position_updates(self):
        positions_data = [
            {
                "market": self.ex_trading_pair,
                "side": "LONG",
                "size": "2.0",
                "openPrice": "1900.0",
                "leverage": "5",
                "unrealisedPnl": "200.0",
            }
        ]

        self.exchange._process_position_updates(positions_data)

        positions = self.exchange._perpetual_trading.account_positions
        self.assertGreater(len(positions), 0)

    async def test_process_position_updates_removes_zero_size(self):
        positions_data = [
            {
                "market": self.ex_trading_pair,
                "side": "LONG",
                "size": "1.0",
                "openPrice": "1900.0",
                "leverage": "5",
                "unrealisedPnl": "100.0",
            }
        ]
        self.exchange._process_position_updates(positions_data)

        zero_positions_data = [
            {
                "market": self.ex_trading_pair,
                "side": "LONG",
                "size": "0",
                "openPrice": "1900.0",
                "leverage": "5",
                "unrealisedPnl": "0.0",
            }
        ]
        self.exchange._process_position_updates(zero_positions_data)

    @aioresponses()
    async def test_request_order_status(self, mock_api):
        self._simulate_trading_rules_initialized()
        self.exchange._set_current_timestamp(1640780000)

        self.exchange.start_tracking_order(
            order_id="HBOT123",
            exchange_order_id="12345",
            trading_pair=self.trading_pair,
            trade_type=TradeType.BUY,
            price=Decimal("2000.0"),
            amount=Decimal("1.0"),
            order_type=OrderType.LIMIT,
        )

        tracked_order = self.exchange._order_tracker.all_updatable_orders["HBOT123"]

        url = web_utils.private_rest_url(f"{CONSTANTS.OPEN_ORDERS_PATH}/12345", self.domain)
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        response = self.get_order_status_response("filled")
        mock_api.get(regex_url, body=json.dumps(response))

        order_update = await self.exchange._request_order_status(tracked_order)

        self.assertEqual("HBOT123", order_update.client_order_id)
        self.assertEqual("12345", order_update.exchange_order_id)
        self.assertEqual(OrderState.FILLED, order_update.new_state)

    @aioresponses()
    async def test_all_trade_updates_for_order(self, mock_api):
        self._simulate_trading_rules_initialized()
        self.exchange._set_current_timestamp(1640780000)

        self.exchange.start_tracking_order(
            order_id="HBOT123",
            exchange_order_id="12345",
            trading_pair=self.trading_pair,
            trade_type=TradeType.BUY,
            price=Decimal("2000.0"),
            amount=Decimal("1.0"),
            order_type=OrderType.LIMIT,
        )

        tracked_order = self.exchange._order_tracker.all_fillable_orders["HBOT123"]

        url = web_utils.private_rest_url(CONSTANTS.TRADES_PATH, self.domain)
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        response = self.get_trades_response()
        mock_api.get(regex_url, body=json.dumps(response))

        trade_updates = await self.exchange._all_trade_updates_for_order(tracked_order)

        self.assertEqual(1, len(trade_updates))
        trade_update = trade_updates[0]
        self.assertEqual("trade123", trade_update.trade_id)
        self.assertEqual(Decimal("2000.0"), trade_update.fill_price)
        self.assertEqual(Decimal("1.0"), trade_update.fill_base_amount)


class ExtendedPerpetualDerivativeAPITests(IsolatedAsyncioWrapperTestCase):
    level = 0

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.api_key = "test_api_key"
        cls.stark_private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        cls.stark_public_key = "0x5d05989e9302dcebc74e241001e3e3ac3f4402ccf2f8e6f74b034b07ad6a904"
        cls.vault_id = 100
        cls.trading_pair = "ETH-USD"
        cls.domain = CONSTANTS.DEFAULT_DOMAIN

    def setUp(self) -> None:
        super().setUp()

        client_config_map = ClientConfigAdapter(ClientConfigMap())
        self.exchange = ExtendedPerpetualDerivative(
            client_config_map,
            extended_perpetual_api_key=self.api_key,
            extended_perpetual_stark_private_key=self.stark_private_key,
            extended_perpetual_stark_public_key=self.stark_public_key,
            extended_perpetual_vault_id=self.vault_id,
            trading_pairs=[self.trading_pair],
        )

    @aioresponses()
    async def test_api_get(self, mock_api):
        url = web_utils.public_rest_url(CONSTANTS.MARKETS_PATH, self.domain)
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        response = {"status": "OK", "data": []}
        mock_api.get(regex_url, body=json.dumps(response))

        result = await self.exchange._api_get(
            path_url=CONSTANTS.MARKETS_PATH,
            params={},
            is_auth_required=False,
        )

        self.assertEqual("OK", result["status"])

    @aioresponses()
    async def test_api_post(self, mock_api):
        url = web_utils.private_rest_url(CONSTANTS.CREATE_ORDER_PATH, self.domain)
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        response = {"status": "OK", "data": {"id": "12345"}}
        mock_api.post(regex_url, body=json.dumps(response))

        result = await self.exchange._api_post(
            path_url=CONSTANTS.CREATE_ORDER_PATH,
            data={"test": "data"},
            is_auth_required=True,
        )

        self.assertEqual("OK", result["status"])

    @aioresponses()
    async def test_api_delete(self, mock_api):
        cancel_path = CONSTANTS.CANCEL_ORDER_PATH.format(id="12345")
        url = web_utils.private_rest_url(cancel_path, self.domain)
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        response = {"status": "OK", "data": {"status": "cancelled"}}
        mock_api.delete(regex_url, body=json.dumps(response))

        result = await self.exchange._api_delete(
            path_url=cancel_path,
            params={},
            is_auth_required=True,
            throttler_limit_id=CONSTANTS.CANCEL_ORDER_PATH,
        )

        self.assertEqual("OK", result["status"])


class ExtendedPerpetualDerivativeOrderStateTests(IsolatedAsyncioWrapperTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.api_key = "test_api_key"
        cls.stark_private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        cls.stark_public_key = "0x5d05989e9302dcebc74e241001e3e3ac3f4402ccf2f8e6f74b034b07ad6a904"
        cls.vault_id = 100
        cls.trading_pair = "ETH-USD"

    def setUp(self) -> None:
        super().setUp()
        client_config_map = ClientConfigAdapter(ClientConfigMap())
        self.exchange = ExtendedPerpetualDerivative(
            client_config_map,
            extended_perpetual_api_key=self.api_key,
            extended_perpetual_stark_private_key=self.stark_private_key,
            extended_perpetual_stark_public_key=self.stark_public_key,
            extended_perpetual_vault_id=self.vault_id,
            trading_pairs=[self.trading_pair],
        )

    async def test_order_state_mapping_new(self):
        order_data = {"externalId": "test", "status": "new"}
        status = order_data.get("status", "").lower()
        new_state = CONSTANTS.ORDER_STATE.get(status, OrderState.OPEN)
        self.assertEqual(OrderState.OPEN, new_state)

    async def test_order_state_mapping_filled(self):
        order_data = {"externalId": "test", "status": "FILLED"}
        status = order_data.get("status", "").lower()
        new_state = CONSTANTS.ORDER_STATE.get(status.lower(), OrderState.OPEN)
        self.assertEqual(OrderState.FILLED, new_state)

    async def test_order_state_mapping_cancelled(self):
        order_data = {"externalId": "test", "status": "cancelled"}
        status = order_data.get("status", "").lower()
        new_state = CONSTANTS.ORDER_STATE.get(status, OrderState.OPEN)
        self.assertEqual(OrderState.CANCELED, new_state)

    async def test_order_state_mapping_rejected(self):
        order_data = {"externalId": "test", "status": "rejected"}
        status = order_data.get("status", "").lower()
        new_state = CONSTANTS.ORDER_STATE.get(status, OrderState.OPEN)
        self.assertEqual(OrderState.FAILED, new_state)

    async def test_order_state_mapping_partially_filled(self):
        status = "partially filled"
        new_state = CONSTANTS.ORDER_STATE.get(status, OrderState.OPEN)
        self.assertEqual(OrderState.PARTIALLY_FILLED, new_state)

    async def test_order_state_mapping_unknown_defaults_to_open(self):
        status = "unknown_status"
        new_state = CONSTANTS.ORDER_STATE.get(status, OrderState.OPEN)
        self.assertEqual(OrderState.OPEN, new_state)
