from decimal import Decimal
from typing import Any, Dict, Optional

from pydantic import ConfigDict, Field, SecretStr

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap
from hummingbot.core.data_type.trade_fee import TradeFeeSchema

DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0.0002"),
    taker_percent_fee_decimal=Decimal("0.0005"),
    buy_percent_fee_deducted_from_returns=True
)

CENTRALIZED = True

EXAMPLE_PAIR = "BTC-USD"

BROKER_ID = "HBOT"


def is_exchange_information_valid(rule: Dict[str, Any]) -> bool:
    """
    Verifies if a trading pair is enabled to operate with based on its exchange information.

    :param rule: the exchange information for a trading pair
    :return: True if the trading pair is enabled, False otherwise
    """
    return True


def convert_to_exchange_trading_pair(hb_trading_pair: str) -> str:
    """
    Converts Hummingbot trading pair format (BASE-QUOTE) to exchange format.
    Extended uses BASE-USD format for perpetuals.

    :param hb_trading_pair: trading pair in Hummingbot format (e.g., "BTC-USD")
    :return: trading pair in exchange format
    """
    return hb_trading_pair


def convert_from_exchange_trading_pair(exchange_trading_pair: str) -> str:
    """
    Converts exchange trading pair format to Hummingbot format (BASE-QUOTE).

    :param exchange_trading_pair: trading pair in exchange format
    :return: trading pair in Hummingbot format (e.g., "BTC-USD")
    """
    return exchange_trading_pair


class ExtendedPerpetualConfigMap(BaseConnectorConfigMap):
    connector: str = "extended_perpetual"
    extended_perpetual_api_key: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Extended API key",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )
    extended_perpetual_api_secret: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Extended API secret",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )
    extended_perpetual_account_address: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Starknet account address",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )
    model_config = ConfigDict(title="extended_perpetual")


KEYS = ExtendedPerpetualConfigMap.model_construct()

OTHER_DOMAINS = ["extended_perpetual_testnet"]
OTHER_DOMAINS_PARAMETER = {"extended_perpetual_testnet": "extended_perpetual_testnet"}
OTHER_DOMAINS_EXAMPLE_PAIR = {"extended_perpetual_testnet": "BTC-USD"}
OTHER_DOMAINS_DEFAULT_FEES = {"extended_perpetual_testnet": [0.02, 0.05]}


class ExtendedPerpetualTestnetConfigMap(BaseConnectorConfigMap):
    connector: str = "extended_perpetual_testnet"
    extended_perpetual_testnet_api_key: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Extended testnet API key",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )
    extended_perpetual_testnet_api_secret: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Extended testnet API secret",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )
    extended_perpetual_testnet_account_address: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Starknet testnet account address",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )
    model_config = ConfigDict(title="extended_perpetual_testnet")


OTHER_DOMAINS_KEYS = {
    "extended_perpetual_testnet": ExtendedPerpetualTestnetConfigMap.model_construct()
}
