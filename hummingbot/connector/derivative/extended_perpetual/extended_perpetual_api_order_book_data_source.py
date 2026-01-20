import asyncio
import sys
import time
from collections import defaultdict
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import hummingbot.connector.derivative.extended_perpetual.extended_perpetual_constants as CONSTANTS
import hummingbot.connector.derivative.extended_perpetual.extended_perpetual_web_utils as web_utils
from hummingbot.core.data_type.common import TradeType
from hummingbot.core.data_type.funding_info import FundingInfo, FundingInfoUpdate
from hummingbot.core.data_type.order_book_message import OrderBookMessage, OrderBookMessageType
from hummingbot.core.data_type.perpetual_api_order_book_data_source import PerpetualAPIOrderBookDataSource
from hummingbot.core.utils.tracking_nonce import NonceCreator
from hummingbot.core.web_assistant.connections.data_types import RESTMethod, WSJSONRequest
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.web_assistant.ws_assistant import WSAssistant
from hummingbot.logger import HummingbotLogger

if TYPE_CHECKING:
    from hummingbot.connector.derivative.extended_perpetual.extended_perpetual_derivative import (
        ExtendedPerpetualDerivative,
    )


class ExtendedPerpetualAPIOrderBookDataSource(PerpetualAPIOrderBookDataSource):
    FULL_ORDER_BOOK_RESET_DELTA_SECONDS = sys.maxsize

    _logger: Optional[HummingbotLogger] = None

    def __init__(
            self,
            trading_pairs: List[str],
            connector: 'ExtendedPerpetualDerivative',
            api_factory: WebAssistantsFactory,
            domain: str = CONSTANTS.DEFAULT_DOMAIN
    ):
        super().__init__(trading_pairs)
        self._connector = connector
        self._api_factory = api_factory
        self._domain = domain
        self._trading_pairs: List[str] = trading_pairs
        self._message_queue: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._nonce_provider = NonceCreator.for_microseconds()
        self._last_sequence: Dict[str, int] = {}
        self._snapshot_messages_queue_key = "order_book_snapshot"
        self._diff_messages_queue_key = "order_book_diff"
        self._trade_messages_queue_key = "trade"
        self._funding_info_messages_queue_key = "funding_info"

    async def get_last_traded_prices(
            self,
            trading_pairs: List[str],
            domain: Optional[str] = None
    ) -> Dict[str, float]:
        return await self._connector.get_last_traded_prices(trading_pairs=trading_pairs)

    async def get_funding_info(self, trading_pair: str) -> FundingInfo:
        ex_trading_pair = await self._connector.exchange_symbol_associated_to_pair(trading_pair=trading_pair)
        stats = await self._request_market_stats(ex_trading_pair)

        funding_info = FundingInfo(
            trading_pair=trading_pair,
            index_price=Decimal(str(stats.get("indexPrice", "0"))),
            mark_price=Decimal(str(stats.get("markPrice", "0"))),
            next_funding_utc_timestamp=self._next_funding_time(),
            rate=Decimal(str(stats.get("fundingRate", "0"))),
        )
        return funding_info

    async def listen_for_funding_info(self, output: asyncio.Queue):
        while True:
            try:
                for trading_pair in self._trading_pairs:
                    funding_info = await self.get_funding_info(trading_pair)
                    funding_info_update = FundingInfoUpdate(
                        trading_pair=trading_pair,
                        index_price=funding_info.index_price,
                        mark_price=funding_info.mark_price,
                        next_funding_utc_timestamp=funding_info.next_funding_utc_timestamp,
                        rate=funding_info.rate,
                    )
                    output.put_nowait(funding_info_update)
                await self._sleep(CONSTANTS.FUNDING_RATE_UPDATE_INTERNAL_SECOND)
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().exception("Unexpected error when processing public funding info updates from exchange")
                await self._sleep(CONSTANTS.FUNDING_RATE_UPDATE_INTERNAL_SECOND)

    async def _request_market_stats(self, market: str) -> Dict[str, Any]:
        rest_assistant = await self._api_factory.get_rest_assistant()
        url = web_utils.public_rest_url(
            path_url=CONSTANTS.MARKET_STATS_PATH.format(market=market),
            domain=self._domain
        )
        data = await rest_assistant.execute_request(
            url=url,
            throttler_limit_id=CONSTANTS.MARKET_STATS_PATH,
            method=RESTMethod.GET,
        )
        return data.get("data", {}) if data.get("status") == "OK" else {}

    async def _request_order_book_snapshot(self, trading_pair: str) -> Dict[str, Any]:
        ex_trading_pair = await self._connector.exchange_symbol_associated_to_pair(trading_pair=trading_pair)
        rest_assistant = await self._api_factory.get_rest_assistant()
        url = web_utils.public_rest_url(
            path_url=CONSTANTS.ORDERBOOK_PATH.format(market=ex_trading_pair),
            domain=self._domain
        )
        data = await rest_assistant.execute_request(
            url=url,
            throttler_limit_id=CONSTANTS.ORDERBOOK_PATH,
            method=RESTMethod.GET,
        )
        return data

    async def _order_book_snapshot(self, trading_pair: str) -> OrderBookMessage:
        snapshot_response = await self._request_order_book_snapshot(trading_pair)
        timestamp = time.time()
        update_id = self._nonce_provider.get_tracking_nonce(timestamp=timestamp)

        ob_data = snapshot_response.get("data", {})
        bids = [[float(level["price"]), float(level["qty"])] for level in ob_data.get("bid", [])]
        asks = [[float(level["price"]), float(level["qty"])] for level in ob_data.get("ask", [])]

        snapshot_msg: OrderBookMessage = OrderBookMessage(
            OrderBookMessageType.SNAPSHOT,
            {
                "trading_pair": trading_pair,
                "update_id": update_id,
                "bids": bids,
                "asks": asks,
            },
            timestamp=timestamp
        )
        return snapshot_msg

    async def _connected_websocket_assistant(self) -> WSAssistant:
        ws: WSAssistant = await self._api_factory.get_ws_assistant()
        await ws.connect(
            ws_url=web_utils.wss_url(domain=self._domain),
            ping_timeout=CONSTANTS.HEARTBEAT_TIME_INTERVAL
        )
        return ws

    async def _subscribe_channels(self, ws: WSAssistant):
        try:
            for trading_pair in self._trading_pairs:
                ex_trading_pair = await self._connector.exchange_symbol_associated_to_pair(
                    trading_pair=trading_pair
                )

                orderbook_ws_url = web_utils.wss_url(
                    path_url=CONSTANTS.WS_ORDERBOOK_PATH.format(market=ex_trading_pair),
                    domain=self._domain
                )
                trades_ws_url = web_utils.wss_url(
                    path_url=CONSTANTS.WS_TRADES_PATH.format(market=ex_trading_pair),
                    domain=self._domain
                )
                funding_ws_url = web_utils.wss_url(
                    path_url=CONSTANTS.WS_FUNDING_PATH.format(market=ex_trading_pair),
                    domain=self._domain
                )

                subscribe_orderbook_request = WSJSONRequest(
                    payload={
                        "action": "subscribe",
                        "channel": "orderbook",
                        "market": ex_trading_pair,
                    }
                )
                subscribe_trades_request = WSJSONRequest(
                    payload={
                        "action": "subscribe",
                        "channel": "publicTrades",
                        "market": ex_trading_pair,
                    }
                )
                subscribe_funding_request = WSJSONRequest(
                    payload={
                        "action": "subscribe",
                        "channel": "funding",
                        "market": ex_trading_pair,
                    }
                )

                await ws.send(subscribe_orderbook_request)
                await ws.send(subscribe_trades_request)
                await ws.send(subscribe_funding_request)

                self._last_sequence[ex_trading_pair] = 0

            self.logger().info("Subscribed to public order book, trade, and funding channels...")
        except asyncio.CancelledError:
            raise
        except Exception:
            self.logger().exception("Unexpected error occurred subscribing to order book data streams.")
            raise

    def _channel_originating_message(self, event_message: Dict[str, Any]) -> str:
        channel = ""
        if event_message.get("type") == "pong":
            return channel

        msg_type = event_message.get("type", "")
        data = event_message.get("data", {})

        if msg_type in ("SNAPSHOT", "DELTA"):
            if data.get("t") == "SNAPSHOT":
                channel = self._snapshot_messages_queue_key
            else:
                channel = self._diff_messages_queue_key
        elif "tT" in str(data) or (isinstance(data, list) and len(data) > 0 and "tT" in data[0]):
            channel = self._trade_messages_queue_key
        elif "fundingRate" in str(data):
            channel = self._funding_info_messages_queue_key

        return channel

    async def _process_message_for_unknown_channel(
            self,
            event_message: Dict[str, Any],
            websocket_assistant: WSAssistant
    ):
        if event_message.get("type") == "ping":
            pong_request = WSJSONRequest(payload={"type": "pong"})
            await websocket_assistant.send(pong_request)

    async def _parse_order_book_snapshot_message(
            self,
            raw_message: Dict[str, Any],
            message_queue: asyncio.Queue
    ):
        data = raw_message.get("data", {})
        timestamp_ms = raw_message.get("ts", int(time.time() * 1000))
        timestamp = timestamp_ms * 1e-3
        seq = raw_message.get("seq", 0)

        market = data.get("m", "")
        trading_pair = await self._connector.trading_pair_associated_to_exchange_symbol(market)

        self._last_sequence[market] = seq

        bids = [[float(level["p"]), float(level["q"])] for level in data.get("b", [])]
        asks = [[float(level["p"]), float(level["q"])] for level in data.get("a", [])]

        update_id = self._nonce_provider.get_tracking_nonce(timestamp=timestamp)

        order_book_message = OrderBookMessage(
            OrderBookMessageType.SNAPSHOT,
            {
                "trading_pair": trading_pair,
                "update_id": update_id,
                "bids": bids,
                "asks": asks,
            },
            timestamp=timestamp
        )
        message_queue.put_nowait(order_book_message)

    async def _parse_order_book_diff_message(
            self,
            raw_message: Dict[str, Any],
            message_queue: asyncio.Queue
    ):
        data = raw_message.get("data", {})
        timestamp_ms = raw_message.get("ts", int(time.time() * 1000))
        timestamp = timestamp_ms * 1e-3
        seq = raw_message.get("seq", 0)

        market = data.get("m", "")
        trading_pair = await self._connector.trading_pair_associated_to_exchange_symbol(market)

        expected_seq = self._last_sequence.get(market, 0) + 1
        if seq != expected_seq:
            self.logger().warning(
                f"Sequence gap detected for {market}. Expected {expected_seq}, got {seq}. "
                "Requesting snapshot..."
            )
            await self._request_and_queue_snapshot(trading_pair, message_queue)
            return

        self._last_sequence[market] = seq

        bids = [[float(level["p"]), float(level["q"])] for level in data.get("b", [])]
        asks = [[float(level["p"]), float(level["q"])] for level in data.get("a", [])]

        update_id = self._nonce_provider.get_tracking_nonce(timestamp=timestamp)

        order_book_message = OrderBookMessage(
            OrderBookMessageType.DIFF,
            {
                "trading_pair": trading_pair,
                "update_id": update_id,
                "bids": bids,
                "asks": asks,
            },
            timestamp=timestamp
        )
        message_queue.put_nowait(order_book_message)

    async def _request_and_queue_snapshot(
            self,
            trading_pair: str,
            message_queue: asyncio.Queue
    ):
        try:
            snapshot_msg = await self._order_book_snapshot(trading_pair)
            message_queue.put_nowait(snapshot_msg)
            ex_trading_pair = await self._connector.exchange_symbol_associated_to_pair(trading_pair)
            self._last_sequence[ex_trading_pair] = 0
        except Exception:
            self.logger().exception(f"Error fetching snapshot for {trading_pair}")

    async def _parse_trade_message(
            self,
            raw_message: Dict[str, Any],
            message_queue: asyncio.Queue
    ):
        timestamp_ms = raw_message.get("ts", int(time.time() * 1000))
        data = raw_message.get("data", [])

        if not isinstance(data, list):
            data = [data]

        for trade_data in data:
            if trade_data.get("tT") != "TRADE":
                continue

            market = trade_data.get("m", "")
            trading_pair = await self._connector.trading_pair_associated_to_exchange_symbol(market)

            trade_side = trade_data.get("S", "BUY")
            trade_type = float(TradeType.BUY.value) if trade_side == "BUY" else float(TradeType.SELL.value)

            trade_timestamp_ms = trade_data.get("T", timestamp_ms)
            trade_timestamp = trade_timestamp_ms * 1e-3

            trade_message = OrderBookMessage(
                OrderBookMessageType.TRADE,
                {
                    "trading_pair": trading_pair,
                    "trade_type": trade_type,
                    "trade_id": trade_data.get("i", int(trade_timestamp_ms)),
                    "price": float(trade_data.get("p", "0")),
                    "amount": float(trade_data.get("q", "0")),
                },
                timestamp=trade_timestamp
            )
            message_queue.put_nowait(trade_message)

    async def _parse_funding_info_message(
            self,
            raw_message: Dict[str, Any],
            message_queue: asyncio.Queue
    ):
        data = raw_message.get("data", {})

        market = data.get("market", data.get("m", ""))
        if not market:
            return

        try:
            trading_pair = await self._connector.trading_pair_associated_to_exchange_symbol(market)
        except KeyError:
            return

        if trading_pair not in self._trading_pairs:
            return

        funding_info_update = FundingInfoUpdate(
            trading_pair=trading_pair,
            index_price=Decimal(str(data.get("indexPrice", data.get("ip", "0")))),
            mark_price=Decimal(str(data.get("markPrice", data.get("mp", "0")))),
            next_funding_utc_timestamp=self._next_funding_time(),
            rate=Decimal(str(data.get("fundingRate", data.get("fr", "0")))),
        )
        message_queue.put_nowait(funding_info_update)

    def _next_funding_time(self) -> int:
        return int(((time.time() // 3600) + 1) * 3600)
