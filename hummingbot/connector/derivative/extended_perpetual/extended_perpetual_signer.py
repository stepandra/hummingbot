import math
import random
import time
from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_UP, Decimal
from typing import Any, Dict, Optional, Tuple

from fast_stark_crypto import get_order_msg_hash, sign

import hummingbot.connector.derivative.extended_perpetual.extended_perpetual_constants as CONSTANTS


@dataclass
class StarknetDomain:
    """SNIP-12 domain separator for Extended Perpetual."""
    name: str = "Perpetuals"
    version: str = "v0"
    chain_id: str = "SN_MAIN"
    revision: str = "1"


@dataclass
class OrderSettlement:
    """Order settlement data including signature."""
    r: int
    s: int
    stark_key: str
    collateral_position: int
    nonce: int
    expiration_seconds: int


class ExtendedPerpetualSigner:
    """
    SNIP-12 Stark signature implementation for Extended Perpetual orders.
    
    This class handles the signing of orders following the Starknet SNIP-12 standard
    using Stark ECDSA signatures.
    """
    
    EXPIRATION_BUFFER_DAYS = 14
    SECONDS_PER_DAY = 86400
    MAX_U32 = 2**32 - 1

    def __init__(
        self,
        private_key: str,
        public_key: str,
        vault_id: int,
        is_testnet: bool = False
    ):
        """
        Initialize the signer.
        
        :param private_key: Stark private key as hex string (with or without 0x prefix)
        :param public_key: Stark public key as hex string (with or without 0x prefix)
        :param vault_id: Vault/collateral position ID
        :param is_testnet: Whether to use testnet chain ID
        """
        self._private_key = self._parse_hex_key(private_key)
        self._public_key = self._parse_hex_key(public_key)
        self._public_key_hex = self._normalize_hex(public_key)
        self._vault_id = vault_id
        self._is_testnet = is_testnet
        self._domain = StarknetDomain(
            chain_id="SN_SEPOLIA" if is_testnet else "SN_MAIN"
        )

    @staticmethod
    def _parse_hex_key(hex_str: str) -> int:
        """Parse hex string to integer, handling 0x prefix."""
        if hex_str.startswith("0x") or hex_str.startswith("0X"):
            return int(hex_str, 16)
        return int(hex_str, 16)

    @staticmethod
    def _normalize_hex(hex_str: str) -> str:
        """Normalize hex string to include 0x prefix."""
        if hex_str.startswith("0x") or hex_str.startswith("0X"):
            return hex_str
        return "0x" + hex_str

    def generate_nonce(self) -> int:
        """Generate a random u32 nonce."""
        return random.randint(0, self.MAX_U32)

    def _calculate_collateral_amount(
        self,
        side: str,
        synthetic_amount: Decimal,
        price: Decimal,
        collateral_resolution: int,
    ) -> Tuple[int, bool]:
        """
        Calculate collateral amount with proper rounding.
        
        For buy orders: ROUND_UP (paying more collateral)
        For sell orders: ROUND_DOWN (receiving less collateral)
        
        :returns: Tuple of (scaled_amount, is_buy)
        """
        is_buy = side.lower() == "buy"
        raw_collateral = synthetic_amount * price
        scaled = raw_collateral * collateral_resolution
        
        if is_buy:
            result = int(scaled.quantize(Decimal(1), rounding=ROUND_UP))
        else:
            result = int(scaled.quantize(Decimal(1), rounding=ROUND_DOWN))
        
        return result, is_buy

    def _calculate_synthetic_amount(
        self,
        synthetic_amount: Decimal,
        synthetic_resolution: int,
    ) -> int:
        """
        Calculate scaled synthetic amount.
        Scales the amount by resolution and rounds up to be conservative.
        """
        scaled = synthetic_amount * synthetic_resolution
        return int(scaled.quantize(Decimal(1), rounding=ROUND_UP))

    def _calculate_fee_amount(
        self,
        collateral_amount: int,
        max_fee_rate: Decimal,
        builder_fee: Optional[Decimal] = None,
    ) -> int:
        """
        Calculate fee amount. Always ROUND_UP to be conservative.
        
        :param collateral_amount: Collateral amount (already scaled)
        :param max_fee_rate: Maximum fee rate as decimal (e.g., 0.001 for 0.1%)
        :param builder_fee: Optional additional builder fee
        """
        fee = Decimal(collateral_amount) * max_fee_rate
        if builder_fee is not None:
            fee += builder_fee
        return int(fee.quantize(Decimal(1), rounding=ROUND_UP))

    def _calculate_expiration(self, order_expiration_ms: int) -> int:
        """
        Calculate signature expiration with 14-day buffer.
        
        :param order_expiration_ms: Order expiration in milliseconds
        :return: Signature expiration in seconds
        """
        order_expiration_sec = order_expiration_ms // 1000
        buffer_sec = self.EXPIRATION_BUFFER_DAYS * self.SECONDS_PER_DAY
        max_expiry_days = (
            CONSTANTS.ORDER_EXPIRY_TESTNET_MAX_DAYS if self._is_testnet 
            else CONSTANTS.ORDER_EXPIRY_MAINNET_MAX_DAYS
        )
        max_expiry_sec = int(time.time()) + (max_expiry_days * self.SECONDS_PER_DAY)
        
        return min(order_expiration_sec + buffer_sec, max_expiry_sec)

    def _compute_message_hash(
        self,
        synthetic_asset_id: int,
        collateral_asset_id: int,
        is_buying_synthetic: bool,
        synthetic_amount: int,
        collateral_amount: int,
        fee_limit: int,
        nonce: int,
        expiration: int,
    ) -> int:
        """
        Compute SNIP-12 message hash for order signing.
        
        Uses the fast_stark_crypto library for efficient hash computation.
        """
        base_amount = synthetic_amount if is_buying_synthetic else -synthetic_amount
        quote_amount = -collateral_amount if is_buying_synthetic else collateral_amount
        
        return get_order_msg_hash(
            position_id=self._vault_id,
            base_asset_id=synthetic_asset_id,
            base_amount=base_amount,
            quote_asset_id=collateral_asset_id,
            quote_amount=quote_amount,
            fee_asset_id=collateral_asset_id,
            fee_amount=fee_limit,
            expiration=expiration,
            salt=nonce,
            user_public_key=self._public_key,
            domain_name=self._domain.name,
            domain_version=self._domain.version,
            domain_chain_id=self._domain.chain_id,
            domain_revision=self._domain.revision,
        )

    def _sign_message(self, message_hash: int) -> Tuple[int, int]:
        """
        Sign a message hash using Stark ECDSA.
        
        :returns: Tuple of (r, s) signature components
        """
        r, s = sign(message_hash, self._private_key)
        return r, s

    def build_order_settlement(
        self,
        side: str,
        synthetic_amount: Decimal,
        price: Decimal,
        synthetic_asset_id: str,
        collateral_asset_id: str,
        synthetic_resolution: int,
        collateral_resolution: int,
        max_fee_rate: Decimal,
        expiration_ms: int,
        builder_fee: Optional[Decimal] = None,
    ) -> OrderSettlement:
        """
        Build a signed order settlement for Extended Perpetual.
        
        Following SDK logic:
        1. Calculate amounts with proper rounding
        2. Scale by resolution
        3. Apply sign convention (negative = outgoing)
        4. Calculate expiration with 14-day buffer
        5. Generate nonce
        6. Compute SNIP-12 message hash
        7. Sign with Stark ECDSA
        8. Return settlement object
        
        :param side: Order side ("buy" or "sell")
        :param synthetic_amount: Base asset amount
        :param price: Limit price
        :param synthetic_asset_id: Hex asset ID for synthetic
        :param collateral_asset_id: Hex asset ID for collateral
        :param synthetic_resolution: Synthetic asset resolution/decimals
        :param collateral_resolution: Collateral asset resolution/decimals
        :param max_fee_rate: Maximum fee rate as decimal
        :param expiration_ms: Order expiration in milliseconds
        :param builder_fee: Optional builder fee
        :return: Signed OrderSettlement
        """
        synthetic_asset_int = self._parse_hex_key(synthetic_asset_id)
        collateral_asset_int = self._parse_hex_key(collateral_asset_id)
        
        scaled_synthetic = self._calculate_synthetic_amount(
            synthetic_amount, synthetic_resolution
        )
        scaled_collateral, is_buy = self._calculate_collateral_amount(
            side, synthetic_amount, price, collateral_resolution
        )
        fee_limit = self._calculate_fee_amount(
            scaled_collateral, max_fee_rate, builder_fee
        )
        
        nonce = self.generate_nonce()
        expiration = self._calculate_expiration(expiration_ms)
        
        message_hash = self._compute_message_hash(
            synthetic_asset_id=synthetic_asset_int,
            collateral_asset_id=collateral_asset_int,
            is_buying_synthetic=is_buy,
            synthetic_amount=scaled_synthetic,
            collateral_amount=scaled_collateral,
            fee_limit=fee_limit,
            nonce=nonce,
            expiration=expiration,
        )
        
        r, s = self._sign_message(message_hash)
        
        return OrderSettlement(
            r=r,
            s=s,
            stark_key=self._public_key_hex,
            collateral_position=self._vault_id,
            nonce=nonce,
            expiration_seconds=expiration,
        )

    def to_settlement_dict(self, settlement: OrderSettlement) -> Dict[str, Any]:
        """
        Convert OrderSettlement to API-compatible dictionary format.
        
        :param settlement: The order settlement to convert
        :return: Dictionary for API submission
        """
        return {
            "signature": {
                "r": hex(settlement.r),
                "s": hex(settlement.s),
            },
            "starkKey": settlement.stark_key,
            "collateralPosition": settlement.collateral_position,
            "nonce": settlement.nonce,
            "expirationSeconds": settlement.expiration_seconds,
        }

    def sign_cancel_order(
        self,
        order_id: str,
        expiration_ms: int,
    ) -> Dict[str, Any]:
        """
        Sign an order cancellation request.
        
        :param order_id: The order ID to cancel
        :param expiration_ms: Cancellation expiration in milliseconds
        :return: Signed cancellation payload
        """
        nonce = self.generate_nonce()
        expiration = self._calculate_expiration(expiration_ms)
        
        order_id_int = self._parse_hex_key(order_id) if order_id.startswith("0x") else int(order_id)
        
        message_hash = get_order_msg_hash(
            position_id=self._vault_id,
            base_asset_id=0,
            base_amount=0,
            quote_asset_id=0,
            quote_amount=0,
            fee_asset_id=0,
            fee_amount=0,
            expiration=expiration,
            salt=nonce,
            user_public_key=self._public_key,
            domain_name=self._domain.name,
            domain_version=self._domain.version,
            domain_chain_id=self._domain.chain_id,
            domain_revision=self._domain.revision,
        )
        
        r, s = self._sign_message(message_hash)
        
        return {
            "orderId": order_id,
            "signature": {
                "r": hex(r),
                "s": hex(s),
            },
            "starkKey": self._public_key_hex,
            "nonce": nonce,
            "expirationSeconds": expiration,
        }
