from decimal import Decimal

from pydantic import Field, SecretStr

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap
from hummingbot.core.data_type.trade_fee import TradeFeeSchema

# Default fees for Vest Perpetual (conservative estimates)
# Taker: 0.05%, Maker: 0.02% (adjust based on actual Vest fee structure)
DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0.0002"),
    taker_percent_fee_decimal=Decimal("0.0005"),
    buy_percent_fee_deducted_from_returns=True
)

CENTRALIZED = True

EXAMPLE_PAIR = "BTC-USDC"


class VestPerpetualConfigMap(BaseConnectorConfigMap):
    """Configuration map for Vest Perpetual connector.

    Required credentials:
    - API key: JWT token from /register endpoint
    - Signing private key: EVM private key for signing orders (NOT your Rabby wallet key)
    - Account group: The account group number from /register response
    """
    connector: str = "vest_perpetual"

    vest_perpetual_api_key: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Vest API key (JWT token from /register endpoint)",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )

    vest_perpetual_signing_private_key: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Vest signing private key (API keypair private key, NOT your Rabby wallet key)",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )

    vest_perpetual_account_group: int = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Vest account group (accGroup from /register response)",
            "is_secure": False,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )


KEYS = VestPerpetualConfigMap.model_construct()


def convert_to_exchange_trading_pair(hb_trading_pair: str) -> str:
    """Convert Hummingbot trading pair to Vest exchange symbol.

    Hummingbot format: "BTC-USDC", "ETH-USDC", "AAPL-USDC"
    Vest format: "BTC-PERP", "ETH-PERP", "AAPL-USD-PERP"

    Args:
        hb_trading_pair: Hummingbot format trading pair

    Returns:
        Vest exchange symbol
    """
    if "-" not in hb_trading_pair:
        return hb_trading_pair

    parts = hb_trading_pair.split("-")
    base = parts[0]

    # For crypto perpetuals, use format: BASE-PERP
    # For stock perpetuals, use format: BASE-USD-PERP
    # Determine if it's a crypto or stock symbol by checking if base is all uppercase and short
    if len(base) <= 5 and base.isupper() and base in ["BTC", "ETH", "SOL", "AVAX", "DOGE"]:
        # Crypto perpetual
        return f"{base}-PERP"
    else:
        # Stock or other perpetual
        return f"{base}-USD-PERP"


def convert_from_exchange_trading_pair(exchange_symbol: str) -> str:
    """Convert Vest exchange symbol to Hummingbot trading pair.

    Vest format: "BTC-PERP", "ETH-PERP", "AAPL-USD-PERP"
    Hummingbot format: "BTC-USDC", "ETH-USDC", "AAPL-USDC"

    Args:
        exchange_symbol: Vest exchange symbol

    Returns:
        Hummingbot format trading pair
    """
    if "-PERP" not in exchange_symbol:
        return exchange_symbol

    # Remove -PERP suffix
    if exchange_symbol.endswith("-PERP"):
        base_part = exchange_symbol[:-5]  # Remove "-PERP"

        # Check if it's in format BASE-USD-PERP
        if base_part.endswith("-USD"):
            base = base_part[:-4]  # Remove "-USD"
        else:
            base = base_part

        # All Vest perpetuals settle in USDC
        return f"{base}-USDC"

    return exchange_symbol
