"""Vest Perpetual Derivative connector implementation."""

import asyncio
import time
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from bidict import bidict

import hummingbot.connector.derivative.vest_perpetual.vest_perpetual_constants as CONSTANTS
import hummingbot.connector.derivative.vest_perpetual.vest_perpetual_web_utils as web_utils
from hummingbot.connector.derivative.perpetual_budget_checker import (
    PerpetualBudgetChecker,
)
from hummingbot.connector.derivative.position import Position
from hummingbot.connector.derivative.vest_perpetual.vest_perpetual_api_order_book_data_source import (
    VestPerpetualAPIOrderBookDataSource,
)
from hummingbot.connector.derivative.vest_perpetual.vest_perpetual_auth import (
    VestPerpetualAuth,
)
from hummingbot.connector.derivative.vest_perpetual.vest_perpetual_user_stream_data_source import (
    VestPerpetualUserStreamDataSource,
)
from hummingbot.connector.derivative.vest_perpetual.vest_perpetual_utils import (
    DEFAULT_FEES,
    convert_from_exchange_trading_pair,
    convert_to_exchange_trading_pair,
)
from hummingbot.connector.perpetual_derivative_py_base import PerpetualDerivativePyBase
from hummingbot.connector.trading_rule import TradingRule
from hummingbot.connector.utils import combine_to_hb_trading_pair
from hummingbot.core.api_throttler.data_types import RateLimit
from hummingbot.core.data_type.common import (
    OrderType,
    PositionAction,
    PositionMode,
    PositionSide,
    TradeType,
)
from hummingbot.core.data_type.in_flight_order import (
    InFlightOrder,
    OrderState,
    OrderUpdate,
    TradeUpdate,
)
from hummingbot.core.data_type.order_book_tracker_data_source import (
    OrderBookTrackerDataSource,
)
from hummingbot.core.data_type.trade_fee import (
    AddedToCostTradeFee,
    TokenAmount,
    TradeFeeBase,
)
from hummingbot.core.data_type.user_stream_tracker_data_source import (
    UserStreamTrackerDataSource,
)
from hummingbot.core.utils.async_utils import safe_gather
from hummingbot.core.utils.estimate_fee import build_trade_fee
from hummingbot.core.web_assistant.connections.data_types import RESTMethod, RESTRequest
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory


class VestPerpetualDerivative(PerpetualDerivativePyBase):
    """
    Vest Perpetual exchange connector.
    """

    web_utils = web_utils

    def __init__(
        self,
        vest_perpetual_api_key: str = None,
        vest_perpetual_signing_key: str = None,
        vest_perpetual_account_group: int = 0,
        vest_perpetual_use_testnet: bool = False,
        trading_pairs: Optional[List[str]] = None,
        trading_required: bool = True,
        domain: str = None,
        balance_asset_limit: Optional[Dict[str, Dict[str, Decimal]]] = None,
        rate_limits_share_pct: Decimal = Decimal("100"),
    ):
        self._api_key = vest_perpetual_api_key
        self._signing_key = vest_perpetual_signing_key
        self._account_group = vest_perpetual_account_group
        self._use_testnet = vest_perpetual_use_testnet
        self._trading_required = trading_required
        self._trading_pairs = trading_pairs
        self._domain = domain or (
            CONSTANTS.TESTNET_DOMAIN
            if vest_perpetual_use_testnet
            else CONSTANTS.DEFAULT_DOMAIN
        )
        self._last_trade_history_timestamp: Optional[float] = None

        super().__init__(balance_asset_limit, rate_limits_share_pct)

        self._position_mode = PositionMode.ONEWAY
        self._set_trading_pair_symbol_map(None)

    @property
    def name(self) -> str:
        return "vest_perpetual"

    @property
    def authenticator(self) -> VestPerpetualAuth:
        return VestPerpetualAuth(
            api_key=self._api_key,
            signing_private_key=self._signing_key,
            account_group=self._account_group,
        )

    @property
    def rate_limits_rules(self) -> List[RateLimit]:
        return CONSTANTS.RATE_LIMITS

    @property
    def domain(self) -> str:
        return self._domain

    @property
    def client_order_id_max_length(self) -> int:
        return -1

    @property
    def client_order_id_prefix(self) -> str:
        return ""

    @property
    def trading_rules_request_path(self) -> str:
        return CONSTANTS.EXCHANGE_INFO_PATH_URL

    @property
    def trading_pairs_request_path(self) -> str:
        return CONSTANTS.EXCHANGE_INFO_PATH_URL

    @property
    def check_network_request_path(self) -> str:
        return CONSTANTS.TICKER_LATEST_PATH_URL

    @property
    def trading_pairs(self) -> List[str]:
        return self._trading_pairs

    @property
    def is_cancel_request_in_exchange_synchronous(self) -> bool:
        return False

    @property
    def is_trading_required(self) -> bool:
        return self._trading_required

    @property
    def funding_fee_poll_interval(self) -> int:
        return 120

    def supported_order_types(self) -> List[OrderType]:
        return [OrderType.LIMIT, OrderType.MARKET]

    def supported_position_modes(self) -> List[PositionMode]:
        return [PositionMode.ONEWAY]

    def get_buy_collateral_token(self, trading_pair: str) -> str:
        return trading_pair.split("-")[1]

    def get_sell_collateral_token(self, trading_pair: str) -> str:
        return trading_pair.split("-")[1]

    def _is_request_exception_related_to_time_synchronizer(
        self, request_exception: Exception
    ) -> bool:
        return False

    def _is_order_not_found_during_status_update_error(
        self, status_update_exception: Exception
    ) -> bool:
        return False

    def _is_order_not_found_during_cancelation_error(
        self, cancelation_exception: Exception
    ) -> bool:
        return False

    @staticmethod
    def _safe_decimal(value: Any, default: Decimal) -> Decimal:
        """Converts any raw value to ``Decimal`` returning a fallback when conversion fails."""
        try:
            if value is None:
                raise InvalidOperation
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return default

    def _create_web_assistants_factory(self) -> WebAssistantsFactory:
        return web_utils.build_api_factory(
            throttler=self._throttler,
            auth=self._auth,
            use_testnet=self._use_testnet,
        )

    def _create_order_book_data_source(self) -> OrderBookTrackerDataSource:
        return VestPerpetualAPIOrderBookDataSource(
            trading_pairs=self._trading_pairs,
            connector=self,
            api_factory=self._web_assistants_factory,
            use_testnet=self._use_testnet,
        )

    def _create_user_stream_data_source(self) -> UserStreamTrackerDataSource:
        return VestPerpetualUserStreamDataSource(
            auth=self._auth,
            trading_pairs=self._trading_pairs or [],
            connector=self,
            api_factory=self._web_assistants_factory,
            domain=self._domain,
        )

    def _get_fee(
        self,
        base_currency: str,
        quote_currency: str,
        order_type: OrderType,
        order_side: TradeType,
        amount: Decimal,
        price: Decimal = Decimal("NaN"),
        is_maker: Optional[bool] = None,
    ) -> TradeFeeBase:
        is_maker = is_maker or (order_type is OrderType.LIMIT_MAKER)
        trading_pair = combine_to_hb_trading_pair(base_currency, quote_currency)
        if trading_pair in self._trading_fees:
            fees_data = self._trading_fees[trading_pair]
            fee_value = (
                Decimal(fees_data.maker) if is_maker else Decimal(fees_data.taker)
            )
        else:
            fee_value = Decimal("0.0001")  # Default 0.01%
        return build_trade_fee(
            exchange=self.name,
            is_maker=is_maker,
            base_currency=base_currency,
            quote_currency=quote_currency,
            order_type=order_type,
            order_side=order_side,
            amount=amount,
            price=price,
            fee_value=fee_value,
        )

    async def _place_order(
        self,
        order_id: str,
        trading_pair: str,
        amount: Decimal,
        trade_type: TradeType,
        order_type: OrderType,
        price: Decimal,
        position_action: PositionAction = PositionAction.NIL,
        **kwargs,
    ) -> Tuple[str, float]:
        """Place order on Vest exchange."""
        symbol = await self.exchange_symbol_associated_to_pair(
            trading_pair=trading_pair
        )

        # Current timestamp in milliseconds
        timestamp = int(time.time() * 1000)
        # Nonce - using timestamp as suggested by docs
        nonce = timestamp

        api_params = {
            "order": {
                "time": timestamp,
                "nonce": nonce,
                "symbol": symbol,
                "isBuy": trade_type == TradeType.BUY,
                "size": f"{amount:f}",
                "orderType": order_type.name,
                "limitPrice": f"{price:f}",
                "reduceOnly": position_action == PositionAction.CLOSE,
            }
        }

        try:
            order_result = await self._api_post(
                path_url=CONSTANTS.ORDERS_PATH_URL,
                data=api_params,
                is_auth_required=True,
            )
            # Response should contain the order ID or success status
            # Example response from docs is not explicitly given for success,
            # but we can assume standard structure or it returns the order object.
            # Based on Hyperliquid and others, usually returns an ID.
            # Vest docs "Example Payload for New Order" is likely the event, but maybe response too.

            exchange_order_id = str(order_result.get("id"))
            return exchange_order_id, float(timestamp) / 1000.0

        except Exception as e:
            raise IOError(f"Error submitting order {order_id}: {e}")

    async def _place_cancel(self, order_id: str, tracked_order: InFlightOrder):
        """Cancel order on Vest exchange via DELETE /orders with id parameter."""
        try:
            timestamp = int(time.time() * 1000)
            params = {
                "id": tracked_order.exchange_order_id,
                "time": timestamp,
            }

            cancel_result = await self._api_request(
                method=RESTMethod.DELETE,
                path_url=CONSTANTS.ORDERS_PATH_URL,
                params=params,
                is_auth_required=True,
            )

            if cancel_result.get("status") == "CANCELLED" or "id" in cancel_result:
                return True
            return False
        except Exception as e:
            self.logger().error(f"Error cancelling order {order_id}: {e}")
            return False

    async def _update_balances(self):
        """Update account balances."""
        local_asset_names = set(self._account_balances.keys())
        remote_asset_names = set()

        try:
            account_info = await self._api_request(
                method=RESTMethod.GET,
                path_url=CONSTANTS.ACCOUNT_PATH_URL,
                params={"time": int(time.time() * 1000)},
                is_auth_required=True,
            )

            # Balances
            balances = account_info.get("balances", [])

            if balances:
                for balance_entry in balances:
                    asset_name = balance_entry["asset"]
                    total_balance = Decimal(balance_entry["total"])
                    locked_balance = Decimal(balance_entry["locked"])
                    available_balance = total_balance - locked_balance

                    self._account_available_balances[asset_name] = available_balance
                    self._account_balances[asset_name] = total_balance
                    remote_asset_names.add(asset_name)
            else:
                # Fallback: Check for root level balance info (e.g. for USDC)
                # Vest API might return "withdrawable", "total", "locked" at root for the main collateral
                # We assume the asset is USDC or try to infer it, but typically it's USDC for Vest.
                # Let's look for "asset" field or default to "USDC" if withdrawable exists.
                withdrawable = account_info.get("withdrawable")
                total = account_info.get("total")  # totalMargin or total?

                if withdrawable is not None:
                    asset_name = account_info.get("asset", "USDC")
                    available_balance = Decimal(str(withdrawable))

                    # If total is not provided, we might have to approximate or use withdrawable + locked
                    # But let's try to find total or marginBalance
                    total_balance = (
                        Decimal(str(total)) if total is not None else available_balance
                    )

                    self._account_available_balances[asset_name] = available_balance
                    self._account_balances[asset_name] = total_balance
                    remote_asset_names.add(asset_name)

            # Positions
            positions = account_info.get("positions", [])
            for position_data in positions:
                symbol = position_data["symbol"]
                trading_pair = await self.trading_pair_associated_to_exchange_symbol(
                    symbol
                )

                if trading_pair in self.trading_pairs:
                    position_side = (
                        PositionSide.LONG
                        if position_data["isLong"]
                        else PositionSide.SHORT
                    )
                    unrealized_pnl = Decimal(position_data["unrealizedPnl"])
                    entry_price = Decimal(position_data["entryPrice"])
                    amount = Decimal(position_data["size"])
                    leverage = Decimal(
                        position_data["initMarginRatio"]
                    )  # Wait, initMarginRatio = 1/leverage usually.
                    # Docs say "leverages": [{"symbol": ..., "value": 20}] separately.
                    # But position object has "initMarginRatio".

                    # Let's try to get leverage from "leverages" list if available
                    leverages_list = account_info.get("leverages", [])
                    leverage_val = Decimal("1.0")
                    for lev in leverages_list:
                        if lev["symbol"] == symbol:
                            leverage_val = Decimal(str(lev["value"]))
                            break

                    position = Position(
                        trading_pair=trading_pair,
                        position_side=position_side,
                        unrealized_pnl=unrealized_pnl,
                        entry_price=entry_price,
                        amount=amount
                        * (
                            Decimal("1")
                            if position_side == PositionSide.LONG
                            else Decimal("-1")
                        ),
                        leverage=leverage_val,
                    )
                    self._perpetual_trading.set_position(
                        trading_pair=trading_pair, position=position
                    )

            self._last_balance_update_time = self.current_timestamp

        except Exception as e:
            self.logger().network(
                f"Error fetching account updates: {e}",
                app_warning_msg="Failed to fetch account updates.",
            )

    async def _all_trade_updates_for_order(
        self, order: InFlightOrder
    ) -> List[TradeUpdate]:
        """Get trade updates for an order.

        Vest does not provide a REST endpoint for fetching trades.
        Trade updates are received via WebSocket ORDER events with fill info.
        """
        return []

    async def _request_order_status(self, tracked_order: InFlightOrder) -> OrderUpdate:
        """Request order status from exchange.

        Vest does not provide a REST endpoint for querying individual order status.
        Order updates are received via WebSocket ORDER events.
        Return the current known state of the order.
        """
        return OrderUpdate(
            client_order_id=tracked_order.client_order_id,
            exchange_order_id=tracked_order.exchange_order_id,
            trading_pair=tracked_order.trading_pair,
            update_timestamp=self.current_timestamp,
            new_state=tracked_order.current_state,
        )

    async def _user_stream_event_listener(self):
        """Listen to user stream events."""
        async for event_message in self._iter_user_event_queue():
            try:
                channel = event_message.get("channel")
                data = event_message.get("data", {})

                if channel == "account_private":
                    event_type = data.get("event")
                    args = data.get("args", {})

                    if event_type == "ORDER":
                        await self._process_order_event(args)
                    elif event_type == "TRANSFER":
                        pass
                    elif event_type == "LP":
                        pass

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger().error(
                    f"Unexpected error in user stream listener: {e}", exc_info=True
                )

    async def _process_order_event(self, order_data: Dict[str, Any]):
        exchange_order_id = str(order_data.get("id"))
        status = order_data.get("status")

        # Find the order in in_flight_orders
        tracked_order = next(
            (
                o
                for o in self._perpetual_trading.in_flight_orders.values()
                if o.exchange_order_id == exchange_order_id
            ),
            None,
        )

        if not tracked_order:
            return

        order_update = OrderUpdate(
            trading_pair=tracked_order.trading_pair,
            update_timestamp=order_data.get("postTime", 0) / 1000.0,
            new_state=OrderState.OPEN,  # Default
            client_order_id=tracked_order.client_order_id,
            exchange_order_id=exchange_order_id,
        )

        if status == "NEW":
            order_update.new_state = OrderState.OPEN
            self._perpetual_trading.process_order_update(order_update)

        elif status == "FILLED" or status == "PARTIALLY_FILLED":
            if status == "FILLED":
                order_update.new_state = OrderState.FILLED
            else:
                order_update.new_state = OrderState.PARTIALLY_FILLED

            self._perpetual_trading.process_order_update(order_update)

            # Process trade fill
            # Vest "ORDER" event contains fill info
            fill_size = Decimal(order_data.get("lastFilledSize", "0"))
            fill_price = Decimal(order_data.get("lastFilledPrice", "0"))
            fee = Decimal(order_data.get("fees", "0"))

            if fill_size > 0:
                trade_fee = AddedToCostTradeFee(
                    percent_token=tracked_order.quote_asset,
                    flat_fees=[
                        TokenAmount(token=tracked_order.quote_asset, amount=fee)
                    ],
                )

                trade_update = TradeUpdate(
                    trade_id=f"{exchange_order_id}-{order_data.get('nonce', 0)}",  # Generating a pseudo trade ID
                    client_order_id=tracked_order.client_order_id,
                    exchange_order_id=exchange_order_id,
                    trading_pair=tracked_order.trading_pair,
                    fee=trade_fee,
                    fill_base_amount=fill_size,
                    fill_quote_amount=fill_size * fill_price,
                    fill_price=fill_price,
                    fill_timestamp=order_data.get("lastFilledTime", 0) / 1000.0,
                )
                self._perpetual_trading.process_trade_update(trade_update)

        elif status == "CANCELLED":
            order_update.new_state = OrderState.CANCELED
            self._perpetual_trading.process_order_update(order_update)

        elif status == "REJECTED":
            order_update.new_state = OrderState.FAILED
            self._perpetual_trading.process_order_update(order_update)

    async def _format_trading_rules(
        self, exchange_info_dict: Dict[str, Any]
    ) -> List[TradingRule]:
        trading_rules: List[TradingRule] = []
        symbols = (
            exchange_info_dict.get("symbols")
            if isinstance(exchange_info_dict, dict)
            else exchange_info_dict
        )
        symbols = symbols or []

        for symbol_info in symbols:
            symbol_name = (
                symbol_info.get("symbol") if isinstance(symbol_info, dict) else None
            )
            status = (
                symbol_info.get("status", CONSTANTS.SYMBOL_STATUS_TRADING)
                if isinstance(symbol_info, dict)
                else None
            )

            if symbol_name is None or status != CONSTANTS.SYMBOL_STATUS_TRADING:
                continue

            trading_pair = convert_from_exchange_trading_pair(symbol_name)
            if self._trading_pairs and trading_pair not in self._trading_pairs:
                continue

            filters = {
                flt.get("filterType"): flt
                for flt in symbol_info.get("filters", [])
                if isinstance(flt, dict) and flt.get("filterType")
            }

            min_qty = self._safe_decimal(
                symbol_info.get("minQty")
                or symbol_info.get("minOrderSize")
                or filters.get("LOT_SIZE", {}).get("minQty"),
                Decimal("0.0001"),
            )
            max_qty = self._safe_decimal(
                symbol_info.get("maxQty") or filters.get("LOT_SIZE", {}).get("maxQty"),
                Decimal("1E6"),
            )
            step_size = self._safe_decimal(
                symbol_info.get("stepSize")
                or symbol_info.get("quantityPrecision")
                or filters.get("LOT_SIZE", {}).get("stepSize"),
                min_qty,
            )
            tick_size = self._safe_decimal(
                symbol_info.get("tickSize")
                or symbol_info.get("priceTickSize")
                or filters.get("PRICE_FILTER", {}).get("tickSize"),
                Decimal("0.0001"),
            )
            min_notional = self._safe_decimal(
                symbol_info.get("minNotional")
                or filters.get("NOTIONAL", {}).get("minNotional"),
                Decimal("0"),
            )
            price_precision = self._safe_decimal(
                symbol_info.get("pricePrecision"), Decimal("18")
            )
            quote_increment = tick_size * step_size if step_size > 0 else tick_size

            order_types = symbol_info.get("orderTypes", [])
            supports_limit = (
                not order_types or CONSTANTS.ORDER_TYPE_LIMIT in order_types
            )
            supports_market = (
                not order_types or CONSTANTS.ORDER_TYPE_MARKET in order_types
            )

            collateral_token = (
                symbol_info.get("quoteAsset") or trading_pair.split("-")[1]
            )

            trading_rules.append(
                TradingRule(
                    trading_pair=trading_pair,
                    min_order_size=min_qty,
                    max_order_size=max_qty,
                    min_price_increment=tick_size,
                    min_base_amount_increment=step_size,
                    min_quote_amount_increment=quote_increment,
                    min_notional_size=min_notional,
                    max_price_significant_digits=price_precision,
                    supports_limit_orders=supports_limit,
                    supports_market_orders=supports_market,
                    buy_order_collateral_token=collateral_token,
                    sell_order_collateral_token=collateral_token,
                )
            )

        return trading_rules

    def _initialize_trading_pair_symbols_from_exchange_info(
        self, exchange_info: Dict[str, Any]
    ):
        symbols = (
            exchange_info.get("symbols")
            if isinstance(exchange_info, dict)
            else exchange_info
        )
        symbols = symbols or []

        self.logger().warning(
            f"Initializing trading pairs from {len(symbols)} symbols. Instance ID: {id(self)}"
        )

        mapping: Dict[str, str] = {}
        for symbol_info in symbols:
            if not isinstance(symbol_info, dict):
                continue
            symbol_name = symbol_info.get("symbol")
            if not symbol_name:
                continue
            trading_pair = convert_from_exchange_trading_pair(symbol_name)
            if trading_pair:
                mapping[trading_pair] = symbol_name
                if "BTC" in trading_pair:
                    self.logger().warning(f"Mapped {symbol_name} -> {trading_pair}")

        self._set_trading_pair_symbol_map(mapping)
        self.logger().warning(f"Total mapped pairs: {len(mapping)}")
        if "BTC-PERP" not in mapping:
            self.logger().error("BTC-PERP missing from mapping!")
        else:
            self.logger().warning("BTC-PERP successfully mapped.")

        if not mapping and self._trading_pairs:
            mapping = {
                tp: convert_to_exchange_trading_pair(tp) for tp in self._trading_pairs
            }

        self._trading_pair_symbol_map = bidict(mapping)

    def _set_trading_pair_symbol_map(self, trading_pairs: Optional[List[str]]):
        """Set up the trading pair to exchange symbol mapping."""
        if trading_pairs is not None:
            self._trading_pair_symbol_map = bidict(
                {tp: convert_to_exchange_trading_pair(tp) for tp in trading_pairs}
            )
        else:
            self._trading_pair_symbol_map = bidict()

    async def _update_trading_fees(self):
        """Assigns a default fee schema for each tracked trading pair."""
        for trading_pair in self.trading_pairs or []:
            self._trading_fees[trading_pair] = deepcopy(DEFAULT_FEES)

    async def _update_positions(self):
        """Clears locally cached positions when the exchange does not provide an endpoint yet."""
        position_keys = list(self._perpetual_trading.account_positions.keys())
        for key in position_keys:
            self._perpetual_trading.remove_position(key)

    async def _set_trading_pair_leverage(
        self, trading_pair: str, leverage: int
    ) -> Tuple[bool, str]:
        if leverage < 1:
            return False, "Leverage must be greater than or equal to 1."
        return True, ""

    async def _trading_pair_position_mode_set(
        self, mode: PositionMode, trading_pair: str
    ) -> Tuple[bool, str]:
        if mode == PositionMode.ONEWAY:
            return True, ""
        return False, "Vest Perpetual currently supports only the ONEWAY position mode."

    async def _fetch_last_fee_payment(
        self, trading_pair: str
    ) -> Tuple[float, Decimal, Decimal]:
        return 0.0, Decimal("-1"), Decimal("-1")

    async def _api_request(self, *args, **kwargs):
        path_url = kwargs.get("path_url")
        if not path_url and len(args) > 1:
            path_url = args[1]

        self.logger().warning(f"API Request: {path_url}")
        try:
            return await super()._api_request(*args, **kwargs)
        except Exception as e:
            self.logger().error(f"API Request failed: {path_url} - {e}")
            raise

    async def exchange_symbol_associated_to_pair(self, trading_pair: str) -> str:
        if trading_pair in self._trading_pair_symbol_map:
            return self._trading_pair_symbol_map[trading_pair]

        # Fallback: try to update trading rules if map is empty or key missing
        self.logger().warning(
            f"Trading pair {trading_pair} not found in map (size: {len(self._trading_pair_symbol_map)}). Fetching trading rules..."
        )
        try:
            await self._update_trading_rules()
        except Exception as e:
            self.logger().error(f"Failed to update trading rules during fallback: {e}")

        if trading_pair in self._trading_pair_symbol_map:
            self.logger().info(f"Successfully mapped {trading_pair} after fallback.")
            return self._trading_pair_symbol_map[trading_pair]

        raise KeyError(trading_pair)

    async def get_last_traded_prices(
        self, trading_pairs: List[str] = None
    ) -> Dict[str, float]:
        try:
            return await self._get_last_traded_prices(trading_pairs)
        except Exception:
            self.logger().network(
                "Error fetching last traded prices.",
                exc_info=True,
                app_warning_msg="Could not fetch last traded prices.",
            )
            return {}

    async def _get_last_traded_prices(
        self, trading_pairs: List[str] = None
    ) -> Dict[str, float]:
        res = await self._api_request(
            method=RESTMethod.GET, path_url=CONSTANTS.TICKER_LATEST_PATH_URL
        )

        tickers = res.get("tickers", [])

        results = {}
        for ticker in tickers:
            symbol = ticker.get("symbol")
            last_price = ticker.get("lastPrice")
            if symbol and last_price:
                try:
                    trading_pair = (
                        await self.trading_pair_associated_to_exchange_symbol(symbol)
                    )
                    if trading_pairs is None or trading_pair in trading_pairs:
                        results[trading_pair] = float(last_price)
                except KeyError:
                    continue

        return results
