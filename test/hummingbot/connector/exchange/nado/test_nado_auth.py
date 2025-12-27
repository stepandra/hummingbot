import asyncio
from typing import Awaitable
from unittest import TestCase

import hummingbot.connector.exchange.nado.nado_constants as CONSTANTS
from hummingbot.connector.exchange.nado.nado_auth import NadoAuth
from hummingbot.connector.exchange.nado.nado_eip712_structs import Order
from hummingbot.core.web_assistant.connections.data_types import (
    RESTMethod,
    RESTRequest,
    WSJSONRequest,
)


class NadoAuthTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        # NOTE: RANDOM KEYS GENERATED JUST FOR UNIT TESTS
        self.sender_address = "0x2162Db26939B9EAF0C5404217774d166056d31B5"  # noqa: mock
        self.private_key = (
            "5500eb16bf3692840e04fb6a63547b9a80b75d9cbb36b43ca5662127d4c19c83"  # noqa: mock
        )

        self.auth = NadoAuth(
            nado_ink_address=self.sender_address,
            nado_ink_private_key=self.private_key,
        )

    def async_run_with_timeout(self, coroutine: Awaitable, timeout: int = 1):
        ret = asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(coroutine, timeout)
        )
        return ret

    def test_rest_authenticate(self):
        request = RESTRequest(
            method=RESTMethod.GET,
            url="https://test.url/api/endpoint",
            is_auth_required=True,
            throttler_limit_id="/api/endpoint",
        )
        ret = self.async_run_with_timeout(self.auth.rest_authenticate(request))
        self.assertEqual(request, ret)

    def test_ws_authenticate(self):
        payload = {"param1": "value_param_1"}
        request = WSJSONRequest(payload=payload, is_auth_required=False)
        ret = self.async_run_with_timeout(self.auth.ws_authenticate(request))
        self.assertEqual(payload, request.payload)
        self.assertEqual(request, ret)

    def test_get_referral_code_headers(self):
        headers = {"referer": CONSTANTS.HBOT_BROKER_ID}
        self.assertEqual(headers, self.auth.get_referral_code_headers())

    def test_sign_payload(self):
        order = Order(
            sender="0x2162Db26939B9EAF0C5404217774d166056d31B5",  # noqa: mock
            priceX18=26383000000000000000000,
            amount=2292000000000000000,
            expiration=1685989016,
            nonce=1767924162661187978,
            appendix=1,
        )
        contract = "0x0000000000000000000000000000000000000002"  # noqa: mock
        chain_id = 763373
        signature, digest = self.auth.sign_payload(order, contract, chain_id)
        signature2, digest2 = self.auth.sign_payload(order, contract, chain_id)
        self.assertTrue(signature.startswith("0x"))
        self.assertTrue(digest.startswith("0x"))
        self.assertEqual(132, len(signature))
        self.assertEqual(66, len(digest))
        self.assertEqual(signature, signature2)
        self.assertEqual(digest, digest2)

    def test_generate_digest(self):
        signable_bytes = (
            b"\x19\x01\xb0_\xd0\xc1Co\xf9K\xb2C$*S\x8f\xd78\xac\xc3\xdcdu\xf0\xfcY\x9d9\xac\xe7\xff/"
            b"\xa6)\x1fp-\xfcL\x9d\xdf\xe8\xbb\xffe\x0bJIl\x14\x94\x89\xc9{\x9af\x97\xad2\x13\x8a1\xca"
            b"\x89\xfa\xd3"
        )  # noqa: mock
        digest = self.auth.generate_digest(signable_bytes)
        self.assertTrue(digest.startswith("0x"))
        self.assertEqual(66, len(digest))
