from decimal import Decimal

from pydantic import ConfigDict, Field, SecretStr

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap
from hummingbot.core.data_type.trade_fee import TradeFeeSchema

CENTRALIZED = True
USE_ETHEREUM_WALLET = False
EXAMPLE_PAIR = "BTC-PERP"
DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0.0"),
    taker_percent_fee_decimal=Decimal("0.0002"),
)


def is_exchange_information_valid(exchange_info):
    return True


class NadoPerpetualConfigMap(BaseConnectorConfigMap):
    connector: str = "nado_perpetual"
    nado_perpetual_ink_private_key: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Ink private key",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        },
    )
    nado_perpetual_ink_address: str = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Ink wallet address",
            "is_secure": False,
            "is_connect_key": True,
            "prompt_on_new": True,
        },
    )
    model_config = ConfigDict(title="nado_perpetual")


KEYS = NadoPerpetualConfigMap.model_construct()


class NadoPerpetualTestnetConfigMap(BaseConnectorConfigMap):
    connector: str = "nado_perpetual_testnet"
    nado_perpetual_testnet_ink_private_key: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Ink TESTNET private key",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        },
    )
    nado_perpetual_testnet_ink_address: str = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Ink TESTNET wallet address",
            "is_secure": False,
            "is_connect_key": True,
            "prompt_on_new": True,
        },
    )
    model_config = ConfigDict(title="nado_perpetual_testnet")


OTHER_DOMAINS = ["nado_perpetual_testnet"]
OTHER_DOMAINS_PARAMETER = {"nado_perpetual_testnet": "nado_perpetual_testnet"}
OTHER_DOMAINS_EXAMPLE_PAIR = {"nado_perpetual_testnet": "BTC-PERP"}
OTHER_DOMAINS_DEFAULT_FEES = {"nado_perpetual_testnet": DEFAULT_FEES}
OTHER_DOMAINS_KEYS = {
    "nado_perpetual_testnet": NadoPerpetualTestnetConfigMap.model_construct()
}
