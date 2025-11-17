from hummingbot.core.api_throttler.data_types import LinkedLimitWeightPair, RateLimit
from hummingbot.core.data_type.in_flight_order import OrderState

EXCHANGE_NAME = "vest_perpetual"
MAX_ORDER_ID_LEN = None

DEFAULT_DOMAIN = "vest_perpetual"
TESTNET_DOMAIN = "vest_perpetual_testnet"

# REST base URLs
PERPETUAL_BASE_URL = "https://server-prod.hz.vestmarkets.com/v2"
TESTNET_BASE_URL = "https://server-dev.hz.vestmarkets.com/v2"

# WebSocket URLs
PERPETUAL_WS_URL = "wss://ws-prod.hz.vestmarkets.com/ws-api"
TESTNET_WS_URL = "wss://ws-dev.hz.vestmarkets.com/ws-api"

# REST API endpoints
EXCHANGE_INFO_PATH = "/exchangeInfo"
DEPTH_PATH = "/depth"
TICKER_LATEST_PATH = "/ticker/latest"
TICKER_24HR_PATH = "/ticker/24hr"
FUNDING_HISTORY_PATH = "/funding/history"
ACCOUNT_PATH = "/account"
ACCOUNT_NONCE_PATH = "/account/nonce"
ACCOUNT_LEVERAGE_PATH = "/account/leverage"
ORDERS_PATH = "/orders"
ORDERS_CANCEL_PATH = "/orders/cancel"
LP_PATH = "/lp"
LP_QUERY_PATH = "/lp"
TRANSFER_WITHDRAW_PATH = "/transfer/withdraw"
TRANSFER_QUERY_PATH = "/transfer"
LISTEN_KEY_PATH = "/account/listenKey"

# WebSocket channels
WS_ORDERBOOK_DEPTH_CHANNEL = "{symbol}@depth"
WS_TRADES_CHANNEL = "{symbol}@trades"
WS_KLINE_CHANNEL = "{symbol}@kline_{interval}"
WS_ACCOUNT_PRIVATE_CHANNEL = "account_private"

# Order states mapping
ORDER_STATE = {
    "NEW": OrderState.OPEN,
    "PARTIALLY_FILLED": OrderState.PARTIALLY_FILLED,
    "FILLED": OrderState.FILLED,
    "CANCELED": OrderState.CANCELED,
    "PENDING_CANCEL": OrderState.PENDING_CANCEL,
    "REJECTED": OrderState.FAILED,
    "EXPIRED": OrderState.CANCELED,
}

# Funding rate update interval
FUNDING_RATE_UPDATE_INTERVAL_SECONDS = 60

# Heartbeat interval
HEARTBEAT_TIME_INTERVAL = 30.0

# Rate limits (conservative estimates as Vest docs don't specify exact limits)
MAX_REQUEST_PER_MINUTE = 600
ALL_ENDPOINTS_LIMIT = "All"

RATE_LIMITS = [
    RateLimit(ALL_ENDPOINTS_LIMIT, limit=MAX_REQUEST_PER_MINUTE, time_interval=60),

    # Public endpoints
    RateLimit(limit_id=EXCHANGE_INFO_PATH, limit=MAX_REQUEST_PER_MINUTE, time_interval=60,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=DEPTH_PATH, limit=MAX_REQUEST_PER_MINUTE, time_interval=60,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=TICKER_LATEST_PATH, limit=MAX_REQUEST_PER_MINUTE, time_interval=60,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=TICKER_24HR_PATH, limit=MAX_REQUEST_PER_MINUTE, time_interval=60,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=FUNDING_HISTORY_PATH, limit=MAX_REQUEST_PER_MINUTE, time_interval=60,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),

    # Private endpoints
    RateLimit(limit_id=ACCOUNT_PATH, limit=MAX_REQUEST_PER_MINUTE, time_interval=60,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=ACCOUNT_NONCE_PATH, limit=MAX_REQUEST_PER_MINUTE, time_interval=60,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=ACCOUNT_LEVERAGE_PATH, limit=MAX_REQUEST_PER_MINUTE, time_interval=60,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=ORDERS_PATH, limit=MAX_REQUEST_PER_MINUTE, time_interval=60,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=ORDERS_CANCEL_PATH, limit=MAX_REQUEST_PER_MINUTE, time_interval=60,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=LP_PATH, limit=MAX_REQUEST_PER_MINUTE, time_interval=60,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=LP_QUERY_PATH, limit=MAX_REQUEST_PER_MINUTE, time_interval=60,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=TRANSFER_WITHDRAW_PATH, limit=MAX_REQUEST_PER_MINUTE, time_interval=60,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=TRANSFER_QUERY_PATH, limit=MAX_REQUEST_PER_MINUTE, time_interval=60,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=LISTEN_KEY_PATH, limit=MAX_REQUEST_PER_MINUTE, time_interval=60,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
]

# Error messages
ORDER_NOT_EXIST_MESSAGE = "Order does not exist"
UNKNOWN_ORDER_MESSAGE = "Order was never placed, already canceled, or filled"
