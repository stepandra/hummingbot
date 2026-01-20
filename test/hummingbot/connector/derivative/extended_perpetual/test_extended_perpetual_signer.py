import time
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

from hummingbot.connector.derivative.extended_perpetual.extended_perpetual_signer import (
    ExtendedPerpetualSigner,
    OrderSettlement,
    StarknetDomain,
)
import hummingbot.connector.derivative.extended_perpetual.extended_perpetual_constants as CONSTANTS


class StarknetDomainTests(TestCase):
    def test_default_values(self):
        domain = StarknetDomain()
        self.assertEqual("Perpetuals", domain.name)
        self.assertEqual("v0", domain.version)
        self.assertEqual("SN_MAIN", domain.chain_id)
        self.assertEqual("1", domain.revision)

    def test_testnet_chain_id(self):
        domain = StarknetDomain(chain_id="SN_SEPOLIA")
        self.assertEqual("SN_SEPOLIA", domain.chain_id)


class OrderSettlementTests(TestCase):
    def test_order_settlement_dataclass(self):
        settlement = OrderSettlement(
            r=12345,
            s=67890,
            stark_key="0xabc",
            collateral_position=100,
            nonce=999,
            expiration_seconds=1700000000,
        )
        self.assertEqual(12345, settlement.r)
        self.assertEqual(67890, settlement.s)
        self.assertEqual("0xabc", settlement.stark_key)
        self.assertEqual(100, settlement.collateral_position)
        self.assertEqual(999, settlement.nonce)
        self.assertEqual(1700000000, settlement.expiration_seconds)


class ExtendedPerpetualSignerTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        self.public_key = "0x5d05989e9302dcebc74e241001e3e3ac3f4402ccf2f8e6f74b034b07ad6a904"
        self.vault_id = 100
        self.is_testnet = True

        self.signer = ExtendedPerpetualSigner(
            private_key=self.private_key,
            public_key=self.public_key,
            vault_id=self.vault_id,
            is_testnet=self.is_testnet,
        )

    def test_parse_hex_key_with_0x_prefix(self):
        result = ExtendedPerpetualSigner._parse_hex_key("0x1a2b3c")
        self.assertEqual(0x1a2b3c, result)

    def test_parse_hex_key_with_0X_prefix(self):
        result = ExtendedPerpetualSigner._parse_hex_key("0X1a2b3c")
        self.assertEqual(0x1a2b3c, result)

    def test_parse_hex_key_without_prefix(self):
        result = ExtendedPerpetualSigner._parse_hex_key("1a2b3c")
        self.assertEqual(0x1a2b3c, result)

    def test_normalize_hex_with_prefix(self):
        result = ExtendedPerpetualSigner._normalize_hex("0xabc")
        self.assertEqual("0xabc", result)

    def test_normalize_hex_without_prefix(self):
        result = ExtendedPerpetualSigner._normalize_hex("abc")
        self.assertEqual("0xabc", result)

    def test_generate_nonce_within_u32_range(self):
        for _ in range(100):
            nonce = self.signer.generate_nonce()
            self.assertGreaterEqual(nonce, 0)
            self.assertLessEqual(nonce, ExtendedPerpetualSigner.MAX_U32)

    def test_generate_nonce_is_random(self):
        nonces = set(self.signer.generate_nonce() for _ in range(100))
        self.assertGreater(len(nonces), 1)

    def test_calculate_collateral_amount_buy_rounds_up(self):
        scaled_amount, is_buy = self.signer._calculate_collateral_amount(
            side="buy",
            synthetic_amount=Decimal("1.5"),
            price=Decimal("100.33"),
            collateral_resolution=10**6,
        )
        self.assertTrue(is_buy)
        self.assertEqual(150495000, scaled_amount)

    def test_calculate_collateral_amount_sell_rounds_down(self):
        scaled_amount, is_buy = self.signer._calculate_collateral_amount(
            side="sell",
            synthetic_amount=Decimal("1.5"),
            price=Decimal("100.33"),
            collateral_resolution=10**6,
        )
        self.assertFalse(is_buy)
        self.assertEqual(150495000, scaled_amount)

    def test_calculate_collateral_amount_buy_case_insensitive(self):
        _, is_buy_upper = self.signer._calculate_collateral_amount(
            side="BUY",
            synthetic_amount=Decimal("1"),
            price=Decimal("100"),
            collateral_resolution=10**6,
        )
        self.assertTrue(is_buy_upper)

        _, is_buy_lower = self.signer._calculate_collateral_amount(
            side="buy",
            synthetic_amount=Decimal("1"),
            price=Decimal("100"),
            collateral_resolution=10**6,
        )
        self.assertTrue(is_buy_lower)

    def test_calculate_synthetic_amount_rounds_up(self):
        result = self.signer._calculate_synthetic_amount(
            synthetic_amount=Decimal("1.234"),
            synthetic_resolution=10**8,
        )
        self.assertEqual(123400000, result)

    def test_calculate_synthetic_amount_whole_number(self):
        result = self.signer._calculate_synthetic_amount(
            synthetic_amount=Decimal("5"),
            synthetic_resolution=10**8,
        )
        self.assertEqual(500000000, result)

    def test_calculate_fee_amount_rounds_up(self):
        result = self.signer._calculate_fee_amount(
            collateral_amount=1000000,
            max_fee_rate=Decimal("0.001"),
            builder_fee=None,
        )
        self.assertEqual(1000, result)

    def test_calculate_fee_amount_with_builder_fee(self):
        result = self.signer._calculate_fee_amount(
            collateral_amount=1000000,
            max_fee_rate=Decimal("0.001"),
            builder_fee=Decimal("500"),
        )
        self.assertEqual(1500, result)

    def test_calculate_fee_amount_rounds_up_fractional(self):
        result = self.signer._calculate_fee_amount(
            collateral_amount=999,
            max_fee_rate=Decimal("0.001"),
            builder_fee=None,
        )
        self.assertEqual(1, result)

    @patch('time.time')
    def test_calculate_expiration_testnet_buffer(self, mock_time):
        mock_time.return_value = 1700000000.0
        order_expiration_ms = 1700100000000

        result = self.signer._calculate_expiration(order_expiration_ms)

        buffer_sec = 14 * 86400
        expected = 1700100000 + buffer_sec
        max_testnet_expiry = 1700000000 + (28 * 86400)

        self.assertEqual(min(expected, max_testnet_expiry), result)

    @patch('time.time')
    def test_calculate_expiration_mainnet_buffer(self, mock_time):
        mock_time.return_value = 1700000000.0

        mainnet_signer = ExtendedPerpetualSigner(
            private_key=self.private_key,
            public_key=self.public_key,
            vault_id=self.vault_id,
            is_testnet=False,
        )

        order_expiration_ms = 1700100000000
        result = mainnet_signer._calculate_expiration(order_expiration_ms)

        buffer_sec = 14 * 86400
        expected = 1700100000 + buffer_sec
        max_mainnet_expiry = 1700000000 + (90 * 86400)

        self.assertEqual(min(expected, max_mainnet_expiry), result)

    @patch('time.time')
    def test_calculate_expiration_clamped_to_max_testnet(self, mock_time):
        mock_time.return_value = 1700000000.0
        very_far_expiration_ms = 1900000000000

        result = self.signer._calculate_expiration(very_far_expiration_ms)

        max_testnet_expiry = 1700000000 + (28 * 86400)
        self.assertEqual(max_testnet_expiry, result)

    @patch('time.time')
    def test_calculate_expiration_clamped_to_max_mainnet(self, mock_time):
        mock_time.return_value = 1700000000.0

        mainnet_signer = ExtendedPerpetualSigner(
            private_key=self.private_key,
            public_key=self.public_key,
            vault_id=self.vault_id,
            is_testnet=False,
        )

        very_far_expiration_ms = 1900000000000
        result = mainnet_signer._calculate_expiration(very_far_expiration_ms)

        max_mainnet_expiry = 1700000000 + (90 * 86400)
        self.assertEqual(max_mainnet_expiry, result)

    def test_domain_initialization_testnet(self):
        self.assertEqual("SN_SEPOLIA", self.signer._domain.chain_id)
        self.assertEqual("Perpetuals", self.signer._domain.name)
        self.assertEqual("v0", self.signer._domain.version)

    def test_domain_initialization_mainnet(self):
        mainnet_signer = ExtendedPerpetualSigner(
            private_key=self.private_key,
            public_key=self.public_key,
            vault_id=self.vault_id,
            is_testnet=False,
        )
        self.assertEqual("SN_MAIN", mainnet_signer._domain.chain_id)

    def test_public_key_hex_normalized(self):
        signer_with_prefix = ExtendedPerpetualSigner(
            private_key="0x123",
            public_key="0xabc",
            vault_id=1,
            is_testnet=True,
        )
        self.assertEqual("0xabc", signer_with_prefix._public_key_hex)

        signer_without_prefix = ExtendedPerpetualSigner(
            private_key="123",
            public_key="abc",
            vault_id=1,
            is_testnet=True,
        )
        self.assertEqual("0xabc", signer_without_prefix._public_key_hex)

    @patch.object(ExtendedPerpetualSigner, '_sign_message')
    @patch.object(ExtendedPerpetualSigner, '_compute_message_hash')
    @patch.object(ExtendedPerpetualSigner, 'generate_nonce')
    @patch('time.time')
    def test_build_order_settlement_buy_order(self, mock_time, mock_nonce, mock_hash, mock_sign):
        mock_time.return_value = 1700000000.0
        mock_nonce.return_value = 12345
        mock_hash.return_value = 0xabcdef
        mock_sign.return_value = (111111, 222222)

        settlement = self.signer.build_order_settlement(
            side="buy",
            synthetic_amount=Decimal("1.0"),
            price=Decimal("100.0"),
            synthetic_asset_id="0x2",
            collateral_asset_id="0x1",
            synthetic_resolution=10**8,
            collateral_resolution=10**6,
            max_fee_rate=Decimal("0.001"),
            expiration_ms=1700100000000,
            builder_fee=None,
        )

        self.assertIsInstance(settlement, OrderSettlement)
        self.assertEqual(111111, settlement.r)
        self.assertEqual(222222, settlement.s)
        self.assertEqual(self.signer._public_key_hex, settlement.stark_key)
        self.assertEqual(self.vault_id, settlement.collateral_position)
        self.assertEqual(12345, settlement.nonce)

    @patch.object(ExtendedPerpetualSigner, '_sign_message')
    @patch.object(ExtendedPerpetualSigner, '_compute_message_hash')
    @patch.object(ExtendedPerpetualSigner, 'generate_nonce')
    @patch('time.time')
    def test_build_order_settlement_sell_order(self, mock_time, mock_nonce, mock_hash, mock_sign):
        mock_time.return_value = 1700000000.0
        mock_nonce.return_value = 54321
        mock_hash.return_value = 0x123456
        mock_sign.return_value = (333333, 444444)

        settlement = self.signer.build_order_settlement(
            side="sell",
            synthetic_amount=Decimal("2.5"),
            price=Decimal("50.0"),
            synthetic_asset_id="0x2",
            collateral_asset_id="0x1",
            synthetic_resolution=10**8,
            collateral_resolution=10**6,
            max_fee_rate=Decimal("0.0005"),
            expiration_ms=1700200000000,
            builder_fee=None,
        )

        self.assertEqual(333333, settlement.r)
        self.assertEqual(444444, settlement.s)
        self.assertEqual(54321, settlement.nonce)

    def test_to_settlement_dict_format(self):
        settlement = OrderSettlement(
            r=0xabc123,
            s=0xdef456,
            stark_key="0x5d05989e9302dcebc74e241001e3e3ac3f4402ccf2f8e6f74b034b07ad6a904",
            collateral_position=100,
            nonce=12345,
            expiration_seconds=1700000000,
        )

        result = self.signer.to_settlement_dict(settlement)

        self.assertIn("signature", result)
        self.assertEqual(hex(0xabc123), result["signature"]["r"])
        self.assertEqual(hex(0xdef456), result["signature"]["s"])
        self.assertEqual("0x5d05989e9302dcebc74e241001e3e3ac3f4402ccf2f8e6f74b034b07ad6a904", result["starkKey"])
        self.assertEqual(100, result["collateralPosition"])
        self.assertEqual(12345, result["nonce"])
        self.assertEqual(1700000000, result["expirationSeconds"])

    @patch.object(ExtendedPerpetualSigner, '_sign_message')
    @patch.object(ExtendedPerpetualSigner, 'generate_nonce')
    @patch('time.time')
    def test_sign_cancel_order(self, mock_time, mock_nonce, mock_sign):
        mock_time.return_value = 1700000000.0
        mock_nonce.return_value = 99999
        mock_sign.return_value = (555555, 666666)

        result = self.signer.sign_cancel_order(
            order_id="12345",
            expiration_ms=1700100000000,
        )

        self.assertIn("orderId", result)
        self.assertEqual("12345", result["orderId"])
        self.assertIn("signature", result)
        self.assertEqual(hex(555555), result["signature"]["r"])
        self.assertEqual(hex(666666), result["signature"]["s"])
        self.assertIn("starkKey", result)
        self.assertEqual(self.signer._public_key_hex, result["starkKey"])
        self.assertIn("nonce", result)
        self.assertEqual(99999, result["nonce"])
        self.assertIn("expirationSeconds", result)

    @patch.object(ExtendedPerpetualSigner, '_sign_message')
    @patch.object(ExtendedPerpetualSigner, 'generate_nonce')
    @patch('time.time')
    def test_sign_cancel_order_with_hex_order_id(self, mock_time, mock_nonce, mock_sign):
        mock_time.return_value = 1700000000.0
        mock_nonce.return_value = 11111
        mock_sign.return_value = (777777, 888888)

        result = self.signer.sign_cancel_order(
            order_id="0xabc123",
            expiration_ms=1700100000000,
        )

        self.assertEqual("0xabc123", result["orderId"])


class ExtendedPerpetualSignerAmountScalingTests(TestCase):
    def setUp(self) -> None:
        self.signer = ExtendedPerpetualSigner(
            private_key="0x123",
            public_key="0x456",
            vault_id=1,
            is_testnet=True,
        )

    def test_amount_scaling_with_high_resolution(self):
        result = self.signer._calculate_synthetic_amount(
            synthetic_amount=Decimal("0.001"),
            synthetic_resolution=10**18,
        )
        self.assertEqual(10**15, result)

    def test_amount_scaling_with_low_resolution(self):
        result = self.signer._calculate_synthetic_amount(
            synthetic_amount=Decimal("100"),
            synthetic_resolution=10**2,
        )
        self.assertEqual(10000, result)

    def test_collateral_scaling_buy_exact(self):
        scaled_amount, is_buy = self.signer._calculate_collateral_amount(
            side="buy",
            synthetic_amount=Decimal("1.0"),
            price=Decimal("100.0"),
            collateral_resolution=10**6,
        )
        self.assertEqual(100000000, scaled_amount)
        self.assertTrue(is_buy)

    def test_collateral_scaling_sell_exact(self):
        scaled_amount, is_buy = self.signer._calculate_collateral_amount(
            side="sell",
            synthetic_amount=Decimal("1.0"),
            price=Decimal("100.0"),
            collateral_resolution=10**6,
        )
        self.assertEqual(100000000, scaled_amount)
        self.assertFalse(is_buy)


class ExtendedPerpetualSignerConstantsTests(TestCase):
    def test_expiration_buffer_days(self):
        self.assertEqual(14, ExtendedPerpetualSigner.EXPIRATION_BUFFER_DAYS)

    def test_seconds_per_day(self):
        self.assertEqual(86400, ExtendedPerpetualSigner.SECONDS_PER_DAY)

    def test_max_u32(self):
        self.assertEqual(2**32 - 1, ExtendedPerpetualSigner.MAX_U32)
