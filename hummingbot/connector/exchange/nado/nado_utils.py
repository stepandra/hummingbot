import numbers
import time
from decimal import Decimal
from random import randint
from typing import Any, Dict, Optional

from pydantic import ConfigDict, Field, SecretStr

import hummingbot.connector.exchange.nado.nado_constants as CONSTANTS
from hummingbot.client.config.config_data_types import BaseConnectorConfigMap
from hummingbot.core.data_type.trade_fee import TradeFeeSchema

CENTRALIZED = True
USE_ETHEREUM_WALLET = False
EXAMPLE_PAIR = "WBTC-USDT0"
DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0.0"),
    taker_percent_fee_decimal=Decimal("0.0002"),
)


def hex_to_bytes32(hex_string: str) -> bytes:
    if hex_string.startswith("0x"):
        hex_string = hex_string[2:]
    data_bytes = bytes.fromhex(hex_string)
    padded_data = data_bytes + b"\x00" * (32 - len(data_bytes))
    return padded_data


def convert_timestamp(timestamp: Any) -> float:
    return float(timestamp) / 1e9


def trading_pair_to_product_id(
    trading_pair: str, exchange_market_info: Dict, is_perp: Optional[bool] = False
) -> int:
    tp = trading_pair.replace("-", "/")
    for product_id in exchange_market_info:
        if is_perp and "perp" not in exchange_market_info[product_id]["symbol"].lower():
            continue
        if exchange_market_info[product_id]["market"] == tp:
            return product_id
    return -1


def market_to_trading_pair(market: str) -> str:
    """Converts a market symbol from Nado to a trading pair."""
    return market.replace("/", "-")


def convert_from_x18(data: Any, precision: Optional[Decimal] = None) -> Any:
    """
    Converts numerical data encoded as x18 to a string representation of a
    floating point number, recursively applies the conversion for other data types.
    """
    if data is None:
        return None

    # Check if data type is str or float
    if isinstance(data, str) or isinstance(data, numbers.Number):
        data = Decimal(data) / Decimal("1000000000000000000")  # type: ignore
        if precision:
            data = data.quantize(precision)
        return str(data)

    if isinstance(data, dict):
        for k, v in data.items():
            data[k] = convert_from_x18(v, precision)
    elif isinstance(data, list):
        for i in range(0, len(data)):
            data[i] = convert_from_x18(data[i], precision)
    else:
        raise TypeError(
            "Data is of unsupported type for convert_from_x18 to process", data
        )
    return data


def convert_to_x18(data: Any, precision: Optional[Decimal] = None) -> Any:
    """
    Converts numerical data encoded to a string representation of x18, recursively
    applies the conversion for other data types.
    """
    if data is None:
        return None

    # Check if data type is str or float
    if isinstance(data, str) or isinstance(data, numbers.Number):
        data = Decimal(str(data))  # type: ignore
        if precision:
            data = data.quantize(precision)
        return str((data * Decimal("1000000000000000000")).quantize(Decimal("1")))

    if isinstance(data, dict):
        for k, v in data.items():
            data[k] = convert_to_x18(v, precision)
    elif isinstance(data, list):
        for i in range(0, len(data)):
            data[i] = convert_to_x18(data[i], precision)
    else:
        raise TypeError(
            "Data is of unsupported type for convert_to_x18 to process", data
        )
    return data


def generate_expiration(timestamp: float = None, expiry_seconds: int = 86400) -> str:
    if timestamp is None:
        timestamp = time.time()
    unix_epoch = int(timestamp)
    return str(unix_epoch + expiry_seconds)


def generate_nonce(timestamp: float, expiry_ms: int = 90) -> int:
    unix_epoch_ms = int((timestamp * 1000) + (expiry_ms * 1000))
    nonce = (unix_epoch_ms << 20) + randint(1, 1001)
    return nonce


def convert_address_to_sender(address: str) -> str:
    # NOTE: the sender address includes the subaccount, which is "default" by default, you cannot interact with
    # subaccounts outside of default on the UI currently.
    # https://docs.nado.xyz/developer-resources/api/gateway/signing
    if isinstance(address, str):
        default_12bytes = "64656661756c740000000000"
        return address + default_12bytes
    raise TypeError("Address must be of type string")


def generate_order_verifying_contract(product_id: int) -> str:
    be_bytes = product_id.to_bytes(20, byteorder="big", signed=False)
    return "0x" + be_bytes.hex()


def build_order_appendix(order_type: str, version: int = 1) -> int:
    order_type_map = {
        CONSTANTS.TIME_IN_FORCE_GTC: 0,
        CONSTANTS.TIME_IN_FORCE_IOC: 1,
        CONSTANTS.TIME_IN_FORCE_FOK: 2,
        CONSTANTS.TIME_IN_FORCE_POSTONLY: 3,
    }
    order_type_value = order_type_map.get(order_type, 0)
    return (version & 0xFF) | ((order_type_value & 0x3) << 9)


def is_exchange_information_valid(exchange_info: Dict[str, Any]) -> bool:
    """
    Default's to true, there isn't anything to check agaisnt.
    """
    return True


class NadoConfigMap(BaseConnectorConfigMap):
    connector: str = "nado"
    nado_ink_private_key: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Ink private key",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        },
    )
    nado_ink_address: str = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Ink wallet address",
            "is_secure": False,
            "is_connect_key": True,
            "prompt_on_new": True,
        },
    )
    model_config = ConfigDict(title="nado")


KEYS = NadoConfigMap.model_construct()


class NadoTestnetConfigMap(BaseConnectorConfigMap):
    connector: str = "nado_testnet"
    nado_testnet_ink_private_key: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Ink TESTNET private key",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        },
    )
    nado_testnet_ink_address: str = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Ink TESTNET wallet address",
            "is_secure": False,
            "is_connect_key": True,
            "prompt_on_new": True,
        },
    )
    model_config = ConfigDict(title="nado_testnet")


OTHER_DOMAINS = ["nado_testnet"]
OTHER_DOMAINS_PARAMETER = {"nado_testnet": "nado_testnet"}
OTHER_DOMAINS_EXAMPLE_PAIR = {"nado_testnet": "WBTC-USDT0"}
OTHER_DOMAINS_DEFAULT_FEES = {"nado_testnet": DEFAULT_FEES}

OTHER_DOMAINS_KEYS = {"nado_testnet": NadoTestnetConfigMap.model_construct()}
