"""Utility helpers for Vest Perpetual REST/WS endpoints and API factories."""

from typing import Any, Dict, Optional

from hummingbot.connector.derivative.vest_perpetual import (
    vest_perpetual_constants as CONSTANTS,
)
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTRequest
from hummingbot.core.web_assistant.rest_pre_processors import RESTPreProcessorBase
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory


class VestPerpetualRESTPreProcessor(RESTPreProcessorBase):
    async def pre_process(self, request: RESTRequest) -> RESTRequest:
        request.headers = request.headers or {}
        request.headers.setdefault("Content-Type", "application/json")
        return request


def _resolve_domain(use_testnet: bool = False, domain: Optional[str] = None) -> str:
    if domain:
        return domain
    return CONSTANTS.TESTNET_DOMAIN if use_testnet else CONSTANTS.DEFAULT_DOMAIN


def rest_url(
    path_url: str, use_testnet: bool = False, domain: Optional[str] = None
) -> str:
    """Creates a full REST URL for a path."""
    resolved_domain = _resolve_domain(use_testnet=use_testnet, domain=domain)
    base_url = CONSTANTS.REST_URLS.get(resolved_domain, CONSTANTS.REST_URL_PROD)
    return base_url + path_url


def public_rest_url(path_url: str, domain: str = CONSTANTS.DEFAULT_DOMAIN) -> str:
    return rest_url(path_url=path_url, domain=domain)


def private_rest_url(path_url: str, domain: str = CONSTANTS.DEFAULT_DOMAIN) -> str:
    return rest_url(path_url=path_url, domain=domain)


def wss_url(use_testnet: bool = False) -> str:
    """Deprecated helper preserved for backwards compatibility."""
    return CONSTANTS.WSS_URL_DEV if use_testnet else CONSTANTS.WSS_URL_PROD


def public_ws_url(
    domain: str = CONSTANTS.DEFAULT_DOMAIN, account_group: int = 0
) -> str:
    base_ws_url = CONSTANTS.WSS_URLS.get(domain, CONSTANTS.WSS_URL_PROD)
    query = f"version=1.0&xwebsocketserver=restserver{account_group}&websocketserver=restserver{account_group}"
    return f"{base_ws_url}?{query}"


def private_ws_url(
    listen_key: str,
    domain: str = CONSTANTS.DEFAULT_DOMAIN,
    account_group: int = 0,
) -> str:
    base = public_ws_url(domain=domain, account_group=account_group)
    return f"{base}&listenKey={listen_key}"


def build_api_factory(
    throttler: Optional[AsyncThrottler] = None,
    auth: Optional[AuthBase] = None,
    use_testnet: bool = False,
) -> WebAssistantsFactory:
    """
    Builds a WebAssistantsFactory with the required settings for Vest Perpetual.
    Similar pattern to Lighter connector.
    """
    throttler = throttler or create_throttler()
    del use_testnet
    return WebAssistantsFactory(
        throttler=throttler,
        rest_pre_processors=[VestPerpetualRESTPreProcessor()],
        auth=auth,
    )


def build_api_factory_without_time_synchronizer_pre_processor(
    throttler: AsyncThrottler,
) -> WebAssistantsFactory:
    """
    Builds a WebAssistantsFactory without the time synchronizer pre-processor.
    """
    return WebAssistantsFactory(
        throttler=throttler,
        rest_pre_processors=[VestPerpetualRESTPreProcessor()],
    )


def create_throttler() -> AsyncThrottler:
    """
    Creates the default AsyncThrottler for Vest Perpetual.
    """
    return AsyncThrottler(CONSTANTS.RATE_LIMITS)


async def get_current_server_time(throttler: AsyncThrottler, domain: str) -> float:
    """
    Gets the current server time from Vest.
    Vest doesn't expose a server time endpoint, so we raise NotImplementedError.
    """
    del throttler, domain
    raise NotImplementedError("Vest does not expose a server time endpoint.")


def is_exchange_information_valid(market_info: Dict[str, Any]) -> bool:
    """Check if the market info indicates a valid/tradable market."""
    status = market_info.get("status", "").upper()
    return status in {CONSTANTS.SYMBOL_STATUS_TRADING, ""}
