from hummingbot.core.api_throttler.data_types import LinkedLimitWeightPair, RateLimit
from hummingbot.core.data_type.in_flight_order import OrderState

EXCHANGE_NAME = "extended_perpetual"
DEFAULT_DOMAIN = "starknet"
TESTNET_DOMAIN = "extended_perpetual_testnet"

HBOT_ORDER_ID_PREFIX = "HBOT"
MAX_ORDER_ID_LEN = 32

MARKET_ORDER_SLIPPAGE = 0.05

REST_URL = "https://api.starknet.extended.exchange"
WSS_URL = "wss://api.starknet.extended.exchange"

TESTNET_REST_URL = "https://api.testnet.extended.exchange"
TESTNET_WSS_URL = "wss://api.testnet.extended.exchange"

CURRENCY = "USD"

FUNDING_RATE_UPDATE_INTERNAL_SECOND = 60

MARKETS_PATH = "/api/v1/info/markets"
ORDERBOOK_PATH = "/api/v1/info/markets/{market}/orderbook"
MARKET_STATS_PATH = "/api/v1/info/markets/{market}/stats"
PUBLIC_TRADES_PATH = "/api/v1/info/markets/{market}/trades"

BALANCE_PATH = "/api/v1/user/balance"
POSITIONS_PATH = "/api/v1/user/positions"
OPEN_ORDERS_PATH = "/api/v1/user/orders"
ORDER_HISTORY_PATH = "/api/v1/user/orders/history"
TRADES_PATH = "/api/v1/user/trades"
CREATE_ORDER_PATH = "/api/v1/user/order"
CANCEL_ORDER_PATH = "/api/v1/user/order/{id}"
CANCEL_ORDER_BY_EXTERNAL_ID_PATH = "/api/v1/user/order"
MASS_CANCEL_PATH = "/api/v1/user/order/massCancel"
LEVERAGE_PATH = "/api/v1/user/leverage"
FUNDING_HISTORY_PATH = "/api/v1/user/funding/history"
ACCOUNT_PATH = "/api/v1/user/account"
FEES_PATH = "/api/v1/user/fees"
PING_PATH = "/api/v1/info/ping"

WS_ORDERBOOK_PATH = "/stream.extended.exchange/v1/orderbooks/{market}"
WS_TRADES_PATH = "/stream.extended.exchange/v1/publicTrades/{market}"
WS_FUNDING_PATH = "/stream.extended.exchange/v1/funding/{market}"
WS_ACCOUNT_PATH = "/stream.extended.exchange/v1/account"

API_KEY_HEADER = "X-Api-Key"
USER_AGENT_HEADER = "User-Agent"
DEFAULT_USER_AGENT = "hummingbot/1.0"

ORDER_STATE = {
    "new": OrderState.OPEN,
    "NEW": OrderState.OPEN,
    "partially filled": OrderState.PARTIALLY_FILLED,
    "PARTIALLY_FILLED": OrderState.PARTIALLY_FILLED,
    "untriggered": OrderState.OPEN,
    "UNTRIGGERED": OrderState.OPEN,
    "filled": OrderState.FILLED,
    "FILLED": OrderState.FILLED,
    "cancelled": OrderState.CANCELED,
    "CANCELLED": OrderState.CANCELED,
    "rejected": OrderState.FAILED,
    "REJECTED": OrderState.FAILED,
    "expired": OrderState.CANCELED,
    "EXPIRED": OrderState.CANCELED,
}

PING_INTERVAL = 15
PONG_TIMEOUT = 10
ORDER_EXPIRY_MAINNET_MAX_DAYS = 90
ORDER_EXPIRY_TESTNET_MAX_DAYS = 28

HEARTBEAT_TIME_INTERVAL = 30.0

MAX_REQUEST = 1200
ONE_MINUTE = 60
ALL_ENDPOINTS_LIMIT = "All"

RATE_LIMITS = [
    RateLimit(ALL_ENDPOINTS_LIMIT, limit=MAX_REQUEST, time_interval=ONE_MINUTE),
    RateLimit(limit_id=MARKETS_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=ORDERBOOK_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=MARKET_STATS_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=PUBLIC_TRADES_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=BALANCE_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=POSITIONS_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=OPEN_ORDERS_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=ORDER_HISTORY_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=TRADES_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=CREATE_ORDER_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=CANCEL_ORDER_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=CANCEL_ORDER_BY_EXTERNAL_ID_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=MASS_CANCEL_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=LEVERAGE_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=FUNDING_HISTORY_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=ACCOUNT_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=FEES_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
    RateLimit(limit_id=PING_PATH, limit=MAX_REQUEST, time_interval=ONE_MINUTE,
              linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)]),
]

ORDER_NOT_EXIST_MESSAGE = "order"
UNKNOWN_ORDER_MESSAGE = "Order was never placed, already canceled, or filled"
