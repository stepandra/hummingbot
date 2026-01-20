import asyncio
import json
import re
from decimal import Decimal
from test.isolated_asyncio_wrapper_test_case import IsolatedAsyncioWrapperTestCase
from typing import Dict
from unittest.mock import AsyncMock, MagicMock, patch

from aioresponses import aioresponses
from bidict import bidict

import hummingbot.connector.derivative.extended_perpetual.extended_perpetual_web_utils as web_utils
import hummingbot.connector.derivative.extended_perpetual.extended_perpetual_constants as CONSTANTS
from hummingbot.client.config.client_config_map import ClientConfigMap
from hummingbot.client.config.config_helpers import ClientConfigAdapter
from hummingbot.connector.derivative.extended_perpetual.extended_perpetual_api_order_book_data_source import (
    ExtendedPerpetualAPIOrderBookDataSource,
)
from hummingbot.connector.derivative.extended_perpetual.extended_perpetual_derivative import (
    ExtendedPerpetualDerivative,
)
from hummingbot.connector.trading_rule import TradingRule
from hummingbot.core.data_type.funding_info import FundingInfo, FundingInfoUpdate
from hummingbot.core.data_type.order_book_message import OrderBookMessage, OrderBookMessageType


class ExtendedPerpetualAPIOrderBookDataSourceTests(IsolatedAsyncioWrapperTestCase):
    level = 0

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.base_asset = "ETH"
        cls.quote_asset = "USD"
        cls.trading_pair = f"{cls.base_asset}-{cls.quote_asset}"
        cls.ex_trading_pair = f"{cls.base_asset}-{cls.quote_asset}"

    def setUp(self) -> None:
        super().setUp()
        self.log_records = []
        self.listening_task = None

        client_config_map = ClientConfigAdapter(ClientConfigMap())
        self.connector = ExtendedPerpetualDerivative(
            client_config_map,
            extended_perpetual_api_key="test_api_key",
            extended_perpetual_stark_private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            extended_perpetual_stark_public_key="0x5d05989e9302dcebc74e241001e3e3ac3f4402ccf2f8e6f74b034b07ad6a904",
            extended_perpetual_vault_id=100,
            trading_pairs=[self.trading_pair],
        )
        self.data_source = ExtendedPerpetualAPIOrderBookDataSource(
            trading_pairs=[self.trading_pair],
            connector=self.connector,
            api_factory=self.connector._web_assistants_factory,
        )

        self._original_full_order_book_reset_time = self.data_source.FULL_ORDER_BOOK_RESET_DELTA_SECONDS
        self.data_source.FULL_ORDER_BOOK_RESET_DELTA_SECONDS = -1

        self.data_source.logger().setLevel(1)
        self.data_source.logger().addHandler(self)

        self.connector._set_trading_pair_symbol_map(
            bidict({f"{self.base_asset}-{self.quote_asset}": self.trading_pair}))

    async def asyncSetUp(self) -> None:
        self.resume_test_event = asyncio.Event()

    def tearDown(self) -> None:
        self.listening_task and self.listening_task.cancel()
        self.data_source.FULL_ORDER_BOOK_RESET_DELTA_SECONDS = self._original_full_order_book_reset_time
        super().tearDown()

    def handle(self, record):
        self.log_records.append(record)

    def _is_logged(self, log_level: str, message: str) -> bool:
        return any(record.levelname == log_level and record.getMessage() == message
                   for record in self.log_records)

    def _create_exception_and_unlock_test_with_event(self, exception):
        self.resume_test_event.set()
        raise exception

    def resume_test_callback(self, *_, **__):
        self.resume_test_event.set()
        return None

    def get_rest_snapshot_msg(self) -> Dict:
        return {
            "status": "OK",
            "data": {
                "bid": [
                    {"price": "2080.3", "qty": "74.6923"},
                    {"price": "2080.0", "qty": "162.2829"},
                    {"price": "1825.5", "qty": "0.0259"},
                    {"price": "1823.6", "qty": "0.0259"},
                ],
                "ask": [
                    {"price": "2080.5", "qty": "73.018"},
                    {"price": "2080.6", "qty": "74.6799"},
                    {"price": "2118.9", "qty": "377.495"},
                    {"price": "2122.1", "qty": "348.8644"},
                ],
            }
        }

    def get_ws_snapshot_msg(self) -> Dict:
        return {
            "type": "SNAPSHOT",
            "ts": 1700687397641,
            "seq": 1,
            "data": {
                "t": "SNAPSHOT",
                "m": self.ex_trading_pair,
                "b": [
                    {"p": "2080.3", "q": "74.6923"},
                    {"p": "2080.0", "q": "162.2829"},
                ],
                "a": [
                    {"p": "2080.5", "q": "73.018"},
                    {"p": "2080.6", "q": "74.6799"},
                ],
            }
        }

    def get_ws_diff_msg(self) -> Dict:
        return {
            "type": "DELTA",
            "ts": 1700687397642,
            "seq": 2,
            "data": {
                "t": "DELTA",
                "m": self.ex_trading_pair,
                "b": [
                    {"p": "2080.4", "q": "74.6923"},
                ],
                "a": [
                    {"p": "2080.5", "q": "73.018"},
                ],
            }
        }

    def get_ws_trade_msg(self) -> Dict:
        return {
            "ts": 1700687397643,
            "data": [
                {
                    "tT": "TRADE",
                    "m": self.ex_trading_pair,
                    "S": "BUY",
                    "T": 1700687397643,
                    "i": 12345,
                    "p": "2080.5",
                    "q": "1.5",
                }
            ]
        }

    def get_funding_info_rest_msg(self) -> Dict:
        return {
            "status": "OK",
            "data": {
                "indexPrice": "2080.0",
                "markPrice": "2081.5",
                "fundingRate": "0.0001",
            }
        }

    def get_market_stats_rest_msg(self) -> Dict:
        return {
            "status": "OK",
            "data": {
                "indexPrice": "2080.0",
                "markPrice": "2081.5",
                "fundingRate": "0.0001",
            }
        }

    @aioresponses()
    async def test_get_new_order_book_successful(self, mock_api):
        url = web_utils.public_rest_url(
            CONSTANTS.ORDERBOOK_PATH.format(market=self.ex_trading_pair)
        )
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        resp = self.get_rest_snapshot_msg()
        mock_api.get(regex_url, body=json.dumps(resp))

        order_book = await self.data_source.get_new_order_book(self.trading_pair)

        bids = list(order_book.bid_entries())
        asks = list(order_book.ask_entries())
        self.assertEqual(4, len(bids))
        self.assertEqual(2080.3, bids[0].price)
        self.assertEqual(74.6923, bids[0].amount)
        self.assertEqual(4, len(asks))
        self.assertEqual(2080.5, asks[0].price)
        self.assertEqual(73.018, asks[0].amount)

    @aioresponses()
    async def test_get_new_order_book_raises_exception_on_error(self, mock_api):
        url = web_utils.public_rest_url(
            CONSTANTS.ORDERBOOK_PATH.format(market=self.ex_trading_pair)
        )
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")

        mock_api.get(regex_url, status=400)
        with self.assertRaises(IOError):
            await self.data_source.get_new_order_book(self.trading_pair)

    @aioresponses()
    async def test_order_book_snapshot_message_parsing(self, mock_api):
        url = web_utils.public_rest_url(
            CONSTANTS.ORDERBOOK_PATH.format(market=self.ex_trading_pair)
        )
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        resp = self.get_rest_snapshot_msg()
        mock_api.get(regex_url, body=json.dumps(resp))

        snapshot_msg = await self.data_source._order_book_snapshot(self.trading_pair)

        self.assertEqual(OrderBookMessageType.SNAPSHOT, snapshot_msg.type)
        self.assertEqual(self.trading_pair, snapshot_msg.trading_pair)
        self.assertEqual(4, len(snapshot_msg.bids))
        self.assertEqual(4, len(snapshot_msg.asks))

    async def test_parse_order_book_snapshot_message(self):
        raw_message = self.get_ws_snapshot_msg()
        message_queue = asyncio.Queue()

        await self.data_source._parse_order_book_snapshot_message(raw_message, message_queue)

        msg: OrderBookMessage = message_queue.get_nowait()
        self.assertEqual(OrderBookMessageType.SNAPSHOT, msg.type)
        self.assertEqual(self.trading_pair, msg.trading_pair)
        self.assertEqual(2, len(msg.bids))
        self.assertEqual(2, len(msg.asks))

    async def test_parse_order_book_diff_message(self):
        self.data_source._last_sequence[self.ex_trading_pair] = 1
        raw_message = self.get_ws_diff_msg()
        message_queue = asyncio.Queue()

        await self.data_source._parse_order_book_diff_message(raw_message, message_queue)

        msg: OrderBookMessage = message_queue.get_nowait()
        self.assertEqual(OrderBookMessageType.DIFF, msg.type)
        self.assertEqual(self.trading_pair, msg.trading_pair)

    @aioresponses()
    async def test_sequence_gap_triggers_resync(self, mock_api):
        url = web_utils.public_rest_url(
            CONSTANTS.ORDERBOOK_PATH.format(market=self.ex_trading_pair)
        )
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        resp = self.get_rest_snapshot_msg()
        mock_api.get(regex_url, body=json.dumps(resp))

        self.data_source._last_sequence[self.ex_trading_pair] = 1
        raw_message = self.get_ws_diff_msg()
        raw_message["seq"] = 5

        message_queue = asyncio.Queue()
        await self.data_source._parse_order_book_diff_message(raw_message, message_queue)

        self.assertTrue(
            self._is_logged(
                "WARNING",
                f"Sequence gap detected for {self.ex_trading_pair}. Expected 2, got 5. Requesting snapshot..."
            )
        )

    async def test_parse_trade_message(self):
        raw_message = self.get_ws_trade_msg()
        message_queue = asyncio.Queue()

        await self.data_source._parse_trade_message(raw_message, message_queue)

        msg: OrderBookMessage = message_queue.get_nowait()
        self.assertEqual(OrderBookMessageType.TRADE, msg.type)
        self.assertEqual(self.trading_pair, msg.trading_pair)
        self.assertEqual(12345, msg.trade_id)
        self.assertEqual(2080.5, msg.content["price"])
        self.assertEqual(1.5, msg.content["amount"])

    async def test_parse_trade_message_sell_side(self):
        raw_message = self.get_ws_trade_msg()
        raw_message["data"][0]["S"] = "SELL"
        message_queue = asyncio.Queue()

        await self.data_source._parse_trade_message(raw_message, message_queue)

        msg: OrderBookMessage = message_queue.get_nowait()
        self.assertEqual(OrderBookMessageType.TRADE, msg.type)

    async def test_parse_trade_message_skips_non_trade_type(self):
        raw_message = self.get_ws_trade_msg()
        raw_message["data"][0]["tT"] = "OTHER"
        message_queue = asyncio.Queue()

        await self.data_source._parse_trade_message(raw_message, message_queue)

        self.assertTrue(message_queue.empty())

    @aioresponses()
    async def test_get_funding_info(self, mock_api):
        url = web_utils.public_rest_url(
            CONSTANTS.MARKET_STATS_PATH.format(market=self.ex_trading_pair)
        )
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")
        resp = self.get_market_stats_rest_msg()
        mock_api.get(regex_url, body=json.dumps(resp))

        funding_info: FundingInfo = await self.data_source.get_funding_info(self.trading_pair)

        self.assertEqual(self.trading_pair, funding_info.trading_pair)
        self.assertEqual(Decimal("2080.0"), funding_info.index_price)
        self.assertEqual(Decimal("2081.5"), funding_info.mark_price)
        self.assertEqual(Decimal("0.0001"), funding_info.rate)

    async def test_channel_originating_message_snapshot(self):
        message = {
            "type": "SNAPSHOT",
            "data": {"t": "SNAPSHOT"}
        }
        channel = self.data_source._channel_originating_message(message)
        self.assertEqual(self.data_source._snapshot_messages_queue_key, channel)

    async def test_channel_originating_message_diff(self):
        message = {
            "type": "DELTA",
            "data": {"t": "DELTA"}
        }
        channel = self.data_source._channel_originating_message(message)
        self.assertEqual(self.data_source._diff_messages_queue_key, channel)

    async def test_channel_originating_message_trade(self):
        message = {
            "data": [{"tT": "TRADE"}]
        }
        channel = self.data_source._channel_originating_message(message)
        self.assertEqual(self.data_source._trade_messages_queue_key, channel)

    async def test_channel_originating_message_funding(self):
        message = {
            "data": {"fundingRate": "0.0001"}
        }
        channel = self.data_source._channel_originating_message(message)
        self.assertEqual(self.data_source._funding_info_messages_queue_key, channel)

    async def test_channel_originating_message_pong(self):
        message = {"type": "pong"}
        channel = self.data_source._channel_originating_message(message)
        self.assertEqual("", channel)

    async def test_process_message_for_unknown_channel_responds_to_ping(self):
        message = {"type": "ping"}
        ws_assistant = MagicMock()
        ws_assistant.send = AsyncMock()

        await self.data_source._process_message_for_unknown_channel(message, ws_assistant)

        ws_assistant.send.assert_called_once()

    @patch(
        "hummingbot.connector.derivative.extended_perpetual."
        "extended_perpetual_api_order_book_data_source."
        "ExtendedPerpetualAPIOrderBookDataSource._next_funding_time"
    )
    async def test_parse_funding_info_message(self, next_funding_time_mock):
        next_funding_time_mock.return_value = 1700700000

        raw_message = {
            "data": {
                "market": self.ex_trading_pair,
                "indexPrice": "2080.0",
                "markPrice": "2081.5",
                "fundingRate": "0.0001",
            }
        }
        message_queue = asyncio.Queue()

        await self.data_source._parse_funding_info_message(raw_message, message_queue)

        msg: FundingInfoUpdate = message_queue.get_nowait()
        self.assertEqual(self.trading_pair, msg.trading_pair)
        self.assertEqual(Decimal("2080.0"), msg.index_price)
        self.assertEqual(Decimal("2081.5"), msg.mark_price)
        self.assertEqual(Decimal("0.0001"), msg.rate)
        self.assertEqual(1700700000, msg.next_funding_utc_timestamp)

    async def test_parse_funding_info_message_with_short_keys(self):
        raw_message = {
            "data": {
                "m": self.ex_trading_pair,
                "ip": "2080.0",
                "mp": "2081.5",
                "fr": "0.0001",
            }
        }
        message_queue = asyncio.Queue()

        await self.data_source._parse_funding_info_message(raw_message, message_queue)

        msg: FundingInfoUpdate = message_queue.get_nowait()
        self.assertEqual(Decimal("2080.0"), msg.index_price)
        self.assertEqual(Decimal("2081.5"), msg.mark_price)
        self.assertEqual(Decimal("0.0001"), msg.rate)

    async def test_parse_funding_info_message_skips_unknown_market(self):
        raw_message = {
            "data": {
                "market": "UNKNOWN-PAIR",
                "indexPrice": "2080.0",
                "markPrice": "2081.5",
                "fundingRate": "0.0001",
            }
        }
        message_queue = asyncio.Queue()

        await self.data_source._parse_funding_info_message(raw_message, message_queue)

        self.assertTrue(message_queue.empty())

    async def test_next_funding_time_rounds_to_next_hour(self):
        with patch("time.time", return_value=1700687397.0):
            next_time = self.data_source._next_funding_time()
            expected_next_hour = int(((1700687397 // 3600) + 1) * 3600)
            self.assertEqual(expected_next_hour, next_time)

    async def test_listen_for_order_book_diffs_cancelled(self):
        mock_queue = AsyncMock()
        mock_queue.get.side_effect = asyncio.CancelledError()
        self.data_source._message_queue[self.data_source._diff_messages_queue_key] = mock_queue

        msg_queue: asyncio.Queue = asyncio.Queue()

        with self.assertRaises(asyncio.CancelledError):
            await self.data_source.listen_for_order_book_diffs(self.local_event_loop, msg_queue)

    async def test_listen_for_trades_cancelled(self):
        mock_queue = AsyncMock()
        mock_queue.get.side_effect = asyncio.CancelledError()
        self.data_source._message_queue[self.data_source._trade_messages_queue_key] = mock_queue

        msg_queue: asyncio.Queue = asyncio.Queue()

        with self.assertRaises(asyncio.CancelledError):
            await self.data_source.listen_for_trades(self.local_event_loop, msg_queue)

    async def test_listen_for_trades_successful(self):
        mock_queue = AsyncMock()
        trade_event = self.get_ws_trade_msg()
        mock_queue.get.side_effect = [trade_event, asyncio.CancelledError()]
        self.data_source._message_queue[self.data_source._trade_messages_queue_key] = mock_queue

        msg_queue: asyncio.Queue = asyncio.Queue()

        self.listening_task = self.local_event_loop.create_task(
            self.data_source.listen_for_trades(self.local_event_loop, msg_queue)
        )

        msg: OrderBookMessage = await msg_queue.get()

        self.assertEqual(OrderBookMessageType.TRADE, msg.type)
        self.assertEqual(12345, msg.trade_id)

    @aioresponses()
    async def test_listen_for_order_book_snapshots_successful(self, mock_api):
        msg_queue: asyncio.Queue = asyncio.Queue()
        url = web_utils.public_rest_url(
            CONSTANTS.ORDERBOOK_PATH.format(market=self.ex_trading_pair)
        )
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")

        resp = self.get_rest_snapshot_msg()
        mock_api.get(regex_url, body=json.dumps(resp))

        self.listening_task = self.local_event_loop.create_task(
            self.data_source.listen_for_order_book_snapshots(self.local_event_loop, msg_queue)
        )

        msg: OrderBookMessage = await msg_queue.get()

        self.assertEqual(OrderBookMessageType.SNAPSHOT, msg.type)
        self.assertEqual(4, len(msg.bids))
        self.assertEqual(4, len(msg.asks))

    @aioresponses()
    async def test_listen_for_order_book_snapshots_cancelled(self, mock_api):
        url = web_utils.public_rest_url(
            CONSTANTS.ORDERBOOK_PATH.format(market=self.ex_trading_pair)
        )
        regex_url = re.compile(f"^{url}".replace(".", r"\.").replace("?", r"\?") + ".*")

        mock_api.get(regex_url, exception=asyncio.CancelledError)

        with self.assertRaises(asyncio.CancelledError):
            await self.data_source.listen_for_order_book_snapshots(self.local_event_loop, asyncio.Queue())

    async def _simulate_trading_rules_initialized(self):
        self.connector._trading_rules = {
            self.trading_pair: TradingRule(
                trading_pair=self.trading_pair,
                min_order_size=Decimal(str(0.01)),
                min_price_increment=Decimal(str(0.0001)),
                min_base_amount_increment=Decimal(str(0.000001)),
            )
        }


class ExtendedPerpetualAPIOrderBookDataSourceWebSocketTests(IsolatedAsyncioWrapperTestCase):
    level = 0

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.base_asset = "ETH"
        cls.quote_asset = "USD"
        cls.trading_pair = f"{cls.base_asset}-{cls.quote_asset}"
        cls.ex_trading_pair = f"{cls.base_asset}-{cls.quote_asset}"

    def setUp(self) -> None:
        super().setUp()
        self.log_records = []

        client_config_map = ClientConfigAdapter(ClientConfigMap())
        self.connector = ExtendedPerpetualDerivative(
            client_config_map,
            extended_perpetual_api_key="test_api_key",
            extended_perpetual_stark_private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            extended_perpetual_stark_public_key="0x5d05989e9302dcebc74e241001e3e3ac3f4402ccf2f8e6f74b034b07ad6a904",
            extended_perpetual_vault_id=100,
            trading_pairs=[self.trading_pair],
        )
        self.data_source = ExtendedPerpetualAPIOrderBookDataSource(
            trading_pairs=[self.trading_pair],
            connector=self.connector,
            api_factory=self.connector._web_assistants_factory,
        )

        self.data_source.logger().setLevel(1)
        self.data_source.logger().addHandler(self)

        self.connector._set_trading_pair_symbol_map(
            bidict({f"{self.base_asset}-{self.quote_asset}": self.trading_pair}))

    def handle(self, record):
        self.log_records.append(record)

    def _is_logged(self, log_level: str, message: str) -> bool:
        return any(record.levelname == log_level and record.getMessage() == message
                   for record in self.log_records)

    async def test_subscribe_channels_raises_cancel_exception(self):
        mock_ws = MagicMock()
        mock_ws.send = AsyncMock(side_effect=asyncio.CancelledError)

        with self.assertRaises(asyncio.CancelledError):
            await self.data_source._subscribe_channels(mock_ws)

    async def test_subscribe_channels_raises_exception_and_logs_error(self):
        mock_ws = MagicMock()
        mock_ws.send = AsyncMock(side_effect=Exception("Test error"))

        with self.assertRaises(Exception):
            await self.data_source._subscribe_channels(mock_ws)

        self.assertTrue(
            self._is_logged(
                "ERROR",
                "Unexpected error occurred subscribing to order book data streams."
            )
        )
