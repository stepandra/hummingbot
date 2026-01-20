from unittest import TestCase

from hummingbot.core.api_throttler.data_types import RateLimit
from hummingbot.core.data_type.in_flight_order import OrderState

import hummingbot.connector.derivative.extended_perpetual.extended_perpetual_constants as CONSTANTS


class ExtendedPerpetualConstantsTests(TestCase):
    def test_exchange_name(self):
        self.assertEqual("extended_perpetual", CONSTANTS.EXCHANGE_NAME)

    def test_default_domain(self):
        self.assertEqual("starknet", CONSTANTS.DEFAULT_DOMAIN)

    def test_testnet_domain(self):
        self.assertEqual("extended_perpetual_testnet", CONSTANTS.TESTNET_DOMAIN)

    def test_hbot_order_id_prefix(self):
        self.assertEqual("HBOT", CONSTANTS.HBOT_ORDER_ID_PREFIX)

    def test_max_order_id_len(self):
        self.assertEqual(32, CONSTANTS.MAX_ORDER_ID_LEN)

    def test_market_order_slippage(self):
        self.assertEqual(0.05, CONSTANTS.MARKET_ORDER_SLIPPAGE)

    def test_rest_url(self):
        self.assertEqual("https://api.starknet.extended.exchange", CONSTANTS.REST_URL)

    def test_wss_url(self):
        self.assertEqual("wss://api.starknet.extended.exchange", CONSTANTS.WSS_URL)

    def test_testnet_rest_url(self):
        self.assertEqual("https://api.testnet.extended.exchange", CONSTANTS.TESTNET_REST_URL)

    def test_testnet_wss_url(self):
        self.assertEqual("wss://api.testnet.extended.exchange", CONSTANTS.TESTNET_WSS_URL)

    def test_currency(self):
        self.assertEqual("USD", CONSTANTS.CURRENCY)

    def test_funding_rate_update_interval(self):
        self.assertEqual(60, CONSTANTS.FUNDING_RATE_UPDATE_INTERNAL_SECOND)


class ExtendedPerpetualConstantsPathTests(TestCase):
    def test_markets_path(self):
        self.assertEqual("/api/v1/info/markets", CONSTANTS.MARKETS_PATH)

    def test_orderbook_path(self):
        self.assertEqual("/api/v1/info/markets/{market}/orderbook", CONSTANTS.ORDERBOOK_PATH)

    def test_market_stats_path(self):
        self.assertEqual("/api/v1/info/markets/{market}/stats", CONSTANTS.MARKET_STATS_PATH)

    def test_public_trades_path(self):
        self.assertEqual("/api/v1/info/markets/{market}/trades", CONSTANTS.PUBLIC_TRADES_PATH)

    def test_balance_path(self):
        self.assertEqual("/api/v1/user/balance", CONSTANTS.BALANCE_PATH)

    def test_positions_path(self):
        self.assertEqual("/api/v1/user/positions", CONSTANTS.POSITIONS_PATH)

    def test_open_orders_path(self):
        self.assertEqual("/api/v1/user/orders", CONSTANTS.OPEN_ORDERS_PATH)

    def test_order_history_path(self):
        self.assertEqual("/api/v1/user/orders/history", CONSTANTS.ORDER_HISTORY_PATH)

    def test_trades_path(self):
        self.assertEqual("/api/v1/user/trades", CONSTANTS.TRADES_PATH)

    def test_create_order_path(self):
        self.assertEqual("/api/v1/user/order", CONSTANTS.CREATE_ORDER_PATH)

    def test_cancel_order_path(self):
        self.assertEqual("/api/v1/user/order/{id}", CONSTANTS.CANCEL_ORDER_PATH)

    def test_cancel_order_by_external_id_path(self):
        self.assertEqual("/api/v1/user/order", CONSTANTS.CANCEL_ORDER_BY_EXTERNAL_ID_PATH)

    def test_mass_cancel_path(self):
        self.assertEqual("/api/v1/user/order/massCancel", CONSTANTS.MASS_CANCEL_PATH)

    def test_leverage_path(self):
        self.assertEqual("/api/v1/user/leverage", CONSTANTS.LEVERAGE_PATH)

    def test_funding_history_path(self):
        self.assertEqual("/api/v1/user/funding/history", CONSTANTS.FUNDING_HISTORY_PATH)

    def test_account_path(self):
        self.assertEqual("/api/v1/user/account", CONSTANTS.ACCOUNT_PATH)

    def test_fees_path(self):
        self.assertEqual("/api/v1/user/fees", CONSTANTS.FEES_PATH)

    def test_ping_path(self):
        self.assertEqual("/api/v1/info/ping", CONSTANTS.PING_PATH)


class ExtendedPerpetualConstantsWSPathTests(TestCase):
    def test_ws_orderbook_path(self):
        self.assertEqual("/stream.extended.exchange/v1/orderbooks/{market}", CONSTANTS.WS_ORDERBOOK_PATH)

    def test_ws_trades_path(self):
        self.assertEqual("/stream.extended.exchange/v1/publicTrades/{market}", CONSTANTS.WS_TRADES_PATH)

    def test_ws_funding_path(self):
        self.assertEqual("/stream.extended.exchange/v1/funding/{market}", CONSTANTS.WS_FUNDING_PATH)

    def test_ws_account_path(self):
        self.assertEqual("/stream.extended.exchange/v1/account", CONSTANTS.WS_ACCOUNT_PATH)


class ExtendedPerpetualConstantsHeaderTests(TestCase):
    def test_api_key_header(self):
        self.assertEqual("X-Api-Key", CONSTANTS.API_KEY_HEADER)

    def test_user_agent_header(self):
        self.assertEqual("User-Agent", CONSTANTS.USER_AGENT_HEADER)

    def test_default_user_agent(self):
        self.assertEqual("hummingbot/1.0", CONSTANTS.DEFAULT_USER_AGENT)


class ExtendedPerpetualConstantsOrderStateTests(TestCase):
    def test_order_state_new_lowercase(self):
        self.assertEqual(OrderState.OPEN, CONSTANTS.ORDER_STATE["new"])

    def test_order_state_new_uppercase(self):
        self.assertEqual(OrderState.OPEN, CONSTANTS.ORDER_STATE["NEW"])

    def test_order_state_partially_filled_lowercase(self):
        self.assertEqual(OrderState.PARTIALLY_FILLED, CONSTANTS.ORDER_STATE["partially filled"])

    def test_order_state_partially_filled_uppercase(self):
        self.assertEqual(OrderState.PARTIALLY_FILLED, CONSTANTS.ORDER_STATE["PARTIALLY_FILLED"])

    def test_order_state_untriggered_lowercase(self):
        self.assertEqual(OrderState.OPEN, CONSTANTS.ORDER_STATE["untriggered"])

    def test_order_state_untriggered_uppercase(self):
        self.assertEqual(OrderState.OPEN, CONSTANTS.ORDER_STATE["UNTRIGGERED"])

    def test_order_state_filled_lowercase(self):
        self.assertEqual(OrderState.FILLED, CONSTANTS.ORDER_STATE["filled"])

    def test_order_state_filled_uppercase(self):
        self.assertEqual(OrderState.FILLED, CONSTANTS.ORDER_STATE["FILLED"])

    def test_order_state_cancelled_lowercase(self):
        self.assertEqual(OrderState.CANCELED, CONSTANTS.ORDER_STATE["cancelled"])

    def test_order_state_cancelled_uppercase(self):
        self.assertEqual(OrderState.CANCELED, CONSTANTS.ORDER_STATE["CANCELLED"])

    def test_order_state_rejected_lowercase(self):
        self.assertEqual(OrderState.FAILED, CONSTANTS.ORDER_STATE["rejected"])

    def test_order_state_rejected_uppercase(self):
        self.assertEqual(OrderState.FAILED, CONSTANTS.ORDER_STATE["REJECTED"])

    def test_order_state_expired_lowercase(self):
        self.assertEqual(OrderState.CANCELED, CONSTANTS.ORDER_STATE["expired"])

    def test_order_state_expired_uppercase(self):
        self.assertEqual(OrderState.CANCELED, CONSTANTS.ORDER_STATE["EXPIRED"])


class ExtendedPerpetualConstantsTimingTests(TestCase):
    def test_ping_interval(self):
        self.assertEqual(15, CONSTANTS.PING_INTERVAL)

    def test_pong_timeout(self):
        self.assertEqual(10, CONSTANTS.PONG_TIMEOUT)

    def test_order_expiry_mainnet_max_days(self):
        self.assertEqual(90, CONSTANTS.ORDER_EXPIRY_MAINNET_MAX_DAYS)

    def test_order_expiry_testnet_max_days(self):
        self.assertEqual(28, CONSTANTS.ORDER_EXPIRY_TESTNET_MAX_DAYS)

    def test_heartbeat_time_interval(self):
        self.assertEqual(30.0, CONSTANTS.HEARTBEAT_TIME_INTERVAL)


class ExtendedPerpetualConstantsRateLimitTests(TestCase):
    def test_max_request(self):
        self.assertEqual(1200, CONSTANTS.MAX_REQUEST)

    def test_one_minute(self):
        self.assertEqual(60, CONSTANTS.ONE_MINUTE)

    def test_all_endpoints_limit(self):
        self.assertEqual("All", CONSTANTS.ALL_ENDPOINTS_LIMIT)

    def test_rate_limits_is_list(self):
        self.assertIsInstance(CONSTANTS.RATE_LIMITS, list)

    def test_rate_limits_not_empty(self):
        self.assertGreater(len(CONSTANTS.RATE_LIMITS), 0)

    def test_rate_limits_all_are_rate_limit_type(self):
        for rate_limit in CONSTANTS.RATE_LIMITS:
            self.assertIsInstance(rate_limit, RateLimit)

    def test_rate_limit_all_endpoints_exists(self):
        all_limit = next(
            (rl for rl in CONSTANTS.RATE_LIMITS if rl.limit_id == CONSTANTS.ALL_ENDPOINTS_LIMIT),
            None
        )
        self.assertIsNotNone(all_limit)
        self.assertEqual(CONSTANTS.MAX_REQUEST, all_limit.limit)
        self.assertEqual(CONSTANTS.ONE_MINUTE, all_limit.time_interval)

    def test_rate_limits_for_key_paths(self):
        key_paths = [
            CONSTANTS.MARKETS_PATH,
            CONSTANTS.ORDERBOOK_PATH,
            CONSTANTS.BALANCE_PATH,
            CONSTANTS.CREATE_ORDER_PATH,
            CONSTANTS.CANCEL_ORDER_PATH,
        ]
        for path in key_paths:
            rate_limit = next(
                (rl for rl in CONSTANTS.RATE_LIMITS if rl.limit_id == path),
                None
            )
            self.assertIsNotNone(rate_limit, f"Rate limit not found for {path}")


class ExtendedPerpetualConstantsErrorMessagesTests(TestCase):
    def test_order_not_exist_message(self):
        self.assertEqual("order", CONSTANTS.ORDER_NOT_EXIST_MESSAGE)

    def test_unknown_order_message(self):
        self.assertEqual(
            "Order was never placed, already canceled, or filled",
            CONSTANTS.UNKNOWN_ORDER_MESSAGE
        )
