from typing import Dict, Optional

import hummingbot.connector.derivative.extended_perpetual.extended_perpetual_constants as CONSTANTS
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTRequest, WSJSONRequest


class ExtendedPerpetualAuth(AuthBase):
    """
    Auth class required by Extended Perpetual API.
    Handles API key authentication for REST and WebSocket requests.
    """

    def __init__(
        self,
        api_key: str,
        stark_private_key: str,
        stark_public_key: str,
        vault_id: int,
        is_testnet: bool = False
    ):
        self._api_key = api_key
        self._stark_private_key = stark_private_key
        self._stark_public_key = stark_public_key
        self._vault_id = vault_id
        self._is_testnet = is_testnet

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def stark_private_key(self) -> str:
        return self._stark_private_key

    @property
    def stark_public_key(self) -> str:
        return self._stark_public_key

    @property
    def vault_id(self) -> int:
        return self._vault_id

    @property
    def is_testnet(self) -> bool:
        return self._is_testnet

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Returns authentication headers for API requests.
        """
        return {
            CONSTANTS.API_KEY_HEADER: self._api_key,
            CONSTANTS.USER_AGENT_HEADER: CONSTANTS.DEFAULT_USER_AGENT,
        }

    async def rest_authenticate(self, request: RESTRequest) -> RESTRequest:
        """
        Adds authentication headers to REST requests.
        
        :param request: the request to be authenticated
        :return: the authenticated request
        """
        if request.headers is None:
            request.headers = {}
        request.headers.update(self._get_auth_headers())
        return request

    async def ws_authenticate(self, request: WSJSONRequest) -> WSJSONRequest:
        """
        Adds authentication data for WebSocket connections.
        
        :param request: the WebSocket request to be authenticated
        :return: the authenticated request with auth payload merged
        """
        auth_payload = self.get_ws_auth_payload()
        new_payload = {**request.payload, **auth_payload}
        return WSJSONRequest(
            payload=new_payload,
            throttler_limit_id=request.throttler_limit_id,
            is_auth_required=request.is_auth_required,
        )

    def get_ws_auth_payload(self) -> Dict[str, str]:
        """
        Returns authentication payload for WebSocket subscription messages.
        """
        return {
            "apiKey": self._api_key,
            "starkKey": self._stark_public_key,
        }
