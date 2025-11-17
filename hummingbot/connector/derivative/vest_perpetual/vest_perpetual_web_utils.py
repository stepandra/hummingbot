from typing import Any, Dict, Optional
from urllib.parse import urlencode

import hummingbot.connector.derivative.vest_perpetual.vest_perpetual_constants as CONSTANTS
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTRequest
from hummingbot.core.web_assistant.rest_pre_processors import RESTPreProcessorBase
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory


class VestPerpetualRESTPreProcessor(RESTPreProcessorBase):
    """REST request preprocessor for Vest Perpetual."""

    async def pre_process(self, request: RESTRequest) -> RESTRequest:
        if request.headers is None:
            request.headers = {}
        request.headers["Content-Type"] = "application/json"
        return request


def public_rest_url(path_url: str, domain: str = CONSTANTS.DEFAULT_DOMAIN) -> str:
    """Build a public REST API URL.

    Args:
        path_url: The API endpoint path (e.g., "/exchangeInfo")
        domain: The domain to use (default or testnet)

    Returns:
        Full URL for the endpoint
    """
    return _rest_url(path_url, domain)


def private_rest_url(path_url: str, domain: str = CONSTANTS.DEFAULT_DOMAIN) -> str:
    """Build a private REST API URL.

    Args:
        path_url: The API endpoint path (e.g., "/orders")
        domain: The domain to use (default or testnet)

    Returns:
        Full URL for the endpoint
    """
    return _rest_url(path_url, domain)


def _rest_url(path_url: str, domain: str) -> str:
    """Internal helper to build REST URLs."""
    if domain == CONSTANTS.TESTNET_DOMAIN:
        base_url = CONSTANTS.TESTNET_BASE_URL
    else:
        base_url = CONSTANTS.PERPETUAL_BASE_URL
    return base_url + path_url


def public_ws_url(domain: str = CONSTANTS.DEFAULT_DOMAIN, account_group: int = 0) -> str:
    """Build a public WebSocket URL with account group parameter.

    Args:
        domain: The domain to use (default or testnet)
        account_group: The account group number

    Returns:
        Full WebSocket URL with query parameters
    """
    base_ws_url = _wss_base_url(domain)
    query_params = {
        "version": "1.0",
        "websocketserver": f"restserver{account_group}",
    }
    return f"{base_ws_url}?{urlencode(query_params)}"


def private_ws_url(listen_key: str, domain: str = CONSTANTS.DEFAULT_DOMAIN, account_group: int = 0) -> str:
    """Build a private WebSocket URL with listenKey.

    Args:
        listen_key: The listenKey obtained from /account/listenKey
        domain: The domain to use (default or testnet)
        account_group: The account group number

    Returns:
        Full WebSocket URL with query parameters including listenKey
    """
    base_ws_url = _wss_base_url(domain)
    query_params = {
        "version": "1.0",
        "websocketserver": f"restserver{account_group}",
        "listenKey": listen_key,
    }
    return f"{base_ws_url}?{urlencode(query_params)}"


def _wss_base_url(domain: str) -> str:
    """Internal helper to get WebSocket base URL."""
    if domain == CONSTANTS.TESTNET_DOMAIN:
        return CONSTANTS.TESTNET_WS_URL
    else:
        return CONSTANTS.PERPETUAL_WS_URL


def build_api_factory(
    throttler: Optional[AsyncThrottler] = None,
    auth: Optional[AuthBase] = None
) -> WebAssistantsFactory:
    """Build the Web Assistants Factory for Vest Perpetual.

    Args:
        throttler: Optional throttler instance
        auth: Optional auth instance

    Returns:
        Configured WebAssistantsFactory
    """
    throttler = throttler or create_throttler()
    api_factory = WebAssistantsFactory(
        throttler=throttler,
        rest_pre_processors=[VestPerpetualRESTPreProcessor()],
        auth=auth
    )
    return api_factory


def build_api_factory_without_time_synchronizer_pre_processor(
    throttler: AsyncThrottler
) -> WebAssistantsFactory:
    """Build API factory without time synchronizer (Vest doesn't require time sync).

    Args:
        throttler: The throttler instance

    Returns:
        Configured WebAssistantsFactory
    """
    api_factory = WebAssistantsFactory(
        throttler=throttler,
        rest_pre_processors=[VestPerpetualRESTPreProcessor()]
    )
    return api_factory


def create_throttler() -> AsyncThrottler:
    """Create a throttler with Vest Perpetual rate limits.

    Returns:
        Configured AsyncThrottler
    """
    return AsyncThrottler(CONSTANTS.RATE_LIMITS)


def is_exchange_information_valid(exchange_info: Dict[str, Any]) -> bool:
    """Verify if a trading pair is enabled based on exchange information.

    Args:
        exchange_info: Exchange information for a trading pair

    Returns:
        True if the trading pair is enabled for trading
    """
    # Check if the symbol status is TRADING
    status = exchange_info.get("status", "")
    return status == "TRADING"
