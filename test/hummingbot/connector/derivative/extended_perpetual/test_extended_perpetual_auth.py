import asyncio
from typing import Awaitable
from unittest import TestCase
from unittest.mock import MagicMock

from hummingbot.connector.derivative.extended_perpetual.extended_perpetual_auth import ExtendedPerpetualAuth
import hummingbot.connector.derivative.extended_perpetual.extended_perpetual_constants as CONSTANTS
from hummingbot.core.web_assistant.connections.data_types import RESTMethod, RESTRequest, WSJSONRequest


class ExtendedPerpetualAuthTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.api_key = "test_api_key_12345"
        self.stark_private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        self.stark_public_key = "0x5d05989e9302dcebc74e241001e3e3ac3f4402ccf2f8e6f74b034b07ad6a904"
        self.vault_id = 100
        self.is_testnet = False

        self.auth = ExtendedPerpetualAuth(
            api_key=self.api_key,
            stark_private_key=self.stark_private_key,
            stark_public_key=self.stark_public_key,
            vault_id=self.vault_id,
            is_testnet=self.is_testnet
        )

    def async_run_with_timeout(self, coroutine: Awaitable, timeout: int = 1):
        ret = asyncio.get_event_loop().run_until_complete(asyncio.wait_for(coroutine, timeout))
        return ret

    def test_api_key_property(self):
        self.assertEqual(self.api_key, self.auth.api_key)

    def test_stark_private_key_property(self):
        self.assertEqual(self.stark_private_key, self.auth.stark_private_key)

    def test_stark_public_key_property(self):
        self.assertEqual(self.stark_public_key, self.auth.stark_public_key)

    def test_vault_id_property(self):
        self.assertEqual(self.vault_id, self.auth.vault_id)

    def test_is_testnet_property(self):
        self.assertEqual(self.is_testnet, self.auth.is_testnet)

    def test_is_testnet_true(self):
        auth = ExtendedPerpetualAuth(
            api_key=self.api_key,
            stark_private_key=self.stark_private_key,
            stark_public_key=self.stark_public_key,
            vault_id=self.vault_id,
            is_testnet=True
        )
        self.assertTrue(auth.is_testnet)

    def test_get_auth_headers_contains_api_key(self):
        headers = self.auth._get_auth_headers()
        self.assertIn(CONSTANTS.API_KEY_HEADER, headers)
        self.assertEqual(self.api_key, headers[CONSTANTS.API_KEY_HEADER])

    def test_get_auth_headers_contains_user_agent(self):
        headers = self.auth._get_auth_headers()
        self.assertIn(CONSTANTS.USER_AGENT_HEADER, headers)
        self.assertEqual(CONSTANTS.DEFAULT_USER_AGENT, headers[CONSTANTS.USER_AGENT_HEADER])

    def test_rest_authenticate_adds_headers_to_request_without_headers(self):
        request = RESTRequest(
            method=RESTMethod.GET,
            url="https://test.url/api/v1/test",
            is_auth_required=True,
        )
        self.assertIsNone(request.headers)

        authenticated_request = self.async_run_with_timeout(self.auth.rest_authenticate(request))

        self.assertIsNotNone(authenticated_request.headers)
        self.assertIn(CONSTANTS.API_KEY_HEADER, authenticated_request.headers)
        self.assertEqual(self.api_key, authenticated_request.headers[CONSTANTS.API_KEY_HEADER])
        self.assertIn(CONSTANTS.USER_AGENT_HEADER, authenticated_request.headers)
        self.assertEqual(CONSTANTS.DEFAULT_USER_AGENT, authenticated_request.headers[CONSTANTS.USER_AGENT_HEADER])

    def test_rest_authenticate_adds_headers_to_request_with_existing_headers(self):
        request = RESTRequest(
            method=RESTMethod.POST,
            url="https://test.url/api/v1/order",
            headers={"Content-Type": "application/json"},
            is_auth_required=True,
        )

        authenticated_request = self.async_run_with_timeout(self.auth.rest_authenticate(request))

        self.assertEqual("application/json", authenticated_request.headers["Content-Type"])
        self.assertEqual(self.api_key, authenticated_request.headers[CONSTANTS.API_KEY_HEADER])
        self.assertEqual(CONSTANTS.DEFAULT_USER_AGENT, authenticated_request.headers[CONSTANTS.USER_AGENT_HEADER])

    def test_rest_authenticate_preserves_original_request_data(self):
        request = RESTRequest(
            method=RESTMethod.POST,
            url="https://test.url/api/v1/order",
            data='{"test": "data"}',
            is_auth_required=True,
        )

        authenticated_request = self.async_run_with_timeout(self.auth.rest_authenticate(request))

        self.assertEqual(RESTMethod.POST, authenticated_request.method)
        self.assertEqual("https://test.url/api/v1/order", authenticated_request.url)
        self.assertEqual('{"test": "data"}', authenticated_request.data)

    def test_ws_authenticate_adds_headers_to_request_without_headers(self):
        request = WSJSONRequest(
            payload={"action": "subscribe", "channel": "orderbook"},
        )

        authenticated_request = self.async_run_with_timeout(self.auth.ws_authenticate(request))

        self.assertIsNotNone(authenticated_request.payload)
        self.assertIn("apiKey", authenticated_request.payload)
        self.assertEqual(self.api_key, authenticated_request.payload["apiKey"])

    def test_ws_authenticate_adds_headers_to_request_with_existing_headers(self):
        request = WSJSONRequest(
            payload={"action": "subscribe", "channel": "account"},
        )

        authenticated_request = self.async_run_with_timeout(self.auth.ws_authenticate(request))

        self.assertIn("action", authenticated_request.payload)
        self.assertIn("apiKey", authenticated_request.payload)

    def test_get_ws_auth_payload(self):
        payload = self.auth.get_ws_auth_payload()

        self.assertIn("apiKey", payload)
        self.assertEqual(self.api_key, payload["apiKey"])
        self.assertIn("starkKey", payload)
        self.assertEqual(self.stark_public_key, payload["starkKey"])

    def test_get_ws_auth_payload_returns_dict(self):
        payload = self.auth.get_ws_auth_payload()
        self.assertIsInstance(payload, dict)
        self.assertEqual(2, len(payload))
