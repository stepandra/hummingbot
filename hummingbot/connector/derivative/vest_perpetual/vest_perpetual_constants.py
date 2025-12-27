"""
Vest Perpetual API constants.
"""
from decimal import Decimal
from typing import Dict

from hummingbot.core.api_throttler.data_types import LinkedLimitWeightPair, RateLimit
from hummingbot.core.data_type.in_flight_order import OrderState

EXCHANGE_NAME = "vest_perpetual"
BROKER_ID = "HBOT"
MAX_ORDER_ID_LEN = None

MARKET_ORDER_SLIPPAGE = Decimal("0.05")

DOMAIN = EXCHANGE_NAME
DEFAULT_DOMAIN = DOMAIN
TESTNET_DOMAIN = f"{EXCHANGE_NAME}_testnet"

# Base URLs
REST_URL_PROD = "https://server-prod.hz.vestmarkets.com/v2"
REST_URL_DEV = "https://server-dev.hz.vestmarkets.com/v2"
WSS_URL_PROD = "wss://ws-prod.hz.vestmarkets.com/ws-api"
WSS_URL_DEV = "wss://ws-dev.hz.vestmarkets.com/ws-api"

REST_URLS = {
    DEFAULT_DOMAIN: REST_URL_PROD,
    TESTNET_DOMAIN: REST_URL_DEV,
    "mainnet": REST_URL_PROD,
    "testnet": REST_URL_DEV,
}

WSS_URLS = {
    DEFAULT_DOMAIN: WSS_URL_PROD,
    TESTNET_DOMAIN: WSS_URL_DEV,
    "mainnet": WSS_URL_PROD,
    "testnet": WSS_URL_DEV,
}

# Default to production
REST_URL = REST_URL_PROD
WSS_URL = WSS_URL_PROD

# Contract addresses
VERIFYING_CONTRACT_PROD = "0x919386306C47b2Fe1036e3B4F7C40D22D2461a23"
VERIFYING_CONTRACT_DEV = "0x8E4D87AEf4AC4D5415C35A12319013e34223825B"
VERIFYING_CONTRACT = VERIFYING_CONTRACT_PROD

# REST endpoints
REGISTER_PATH_URL = "/register"
EXCHANGE_INFO_PATH_URL = "/exchangeInfo"
TICKER_LATEST_PATH_URL = "/ticker/latest"
TICKER_24HR_PATH_URL = "/ticker/24hr"
FUNDING_HISTORY_PATH_URL = "/funding/history"
KLINES_PATH_URL = "/klines"
ACCOUNT_PATH_URL = "/account"
ACCOUNT_NONCE_PATH_URL = "/account/nonce"
ACCOUNT_LEVERAGE_PATH_URL = "/account/leverage"
ORDERS_PATH_URL = "/orders"
LP_PATH_URL = "/lp"
TRANSFER_WITHDRAW_PATH_URL = "/transfer/withdraw"
TRANSFER_PATH_URL = "/transfer"
LISTEN_KEY_PATH_URL = "/account/listenKey"

# WebSocket channels
WS_TICKERS_CHANNEL = "tickers"
WS_KLINE_CHANNEL = "{symbol}@kline_{interval}"
WS_DEPTH_CHANNEL = "{symbol}@depth"
WS_TRADES_CHANNEL = "{symbol}@trades"
WS_ACCOUNT_PRIVATE_CHANNEL = "account_private"

# WebSocket events
WS_EVENT_ORDER = "ORDER"
WS_EVENT_LP = "LP"
WS_EVENT_TRANSFER = "TRANSFER"

# Order types
ORDER_TYPE_MARKET = "MARKET"
ORDER_TYPE_LIMIT = "LIMIT"
ORDER_TYPE_STOP_LOSS = "STOP_LOSS"
ORDER_TYPE_TAKE_PROFIT = "TAKE_PROFIT"
ORDER_TYPE_LIQUIDATION = "LIQUIDATION"

# Order status
ORDER_STATUS_NEW = "NEW"
ORDER_STATUS_PARTIALLY_FILLED = "PARTIALLY_FILLED"
ORDER_STATUS_FILLED = "FILLED"
ORDER_STATUS_CANCELLED = "CANCELLED"
ORDER_STATUS_REJECTED = "REJECTED"

# Time in force
TIME_IN_FORCE_GTC = "GTC"
TIME_IN_FORCE_FOK = "FOK"

# Symbol status
SYMBOL_STATUS_TRADING = "TRADING"
SYMBOL_STATUS_HALT = "HALT"

# Heartbeat interval for WebSocket ping/pong (seconds)
HEARTBEAT_TIME_INTERVAL = 30.0

# Order state mapping (like Lighter)
ORDER_STATE: Dict[str, OrderState] = {
    "NEW": OrderState.OPEN,
    "new": OrderState.OPEN,
    "PENDING": OrderState.OPEN,
    "pending": OrderState.OPEN,
    "OPEN": OrderState.OPEN,
    "open": OrderState.OPEN,
    "PARTIALLY_FILLED": OrderState.PARTIALLY_FILLED,
    "partially_filled": OrderState.PARTIALLY_FILLED,
    "FILLED": OrderState.FILLED,
    "filled": OrderState.FILLED,
    "CANCELLED": OrderState.CANCELED,
    "CANCELED": OrderState.CANCELED,
    "cancelled": OrderState.CANCELED,
    "canceled": OrderState.CANCELED,
    "REJECTED": OrderState.FAILED,
    "rejected": OrderState.FAILED,
    "FAILED": OrderState.FAILED,
    "failed": OrderState.FAILED,
}

# Rate limits - using LinkedLimitWeightPair pattern like Lighter
REST_GLOBAL_LIMIT_ID = "vest_rest_global_limit"
REST_GLOBAL_LIMIT = 1200
RATE_LIMIT_INTERVAL = 60

# Endpoint weights for rate limiting
ENDPOINT_WEIGHTS: Dict[str, int] = {
    EXCHANGE_INFO_PATH_URL: 10,
    TICKER_LATEST_PATH_URL: 10,
    TICKER_24HR_PATH_URL: 10,
    FUNDING_HISTORY_PATH_URL: 10,
    KLINES_PATH_URL: 10,
    ACCOUNT_PATH_URL: 20,
    ACCOUNT_NONCE_PATH_URL: 20,
    ACCOUNT_LEVERAGE_PATH_URL: 20,
    ORDERS_PATH_URL: 10,
    LP_PATH_URL: 20,
    TRANSFER_WITHDRAW_PATH_URL: 50,
    TRANSFER_PATH_URL: 20,
    LISTEN_KEY_PATH_URL: 20,
    REGISTER_PATH_URL: 100,
}

RATE_LIMITS = [
    RateLimit(
        REST_GLOBAL_LIMIT_ID, limit=REST_GLOBAL_LIMIT, time_interval=RATE_LIMIT_INTERVAL
    ),
]

for endpoint, weight in ENDPOINT_WEIGHTS.items():
    per_route_limit = max(1, REST_GLOBAL_LIMIT // weight)
    RATE_LIMITS.append(
        RateLimit(
            limit_id=endpoint,
            limit=per_route_limit,
            time_interval=RATE_LIMIT_INTERVAL,
            linked_limits=[LinkedLimitWeightPair(REST_GLOBAL_LIMIT_ID, weight=weight)],
        )
    )

ORDER_NOT_EXIST_MESSAGE = "order"
UNKNOWN_ORDER_MESSAGE = "Order not found"
