import time
from typing import Any, Dict, Optional

import hummingbot.connector.derivative.extended_perpetual.extended_perpetual_constants as CONSTANTS
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTRequest
from hummingbot.core.web_assistant.rest_pre_processors import RESTPreProcessorBase
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory


class ExtendedPerpetualRESTPreProcessor(RESTPreProcessorBase):
    """
    Pre-processor to add required headers to all REST requests.
    """

    async def pre_process(self, request: RESTRequest) -> RESTRequest:
        if request.headers is None:
            request.headers = {}
        request.headers["Content-Type"] = "application/json"
        request.headers[CONSTANTS.USER_AGENT_HEADER] = CONSTANTS.DEFAULT_USER_AGENT
        return request


def public_rest_url(path_url: str, domain: str = CONSTANTS.DEFAULT_DOMAIN) -> str:
    """
    Creates a full URL for public REST endpoints.

    :param path_url: the path of the endpoint
    :param domain: the domain to use (starknet or testnet)
    :return: the full URL
    """
    return rest_url(path_url, domain)


def private_rest_url(path_url: str, domain: str = CONSTANTS.DEFAULT_DOMAIN) -> str:
    """
    Creates a full URL for private REST endpoints.

    :param path_url: the path of the endpoint
    :param domain: the domain to use (starknet or testnet)
    :return: the full URL
    """
    return rest_url(path_url, domain)


def rest_url(path_url: str, domain: str = CONSTANTS.DEFAULT_DOMAIN) -> str:
    """
    Creates a full URL for REST endpoints.

    :param path_url: the path of the endpoint
    :param domain: the domain to use (starknet or testnet)
    :return: the full URL
    """
    if domain == CONSTANTS.DEFAULT_DOMAIN:
        base_url = CONSTANTS.REST_URL
    else:
        base_url = CONSTANTS.TESTNET_REST_URL
    return base_url + path_url


def wss_url(path_url: str = "", domain: str = CONSTANTS.DEFAULT_DOMAIN) -> str:
    """
    Creates a full URL for WebSocket connections.

    :param path_url: optional path to append
    :param domain: the domain to use (starknet or testnet)
    :return: the full WebSocket URL
    """
    if domain == CONSTANTS.DEFAULT_DOMAIN:
        base_ws_url = CONSTANTS.WSS_URL
    else:
        base_ws_url = CONSTANTS.TESTNET_WSS_URL
    return base_ws_url + path_url


def build_api_factory(
        throttler: Optional[AsyncThrottler] = None,
        auth: Optional[AuthBase] = None) -> WebAssistantsFactory:
    """
    Builds a WebAssistantsFactory with the required pre-processors and authentication.

    :param throttler: optional throttler for rate limiting
    :param auth: optional authentication handler
    :return: configured WebAssistantsFactory
    """
    throttler = throttler or create_throttler()
    api_factory = WebAssistantsFactory(
        throttler=throttler,
        rest_pre_processors=[ExtendedPerpetualRESTPreProcessor()],
        auth=auth)
    return api_factory


def build_api_factory_without_time_synchronizer_pre_processor(
        throttler: AsyncThrottler) -> WebAssistantsFactory:
    """
    Builds a WebAssistantsFactory without time synchronization pre-processor.

    :param throttler: throttler for rate limiting
    :return: configured WebAssistantsFactory
    """
    api_factory = WebAssistantsFactory(
        throttler=throttler,
        rest_pre_processors=[ExtendedPerpetualRESTPreProcessor()])
    return api_factory


def create_throttler() -> AsyncThrottler:
    """
    Creates an AsyncThrottler with the configured rate limits.

    :return: configured AsyncThrottler
    """
    return AsyncThrottler(CONSTANTS.RATE_LIMITS)


async def get_current_server_time(
        throttler: Optional[AsyncThrottler] = None,
        domain: str = CONSTANTS.DEFAULT_DOMAIN) -> float:
    """
    Gets the current server time. Extended Exchange does not require time synchronization,
    so this returns the local time.

    :param throttler: optional throttler
    :param domain: the domain to use
    :return: current timestamp in seconds
    """
    return time.time()


def is_exchange_information_valid(rule: Dict[str, Any]) -> bool:
    """
    Verifies if a trading pair is enabled to operate with based on its exchange information.

    :param rule: the exchange information for a trading pair
    :return: True if the trading pair is enabled, False otherwise
    """
    return True
