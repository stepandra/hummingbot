from typing import Any, Dict

# A single source of truth for constant variables related to the exchange
from hummingbot.core.api_throttler.data_types import LinkedLimitWeightPair, RateLimit
from hummingbot.core.data_type.in_flight_order import OrderState

# The max size of a digest is 66 characters (Nado uses digests comparable to client order id).
MAX_ORDER_ID_LEN = 66

HEARTBEAT_TIME_INTERVAL = 30.0

ORDER_BOOK_DEPTH = 100

VERSION = "0.0.1"

EXCHANGE_NAME = "nado"

DEFAULT_DOMAIN = "nado"
TESTNET_DOMAIN = "nado_testnet"

QUOTE = "USDT0"

BASE_URLS = {
    DEFAULT_DOMAIN: "https://gateway.prod.nado.xyz/v1",
    TESTNET_DOMAIN: "https://gateway.test.nado.xyz/v1",
}

WSS_URLS = {
    DEFAULT_DOMAIN: "wss://gateway.prod.nado.xyz/v1/ws",
    TESTNET_DOMAIN: "wss://gateway.test.nado.xyz/v1/ws",
}

ARCHIVE_INDEXER_URLS = {
    DEFAULT_DOMAIN: "https://archive.prod.nado.xyz/v1",
    TESTNET_DOMAIN: "https://archive.test.nado.xyz/v1",
}

WS_SUBSCRIBE_URLS = {
    DEFAULT_DOMAIN: "wss://gateway.prod.nado.xyz/v1/subscribe",
    TESTNET_DOMAIN: "wss://gateway.test.nado.xyz/v1/subscribe",
}

CONTRACTS = {
    DEFAULT_DOMAIN: "0x05ec92d78ed421f3d3ada77ffde167106565974e",
    TESTNET_DOMAIN: "0x698d87105274292b5673367dec81874ce3633ac2",
}

CHAIN_IDS = {
    DEFAULT_DOMAIN: 57073,
    TESTNET_DOMAIN: 763373,
}

HBOT_BROKER_ID = ""

SIDE_BUY = "BUY"
SIDE_SELL = "SELL"

TIME_IN_FORCE_GTC = "GTC"  # Good till cancelled
TIME_IN_FORCE_IOC = "IOC"  # Immediate or cancel
TIME_IN_FORCE_FOK = "FOK"  # Fill or kill
TIME_IN_FORCE_POSTONLY = "POSTONLY"  # PostOnly

# API PATHS
POST_PATH_URL = "/execute"
QUERY_PATH_URL = "/query"
INDEXER_PATH_URL = "/indexer"
SYMBOLS_PATH_URL = "/symbols"

# POST METHODS
PLACE_ORDER_METHOD = "place_order"
PLACE_ORDER_METHOD_NO_LEVERAGE = "place_order_no_leverage"
CANCEL_ORDERS_METHOD = "cancel_orders"
CANCEL_ALL_METHOD = "cancel_product_orders"

# REST QUERY API TYPES
STATUS_REQUEST_TYPE = "status"
ORDER_REQUEST_TYPE = "order"
SUBACCOUNT_INFO_REQUEST_TYPE = "subaccount_info"
MARKET_LIQUIDITY_REQUEST_TYPE = "market_liquidity"
ALL_PRODUCTS_REQUEST_TYPE = "all_products"
MARKET_PRICE_REQUEST_TYPE = "market_price"
FEE_RATES_REQUEST_TYPE = "fee_rates"
CONTRACTS_REQUEST_TYPE = "contracts"
SUBACCOUNT_ORDERS_REQUEST_TYPE = "subaccount_orders"
MAX_WITHDRAWABLE_REQUEST_TYPE = "max_withdrawable"

# WS API ENDPOINTS
WS_SUBSCRIBE_METHOD = "subscribe"
TOB_TOPIC_EVENT_TYPE = "best_bid_offer"
POSITION_CHANGE_EVENT_TYPE = "position_change"
SNAPSHOT_EVENT_TYPE = "market_liquidity"
TRADE_EVENT_TYPE = "trade"
DIFF_EVENT_TYPE = "book_depth"
FILL_EVENT_TYPE = "fill"
POSITION_CHANGE_EVENT_TYPE = "position_change"

# Products are fetched dynamically from the symbols and all_products queries.
PRODUCTS = {}

# OrderStates
ORDER_STATE = {
    "PendingNew": OrderState.PENDING_CREATE,
    "New": OrderState.OPEN,
    "Filled": OrderState.FILLED,
    "PartiallyFilled": OrderState.PARTIALLY_FILLED,
    "Canceled": OrderState.CANCELED,
    "Rejected": OrderState.FAILED,
}

# Any call increases call rate in ALL pool, so e.g. a query/execute call will contribute to both ALL and query/execute pools.
ALL_ENDPOINTS_LIMIT = "All"
RATE_LIMITS = [
    RateLimit(limit_id=ALL_ENDPOINTS_LIMIT, limit=600, time_interval=10),
    RateLimit(
        limit_id=INDEXER_PATH_URL,
        limit=60,
        time_interval=1,
        linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)],
    ),
    RateLimit(
        limit_id=STATUS_REQUEST_TYPE,
        limit=60,
        time_interval=1,
        linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)],
    ),
    RateLimit(
        limit_id=ORDER_REQUEST_TYPE,
        limit=60,
        time_interval=1,
        # NOTE: No weight for weight of 1...
        linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)],
    ),
    RateLimit(
        limit_id=SUBACCOUNT_INFO_REQUEST_TYPE,
        limit=60,
        time_interval=10,
        weight=10,
        linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)],
    ),
    RateLimit(
        limit_id=MARKET_LIQUIDITY_REQUEST_TYPE,
        limit=60,
        time_interval=1,
        # NOTE: No weight for weight of 1...
        linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)],
    ),
    RateLimit(
        limit_id=ALL_PRODUCTS_REQUEST_TYPE,
        limit=12,
        time_interval=1,
        weight=5,
        linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)],
    ),
    RateLimit(
        limit_id=MARKET_PRICE_REQUEST_TYPE,
        limit=60,
        time_interval=1,
        # NOTE: No weight for weight of 1...
        linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)],
    ),
    RateLimit(
        limit_id=FEE_RATES_REQUEST_TYPE,
        limit=30,
        time_interval=1,
        weight=2,
        linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)],
    ),
    RateLimit(
        limit_id=CONTRACTS_REQUEST_TYPE,
        limit=60,
        time_interval=1,
        weight=1,
        linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)],
    ),
    RateLimit(
        limit_id=SUBACCOUNT_ORDERS_REQUEST_TYPE,
        limit=30,
        time_interval=1,
        weight=2,
        linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)],
    ),
    RateLimit(
        limit_id=MAX_WITHDRAWABLE_REQUEST_TYPE,
        limit=120,
        time_interval=10,
        weight=5,
        linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)],
    ),
    # NOTE: For spot with no leverage, there are different limits.
    # Review https://docs.nado.xyz/developer-resources/api/gateway/executes/place-order
    RateLimit(
        limit_id=PLACE_ORDER_METHOD,
        limit=10,
        time_interval=1,
        linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)],
    ),
    RateLimit(
        limit_id=PLACE_ORDER_METHOD_NO_LEVERAGE,
        limit=5,
        time_interval=10,
        linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)],
    ),
    # NOTE: We're only providing one (1) digest at a time currently.
    # https://docs.nado.xyz/developer-resources/api/gateway/executes/cancel-orders
    RateLimit(
        limit_id=CANCEL_ORDERS_METHOD,
        limit=600,
        time_interval=1,
        linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)],
    ),
    # NOTE: This isn't currently in use.
    # https://docs.nado.xyz/developer-resources/api/gateway/executes/cancel-product-orders
    RateLimit(
        limit_id=CANCEL_ALL_METHOD,
        limit=2,
        time_interval=1,
        linked_limits=[LinkedLimitWeightPair(ALL_ENDPOINTS_LIMIT)],
    ),
]

"""
https://docs.nado.xyz/developer-resources/api/gateway/errors
"""
ERRORS: Dict[int, Any] = {
    1000: {
        "code": 1000,
        "error_value": "RateLimit",
        "description": "Too Many Requests: You have exceeded the rate limit. Please reduce your request frequency and try again later.",
        "message": "",
    },
    1001: {
        "code": 1001,
        "error_value": "BlacklistedAddress",
        "description": "This address has been blacklisted from accessing the sequencer due to a violation of the Terms of Service. If you believe this is an error, please contact the Nado team for assistance.",
        "message": "",
    },
    1002: {
        "code": 1002,
        "error_value": "BlockedLocation",
        "description": "Access from your current location ({location}) is blocked. Please check your location and try again.",
        "message": "",
    },
    1003: {
        "code": 1003,
        "error_value": "BlockedSubdivision",
        "description": "Access from your current location ({location} - {subdivision}) is blocked. Please check your location and try again.",
        "message": "",
    },
}
