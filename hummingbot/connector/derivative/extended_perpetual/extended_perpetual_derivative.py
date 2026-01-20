"""Extended Perpetual Derivative Exchange Connector."""
import asyncio
import hashlib
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from hummingbot.connector.derivative.extended_perpetual import (
    extended_perpetual_constants as CONSTANTS,
    extended_perpetual_web_utils as web_utils,
)
from hummingbot.connector.derivative.extended_perpetual.extended_perpetual_api_order_book_data_source import (
    ExtendedPerpetualAPIOrderBookDataSource,
)
from hummingbot.connector.derivative.extended_perpetual.extended_perpetual_api_user_stream_data_source import (
    ExtendedPerpetualAPIUserStreamDataSource,
)
from hummingbot.connector.derivative.extended_perpetual.extended_perpetual_auth import ExtendedPerpetualAuth
from hummingbot.connector.derivative.extended_perpetual.extended_perpetual_signer import ExtendedPerpetualSigner
from hummingbot.connector.derivative.position import Position
from hummingbot.connector.perpetual_derivative_py_base import PerpetualDerivativePyBase
from hummingbot.connector.trading_rule import TradingRule
from hummingbot.connector.utils import combine_to_hb_trading_pair
from hummingbot.core.api_throttler.data_types import RateLimit
from hummingbot.core.data_type.common import OrderType, PositionAction, PositionMode, PositionSide, TradeType
from hummingbot.core.data_type.in_flight_order import InFlightOrder, OrderState, OrderUpdate, TradeUpdate
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.data_type.trade_fee import TokenAmount, TradeFeeBase
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.utils.async_utils import safe_ensure_future
from hummingbot.core.web_assistant.connections.data_types import RESTMethod
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory

s_decimal_NaN = Decimal("nan")


class ExtendedPerpetualDerivative(PerpetualDerivativePyBase):
    """Extended Perpetual derivative exchange connector for Hummingbot."""

    web_utils = web_utils

    SHORT_POLL_INTERVAL = 5.0
    LONG_POLL_INTERVAL = 12.0
    MARKET_ORDER_SLIPPAGE = Decimal("0.0075")  # 0.75% slippage for market orders

    def __init__(
        self,
        client_config_map: "ClientConfigAdapter",  # noqa: F821
        extended_perpetual_api_key: str,
        extended_perpetual_stark_private_key: str,
        extended_perpetual_stark_public_key: str,
        extended_perpetual_vault_id: int,
        trading_pairs: Optional[List[str]] = None,
        trading_required: bool = True,
        domain: str = CONSTANTS.DEFAULT_DOMAIN,
    ):
        self._api_key = extended_perpetual_api_key
        self._stark_private_key = extended_perpetual_stark_private_key
        self._stark_public_key = extended_perpetual_stark_public_key
        self._vault_id = extended_perpetual_vault_id
        self._trading_required = trading_required
        self._trading_pairs = trading_pairs
        self._domain = domain
        self._is_testnet = domain != CONSTANTS.DEFAULT_DOMAIN
        self._position_mode = PositionMode.ONEWAY
        self._last_trade_history_timestamp = None
        
        # Market info cache
        self._market_info: Dict[str, Any] = {}
        self._fee_rates: Dict[str, Decimal] = {}
        
        # Initialize signer
        self._signer = ExtendedPerpetualSigner(
            private_key=self._stark_private_key,
            public_key=self._stark_public_key,
            vault_id=self._vault_id,
            is_testnet=self._is_testnet,
        )
        
        super().__init__(client_config_map)

    @property
    def name(self) -> str:
        return "extended_perpetual" if not self._is_testnet else "extended_perpetual_testnet"

    @property
    def authenticator(self) -> Optional[ExtendedPerpetualAuth]:
        if self._trading_required:
            return ExtendedPerpetualAuth(
                api_key=self._api_key,
                stark_private_key=self._stark_private_key,
                stark_public_key=self._stark_public_key,
                vault_id=self._vault_id,
                is_testnet=self._is_testnet,
            )
        return None

    @property
    def rate_limits_rules(self) -> List[RateLimit]:
        return CONSTANTS.RATE_LIMITS

    @property
    def domain(self) -> str:
        return self._domain

    @property
    def client_order_id_max_length(self) -> int:
        return CONSTANTS.MAX_ORDER_ID_LEN

    @property
    def client_order_id_prefix(self) -> str:
        return CONSTANTS.HBOT_ORDER_ID_PREFIX

    @property
    def trading_rules_request_path(self) -> str:
        return CONSTANTS.MARKETS_PATH

    @property
    def trading_pairs_request_path(self) -> str:
        return CONSTANTS.MARKETS_PATH

    @property
    def check_network_request_path(self) -> str:
        return CONSTANTS.MARKETS_PATH

    @property
    def supported_order_types(self) -> List[OrderType]:
        return [OrderType.LIMIT, OrderType.LIMIT_MAKER, OrderType.MARKET]

    @property
    def supported_position_modes(self) -> List[PositionMode]:
        return [PositionMode.ONEWAY]

    @property
    def funding_fee_poll_interval(self) -> int:
        return 3600  # 1 hour, funding is applied hourly

    @property
    def trading_pairs(self) -> List[str]:
        return self._trading_pairs or []

    @property
    def is_trading_required(self) -> bool:
        return self._trading_required

    @property
    def is_cancel_request_in_exchange_synchronous(self) -> bool:
        return True

    def get_buy_collateral_token(self, trading_pair: str) -> str:
        return "USDC"

    def get_sell_collateral_token(self, trading_pair: str) -> str:
        return "USDC"

    def _is_request_exception_related_to_time_synchronizer(self, request_exception: Exception) -> bool:
        return False

    def _is_order_not_found_during_status_update_error(self, status_update_exception: Exception) -> bool:
        error_msg = str(status_update_exception).lower()
        return "not found" in error_msg or "order does not exist" in error_msg

    def _is_order_not_found_during_cancelation_error(self, cancelation_exception: Exception) -> bool:
        error_msg = str(cancelation_exception).lower()
        return "not found" in error_msg or "order does not exist" in error_msg

    async def _trading_pair_position_mode_set(
        self, mode: PositionMode, trading_pair: str
    ) -> Tuple[bool, str]:
        return True, ""

    async def _set_trading_pair_leverage(
        self, trading_pair: str, leverage: int
    ) -> Tuple[bool, str]:
        return True, ""

    async def _fetch_last_fee_payment(
        self, trading_pair: str
    ) -> Tuple[float, Decimal, Decimal]:
        return 0.0, Decimal("0"), Decimal("0")

    async def _update_trading_fees(self):
        await self._fetch_fees()

    async def _initialize_trading_pair_symbols_from_exchange_info(self, exchange_info: Dict[str, Any]) -> Dict[str, str]:
        mapping = {}
        markets_data = exchange_info.get("data", [])
        for market in markets_data:
            trading_pair = market.get("name", "")
            if trading_pair:
                mapping[trading_pair] = trading_pair
        return mapping

    def _create_web_assistants_factory(self) -> WebAssistantsFactory:
        return web_utils.build_api_factory(
            throttler=self._throttler,
            auth=self._auth,
        )

    def _create_order_book_data_source(self) -> OrderBookTrackerDataSource:
        return ExtendedPerpetualAPIOrderBookDataSource(
            trading_pairs=self._trading_pairs,
            connector=self,
            api_factory=self._web_assistants_factory,
            domain=self._domain,
        )

    def _create_user_stream_data_source(self) -> UserStreamTrackerDataSource:
        return ExtendedPerpetualAPIUserStreamDataSource(
            auth=self._auth,
            trading_pairs=self._trading_pairs,
            connector=self,
            api_factory=self._web_assistants_factory,
            domain=self._domain,
        )

    def _get_fee(self, base_currency: str, quote_currency: str, order_type: OrderType, order_side: TradeType,
                 amount: Decimal, price: Decimal = s_decimal_NaN,
                 is_maker: Optional[bool] = None) -> TradeFeeBase:
        is_maker = is_maker or order_type is OrderType.LIMIT_MAKER
        trading_pair = combine_to_hb_trading_pair(base=base_currency, quote=quote_currency)
        
        if is_maker:
            fee_rate = self._fee_rates.get("maker", Decimal("0.0002"))  # Default 0.02%
        else:
            fee_rate = self._fee_rates.get("taker", Decimal("0.0005"))  # Default 0.05%
        
        return TradeFeeBase.new_perpetual_fee(
            fee_schema=self.trade_fee_schema(),
            position_action=PositionAction.OPEN,
            percent=fee_rate,
            percent_token=quote_currency,
        )

    async def _update_trading_rules(self):
        """Fetch and update trading rules from exchange."""
        exchange_info = await self._api_get(
            path_url=CONSTANTS.MARKETS_PATH,
            params={},
            is_auth_required=False,
        )
        trading_rules = await self._format_trading_rules(exchange_info)
        self._trading_rules.clear()
        for trading_rule in trading_rules:
            self._trading_rules[trading_rule.trading_pair] = trading_rule

    async def _format_trading_rules(self, exchange_info: Dict[str, Any]) -> List[TradingRule]:
        """Parse exchange info into trading rules."""
        trading_rules = []
        
        if exchange_info.get("status") != "OK":
            self.logger().error(f"Error fetching trading rules: {exchange_info}")
            return trading_rules
        
        markets_data = exchange_info.get("data", [])
        
        for market in markets_data:
            try:
                trading_pair = market["name"]  # e.g., "ETH-USD"
                trading_config = market.get("tradingConfig", {})
                
                # Store market info for order signing
                self._market_info[trading_pair] = market
                
                min_order_size = Decimal(str(trading_config.get("minOrderSize", "0.001")))
                min_size_change = Decimal(str(trading_config.get("minOrderSizeChange", "0.001")))
                min_price_change = Decimal(str(trading_config.get("minPriceChange", "0.01")))
                
                trading_rules.append(
                    TradingRule(
                        trading_pair=trading_pair,
                        min_order_size=min_order_size,
                        min_base_amount_increment=min_size_change,
                        min_price_increment=min_price_change,
                        buy_order_collateral_token="USDC",
                        sell_order_collateral_token="USDC",
                    )
                )
            except Exception as e:
                self.logger().error(f"Error parsing trading rule for {market}: {e}", exc_info=True)
        
        return trading_rules

    async def _update_balances(self):
        """Fetch and update account balances."""
        try:
            balance_response = await self._api_get(
                path_url=CONSTANTS.BALANCE_PATH,
                params={},
                is_auth_required=True,
            )
            
            if balance_response.get("status") == "OK":
                balance_data = balance_response.get("data", {})
                quote_asset = balance_data.get("collateralName", "USDC")
                
                total_balance = Decimal(str(balance_data.get("equity", "0")))
                available_balance = Decimal(str(balance_data.get("availableForTrade", "0")))
                
                self._account_balances[quote_asset] = total_balance
                self._account_available_balances[quote_asset] = available_balance
            else:
                self.logger().error(f"Error updating balances: {balance_response}")
        except Exception as e:
            self.logger().error(f"Error updating balances: {e}", exc_info=True)

    async def _update_positions(self):
        """Fetch and update open positions."""
        try:
            positions_response = await self._api_get(
                path_url=CONSTANTS.POSITIONS_PATH,
                params={},
                is_auth_required=True,
            )
            
            if positions_response.get("status") == "OK":
                positions_data = positions_response.get("data", [])
                
                for pos_data in positions_data:
                    trading_pair = pos_data.get("market")
                    side_str = pos_data.get("side", "").upper()
                    position_side = PositionSide.LONG if side_str == "LONG" else PositionSide.SHORT
                    
                    amount = abs(Decimal(str(pos_data.get("size", "0"))))
                    if amount == 0:
                        continue
                    
                    entry_price = Decimal(str(pos_data.get("openPrice", "0")))
                    leverage = Decimal(str(pos_data.get("leverage", "1")))
                    unrealized_pnl = Decimal(str(pos_data.get("unrealisedPnl", "0")))
                    
                    pos_key = self._perpetual_trading.position_key(trading_pair, position_side)
                    position = Position(
                        trading_pair=trading_pair,
                        position_side=position_side,
                        unrealized_pnl=unrealized_pnl,
                        entry_price=entry_price,
                        amount=amount,
                        leverage=leverage,
                    )
                    self._perpetual_trading.set_position(pos_key, position)
                
                # Clear positions that are no longer open
                current_pairs = {pos.get("market") for pos in positions_data}
                for pos_key in list(self._perpetual_trading.account_positions.keys()):
                    if pos_key[0] not in current_pairs:
                        self._perpetual_trading.remove_position(pos_key)
            else:
                self.logger().error(f"Error updating positions: {positions_response}")
        except Exception as e:
            self.logger().error(f"Error updating positions: {e}", exc_info=True)

    async def _fetch_fees(self):
        """Fetch current fee rates."""
        try:
            fees_response = await self._api_get(
                path_url=CONSTANTS.FEES_PATH,
                params={},
                is_auth_required=True,
            )
            
            if fees_response.get("status") == "OK":
                fees_data = fees_response.get("data", {})
                self._fee_rates["maker"] = Decimal(str(fees_data.get("makerFee", "0.0002")))
                self._fee_rates["taker"] = Decimal(str(fees_data.get("takerFee", "0.0005")))
        except Exception as e:
            self.logger().warning(f"Error fetching fees, using defaults: {e}")

    def buy(
        self,
        trading_pair: str,
        amount: Decimal,
        order_type: OrderType = OrderType.LIMIT,
        price: Decimal = s_decimal_NaN,
        **kwargs,
    ) -> str:
        """Create a buy order."""
        order_id = self._generate_order_id(is_buy=True, trading_pair=trading_pair)
        
        if order_type is OrderType.MARKET:
            price = self._get_market_order_price(trading_pair, is_buy=True)
        
        safe_ensure_future(
            self._create_order(
                trade_type=TradeType.BUY,
                order_id=order_id,
                trading_pair=trading_pair,
                amount=amount,
                order_type=order_type,
                price=price,
                **kwargs,
            )
        )
        return order_id

    def sell(
        self,
        trading_pair: str,
        amount: Decimal,
        order_type: OrderType = OrderType.LIMIT,
        price: Decimal = s_decimal_NaN,
        **kwargs,
    ) -> str:
        """Create a sell order."""
        order_id = self._generate_order_id(is_buy=False, trading_pair=trading_pair)
        
        if order_type is OrderType.MARKET:
            price = self._get_market_order_price(trading_pair, is_buy=False)
        
        safe_ensure_future(
            self._create_order(
                trade_type=TradeType.SELL,
                order_id=order_id,
                trading_pair=trading_pair,
                amount=amount,
                order_type=order_type,
                price=price,
                **kwargs,
            )
        )
        return order_id

    def _generate_order_id(self, is_buy: bool, trading_pair: str) -> str:
        """Generate unique client order ID."""
        side = "B" if is_buy else "S"
        timestamp = int(time.time() * 1000)
        raw_id = f"{self.client_order_id_prefix}-{side}-{trading_pair}-{timestamp}"
        
        # Create MD5 hash for shorter ID
        md5 = hashlib.md5()
        md5.update(raw_id.encode("utf-8"))
        return f"{self.client_order_id_prefix}{md5.hexdigest()[:24]}"

    def _get_market_order_price(self, trading_pair: str, is_buy: bool) -> Decimal:
        """Calculate aggressive price for market order emulation."""
        order_book = self.get_order_book(trading_pair)
        
        if is_buy:
            best_ask = Decimal(str(order_book.get_price(True)))
            return best_ask * (Decimal("1") + self.MARKET_ORDER_SLIPPAGE)
        else:
            best_bid = Decimal(str(order_book.get_price(False)))
            return best_bid * (Decimal("1") - self.MARKET_ORDER_SLIPPAGE)

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
        """Place an order on the exchange."""
        # Get market info for signing
        market_info = self._market_info.get(trading_pair, {})
        if not market_info:
            await self._update_trading_rules()
            market_info = self._market_info.get(trading_pair, {})
        
        # Determine order parameters
        side = "buy" if trade_type is TradeType.BUY else "sell"
        order_type_str = "limit"
        time_in_force = "GTT"
        post_only = False
        reduce_only = position_action == PositionAction.CLOSE
        
        if order_type is OrderType.LIMIT_MAKER:
            post_only = True
        elif order_type is OrderType.MARKET:
            time_in_force = "IOC"
        
        # Calculate expiration (default 1 day, max 90 days mainnet / 28 days testnet)
        max_days = CONSTANTS.ORDER_EXPIRY_TESTNET_MAX_DAYS if self._is_testnet else CONSTANTS.ORDER_EXPIRY_MAINNET_MAX_DAYS
        expiry_days = min(1, max_days)
        expiry_ms = int((time.time() + expiry_days * 86400) * 1000)
        
        # Get fee rate
        fee_rate = self._fee_rates.get("maker" if post_only else "taker", Decimal("0.0005"))
        
        # Build settlement with Stark signature
        # Get asset info from market config
        synthetic_asset_id = market_info.get("syntheticAssetId", "0x0")
        collateral_asset_id = market_info.get("collateralAssetId", "0x0")
        synthetic_resolution = int(market_info.get("syntheticResolution", 1000000))
        collateral_resolution = int(market_info.get("collateralResolution", 1000000))
        
        settlement = self._signer.build_order_settlement(
            side=side,
            synthetic_amount=amount,
            price=price,
            synthetic_asset_id=synthetic_asset_id,
            collateral_asset_id=collateral_asset_id,
            synthetic_resolution=synthetic_resolution,
            collateral_resolution=collateral_resolution,
            max_fee_rate=fee_rate,
            expiration_ms=expiry_ms,
        )
        
        # Build order payload
        order_payload = {
            "id": order_id,
            "market": trading_pair,
            "type": order_type_str,
            "side": side,
            "qty": str(amount),
            "price": str(price),
            "timeInForce": time_in_force,
            "expiryEpochMillis": expiry_ms,
            "fee": str(fee_rate),
            "reduceOnly": reduce_only,
            "postOnly": post_only,
            "settlement": self._signer.to_settlement_dict(settlement),
        }
        
        # Submit order
        response = await self._api_post(
            path_url=CONSTANTS.CREATE_ORDER_PATH,
            data=order_payload,
            is_auth_required=True,
        )
        
        if response.get("status") == "ERROR":
            error_msg = response.get("error", "Unknown error")
            raise IOError(f"Error placing order {order_id}: {error_msg}")
        
        # Extract exchange order ID
        order_data = response.get("data", {})
        exchange_order_id = str(order_data.get("id", order_id))
        
        return exchange_order_id, self.current_timestamp

    async def _place_cancel(self, order_id: str, tracked_order: InFlightOrder) -> bool:
        """Cancel an order on the exchange."""
        try:
            # Cancel by external ID (client order ID)
            response = await self._api_delete(
                path_url=CONSTANTS.CANCEL_ORDER_BY_EXTERNAL_ID_PATH,
                params={"externalId": order_id},
                is_auth_required=True,
            )
            
            if response.get("status") == "OK":
                return True
            else:
                self.logger().warning(f"Cancel order {order_id} failed: {response}")
                return False
        except Exception as e:
            self.logger().error(f"Error canceling order {order_id}: {e}", exc_info=True)
            return False

    async def cancel_all(self, timeout_seconds: float) -> List[Dict[str, Any]]:
        """Cancel all open orders."""
        cancellation_results = []
        
        try:
            # Use mass cancel endpoint
            response = await self._api_post(
                path_url=CONSTANTS.MASS_CANCEL_PATH,
                data={"cancelAll": True},
                is_auth_required=True,
            )
            
            if response.get("status") == "OK":
                for order in self._order_tracker.active_orders.values():
                    cancellation_results.append({
                        "order_id": order.client_order_id,
                        "success": True,
                    })
            else:
                for order in self._order_tracker.active_orders.values():
                    cancellation_results.append({
                        "order_id": order.client_order_id,
                        "success": False,
                    })
        except Exception as e:
            self.logger().error(f"Error in cancel_all: {e}", exc_info=True)
            for order in self._order_tracker.active_orders.values():
                cancellation_results.append({
                    "order_id": order.client_order_id,
                    "success": False,
                })
        
        return cancellation_results

    async def _set_trading_pair_leverage(self, trading_pair: str, leverage: int) -> Tuple[bool, str]:
        """Set leverage for a trading pair."""
        try:
            response = await self._api_request(
                method="PATCH",
                path_url=CONSTANTS.LEVERAGE_PATH,
                data={"market": trading_pair, "leverage": str(leverage)},
                is_auth_required=True,
            )
            
            if response.get("status") == "OK":
                return True, ""
            else:
                error_msg = response.get("error", "Failed to set leverage")
                return False, error_msg
        except Exception as e:
            return False, str(e)

    async def _fetch_last_fee_payment(self, trading_pair: str) -> Tuple[int, Decimal, Decimal]:
        """Fetch last funding payment for a trading pair."""
        try:
            response = await self._api_get(
                path_url=CONSTANTS.FUNDING_HISTORY_PATH,
                params={"market": trading_pair},
                is_auth_required=True,
            )
            
            if response.get("status") == "OK":
                funding_data = response.get("data", [])
                if funding_data:
                    last_payment = funding_data[0]
                    timestamp = int(last_payment.get("time", 0))
                    funding_rate = Decimal(str(last_payment.get("fundingRate", "0")))
                    payment = Decimal(str(last_payment.get("payment", "0")))
                    return timestamp, funding_rate, payment
            
            return 0, Decimal("-1"), Decimal("-1")
        except Exception as e:
            self.logger().warning(f"Error fetching funding payment: {e}")
            return 0, Decimal("-1"), Decimal("-1")

    async def _user_stream_event_listener(self):
        """Listen and process user stream events."""
        async for event_message in self._iter_user_event_queue():
            try:
                if isinstance(event_message, dict):
                    # Process orders updates
                    if "orders" in event_message:
                        for order_data in event_message["orders"]:
                            self._process_order_update(order_data)
                    
                    # Process trades updates
                    if "trades" in event_message:
                        for trade_data in event_message["trades"]:
                            await self._process_trade_update(trade_data)
                    
                    # Process balance updates
                    if "balance" in event_message:
                        self._process_balance_update(event_message["balance"])
                    
                    # Process position updates
                    if "positions" in event_message:
                        self._process_position_updates(event_message["positions"])
            
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger().error(f"Error processing user stream event: {e}", exc_info=True)
                await self._sleep(5.0)

    def _process_order_update(self, order_data: Dict[str, Any]):
        """Process order status update from WebSocket."""
        client_order_id = order_data.get("externalId", "")
        tracked_order = self._order_tracker.all_updatable_orders.get(client_order_id)
        
        if not tracked_order:
            return
        
        status = order_data.get("status", "").lower()
        new_state = CONSTANTS.ORDER_STATE.get(status, OrderState.OPEN)
        
        order_update = OrderUpdate(
            trading_pair=tracked_order.trading_pair,
            update_timestamp=order_data.get("updatedTime", 0) / 1000,
            new_state=new_state,
            client_order_id=client_order_id,
            exchange_order_id=str(order_data.get("id", "")),
        )
        
        self._order_tracker.process_order_update(order_update)

    async def _process_trade_update(self, trade_data: Dict[str, Any]):
        """Process trade fill update from WebSocket."""
        exchange_order_id = str(trade_data.get("orderId", ""))
        client_order_id = trade_data.get("externalOrderId", "")
        
        tracked_order = self._order_tracker.all_fillable_orders.get(client_order_id)
        if not tracked_order:
            tracked_order = self._order_tracker.all_fillable_orders_by_exchange_order_id.get(exchange_order_id)
        
        if not tracked_order:
            return
        
        fee_asset = tracked_order.quote_asset
        fee_amount = Decimal(str(trade_data.get("fee", "0")))
        
        fee = TradeFeeBase.new_perpetual_fee(
            fee_schema=self.trade_fee_schema(),
            position_action=PositionAction.OPEN,
            percent_token=fee_asset,
            flat_fees=[TokenAmount(amount=fee_amount, token=fee_asset)],
        )
        
        trade_update = TradeUpdate(
            trade_id=str(trade_data.get("id", "")),
            client_order_id=tracked_order.client_order_id,
            exchange_order_id=exchange_order_id,
            trading_pair=tracked_order.trading_pair,
            fill_timestamp=trade_data.get("createdTime", 0) / 1000,
            fill_price=Decimal(str(trade_data.get("averagePrice", "0"))),
            fill_base_amount=Decimal(str(trade_data.get("filledQty", "0"))),
            fill_quote_amount=Decimal(str(trade_data.get("value", "0"))),
            fee=fee,
        )
        
        self._order_tracker.process_trade_update(trade_update)

    def _process_balance_update(self, balance_data: Dict[str, Any]):
        """Process balance update from WebSocket."""
        quote_asset = balance_data.get("collateralName", "USDC")
        total_balance = Decimal(str(balance_data.get("equity", "0")))
        available_balance = Decimal(str(balance_data.get("availableForTrade", "0")))
        
        self._account_balances[quote_asset] = total_balance
        self._account_available_balances[quote_asset] = available_balance

    def _process_position_updates(self, positions_data: List[Dict[str, Any]]):
        """Process position updates from WebSocket."""
        for pos_data in positions_data:
            trading_pair = pos_data.get("market")
            side_str = pos_data.get("side", "").upper()
            position_side = PositionSide.LONG if side_str == "LONG" else PositionSide.SHORT
            
            amount = abs(Decimal(str(pos_data.get("size", "0"))))
            pos_key = self._perpetual_trading.position_key(trading_pair, position_side)
            
            if amount == 0:
                self._perpetual_trading.remove_position(pos_key)
            else:
                entry_price = Decimal(str(pos_data.get("openPrice", "0")))
                leverage = Decimal(str(pos_data.get("leverage", "1")))
                unrealized_pnl = Decimal(str(pos_data.get("unrealisedPnl", "0")))
                
                position = Position(
                    trading_pair=trading_pair,
                    position_side=position_side,
                    unrealized_pnl=unrealized_pnl,
                    entry_price=entry_price,
                    amount=amount,
                    leverage=leverage,
                )
                self._perpetual_trading.set_position(pos_key, position)

    async def _request_order_status(self, tracked_order: InFlightOrder) -> OrderUpdate:
        """Request current order status from exchange."""
        try:
            response = await self._api_get(
                path_url=f"{CONSTANTS.OPEN_ORDERS_PATH}/{tracked_order.exchange_order_id}",
                params={},
                is_auth_required=True,
                throttler_limit_id=CONSTANTS.OPEN_ORDERS_PATH,
            )
            
            if response.get("status") == "OK":
                order_data = response.get("data", {})
                status = order_data.get("status", "").lower()
                new_state = CONSTANTS.ORDER_STATE.get(status, OrderState.OPEN)
                
                return OrderUpdate(
                    trading_pair=tracked_order.trading_pair,
                    update_timestamp=order_data.get("updatedTime", 0) / 1000,
                    new_state=new_state,
                    client_order_id=tracked_order.client_order_id,
                    exchange_order_id=str(order_data.get("id", "")),
                )
        except Exception as e:
            self.logger().warning(f"Error requesting order status: {e}")
        
        return OrderUpdate(
            trading_pair=tracked_order.trading_pair,
            update_timestamp=self.current_timestamp,
            new_state=tracked_order.current_state,
            client_order_id=tracked_order.client_order_id,
            exchange_order_id=tracked_order.exchange_order_id,
        )

    async def _all_trade_updates_for_order(self, order: InFlightOrder) -> List[TradeUpdate]:
        """Fetch all trade updates for an order."""
        trade_updates = []
        
        try:
            response = await self._api_get(
                path_url=CONSTANTS.TRADES_PATH,
                params={"externalId": order.client_order_id},
                is_auth_required=True,
            )
            
            if response.get("status") == "OK":
                trades_data = response.get("data", [])
                for trade_data in trades_data:
                    fee_asset = order.quote_asset
                    fee_amount = Decimal(str(trade_data.get("fee", "0")))
                    
                    fee = TradeFeeBase.new_perpetual_fee(
                        fee_schema=self.trade_fee_schema(),
                        position_action=PositionAction.OPEN,
                        percent_token=fee_asset,
                        flat_fees=[TokenAmount(amount=fee_amount, token=fee_asset)],
                    )
                    
                    trade_update = TradeUpdate(
                        trade_id=str(trade_data.get("id", "")),
                        client_order_id=order.client_order_id,
                        exchange_order_id=str(trade_data.get("orderId", "")),
                        trading_pair=order.trading_pair,
                        fill_timestamp=trade_data.get("createdTime", 0) / 1000,
                        fill_price=Decimal(str(trade_data.get("averagePrice", "0"))),
                        fill_base_amount=Decimal(str(trade_data.get("filledQty", "0"))),
                        fill_quote_amount=Decimal(str(trade_data.get("value", "0"))),
                        fee=fee,
                    )
                    trade_updates.append(trade_update)
        except Exception as e:
            self.logger().warning(f"Error fetching trade updates: {e}")
        
        return trade_updates

    async def _api_get(self, path_url: str, params: Dict = None, is_auth_required: bool = False, throttler_limit_id: str = None) -> Dict[str, Any]:
        """Make GET request to API."""
        rest_assistant = await self._web_assistants_factory.get_rest_assistant()
        url = web_utils.public_rest_url(path_url, self._domain) if not is_auth_required else web_utils.private_rest_url(path_url, self._domain)
        
        response = await rest_assistant.execute_request(
            url=url,
            params=params or {},
            method=RESTMethod.GET,
            is_auth_required=is_auth_required,
            throttler_limit_id=throttler_limit_id or path_url,
        )
        return response

    async def _api_post(self, path_url: str, data: Dict = None, is_auth_required: bool = False) -> Dict[str, Any]:
        """Make POST request to API."""
        rest_assistant = await self._web_assistants_factory.get_rest_assistant()
        url = web_utils.private_rest_url(path_url, self._domain)
        
        response = await rest_assistant.execute_request(
            url=url,
            data=data or {},
            method=RESTMethod.POST,
            is_auth_required=is_auth_required,
            throttler_limit_id=path_url,
        )
        return response

    async def _api_delete(self, path_url: str, params: Dict = None, is_auth_required: bool = False, throttler_limit_id: str = None) -> Dict[str, Any]:
        """Make DELETE request to API."""
        rest_assistant = await self._web_assistants_factory.get_rest_assistant()
        url = web_utils.private_rest_url(path_url, self._domain)
        
        response = await rest_assistant.execute_request(
            url=url,
            params=params or {},
            method=RESTMethod.DELETE,
            is_auth_required=is_auth_required,
            throttler_limit_id=throttler_limit_id or path_url,
        )
        return response

    async def _api_request(
        self, method: RESTMethod, path_url: str, data: Dict = None, params: Dict = None, is_auth_required: bool = False
    ) -> Dict[str, Any]:
        """Make arbitrary HTTP request to API."""
        rest_assistant = await self._web_assistants_factory.get_rest_assistant()
        url = web_utils.private_rest_url(path_url, self._domain)
        
        response = await rest_assistant.execute_request(
            url=url,
            data=data,
            params=params or {},
            method=method,
            is_auth_required=is_auth_required,
            throttler_limit_id=path_url,
        )
        return response
