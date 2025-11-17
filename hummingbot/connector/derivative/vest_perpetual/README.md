# Vest Perpetual Connector - Implementation Status

## Overview

This directory contains the Vest Perpetual connector for Hummingbot. The implementation follows the architecture described in `vest_perpetual_connector_tasks.md`.

## Implementation Status

### ✅ Completed Components

#### 1. Infrastructure and Configuration (100%)
- **dummy.pxd / dummy.pyx**: Cython stub files
- **vest_perpetual_constants.py**: All REST/WS endpoints, rate limits, order states
  - REST base URLs (prod/dev)
  - WebSocket URLs
  - All API endpoints (exchangeInfo, depth, orders, account, listenKey, etc.)
  - Rate limits configuration
  - Order state mappings
  - **Tests**: `test_vest_perpetual_constants.py` ✅

#### 2. Web Utilities (100%)
- **vest_perpetual_web_utils.py**: URL building and API factory
  - `public_rest_url()` - Build public REST URLs
  - `private_rest_url()` - Build private REST URLs
  - `public_ws_url()` - Build public WebSocket URLs with account_group
  - `private_ws_url()` - Build private WebSocket URLs with listenKey
  - `build_api_factory()` - Create web assistants factory
  - `create_throttler()` - Create rate limiter
  - `is_exchange_information_valid()` - Validate trading pair status
  - **Tests**: `test_vest_perpetual_web_utils.py` ✅

#### 3. Configuration and Utils (100%)
- **vest_perpetual_utils.py**: Config map, fees, symbol conversion
  - `VestPerpetualConfigMap`: Complete configuration schema
    - `vest_perpetual_api_key`: JWT API key
    - `vest_perpetual_signing_private_key`: EVM private key for signing
    - `vest_perpetual_account_group`: Account group number
  - `DEFAULT_FEES`: Fee structure (maker/taker)
  - `convert_to_exchange_trading_pair()`: HB → Vest symbol conversion
  - `convert_from_exchange_trading_pair()`: Vest → HB symbol conversion
  - **Tests**: `test_vest_perpetual_utils.py` ✅

#### 4. Authentication (100%)
- **vest_perpetual_auth.py**: Complete EVM signature implementation
  - Headers: `X-API-KEY`, `xrestservermm`
  - `_generate_orders_signature()`: Sign POST /orders requests
  - `_generate_cancel_signature()`: Sign POST /orders/cancel requests
  - `_generate_lp_signature()`: Sign POST /lp requests
  - `_generate_withdraw_signature()`: Sign POST /transfer/withdraw requests
  - All signatures use keccak256 + EVM signing per Vest API spec
  - **Tests**: `test_vest_perpetual_auth.py` ✅
    - Tests for all signature types
    - Signature recovery verification
    - REST authentication flow

### ⚠️ Stub Implementations (Require Full Implementation)

#### 5. Order Book Data Source (10%)
- **vest_perpetual_api_order_book_data_source.py**: Minimal stub
- **TODO**: Implement following `hyperliquid_perpetual_api_order_book_data_source.py` pattern:
  - REST snapshot fetching (`GET /depth`)
  - Funding info retrieval (`GET /funding/history`)
  - WebSocket subscriptions (`{symbol}@depth`, `{symbol}@trades`)
  - Message parsers: `_parse_order_book_diff_message`, `_parse_trade_message`
  - Channel routing: `_channel_originating_message`
- **Tests**: Not yet implemented

#### 6. User Stream Data Source (10%)
- **vest_perpetual_user_stream_data_source.py**: Minimal stub
- **TODO**: Implement following `binance_perpetual_user_stream_data_source.py` pattern:
  - ListenKey lifecycle: `_get_listen_key`, `_ping_listen_key`, `_delete_listen_key`
  - Private WebSocket connection with listenKey
  - Subscribe to `account_private` channel
  - Parse ORDER, LP, TRANSFER events
  - Event queue management
- **Tests**: Not yet implemented

#### 7. Main Derivative Connector (10%)
- **vest_perpetual_derivative.py**: Minimal stub
- **TODO**: Implement all abstract methods from:
  - `ExchangePyBase`: ~25 methods
  - `PerpetualDerivativePyBase`: ~8 methods
  - `PerpetualTrading`: Additional trading methods
  - Key methods needed:
    - `_place_order()`: Create orders via POST /orders
    - `_place_cancel()`: Cancel orders via POST /orders/cancel
    - `_update_balances()`: Fetch balances from GET /account
    - `_update_positions()`: Fetch positions from GET /account
    - `_set_trading_pair_leverage()`: Set leverage via POST /account/leverage
    - `_format_trading_rules()`: Parse trading rules from GET /exchangeInfo
    - `_user_stream_event_listener()`: Process ORDER/LP/TRANSFER events
    - And many more...
- **Tests**: Not yet implemented

## Test Coverage

### Current Coverage
- **Fully Tested**:
  - `vest_perpetual_constants.py` ✅
  - `vest_perpetual_web_utils.py` ✅
  - `vest_perpetual_utils.py` ✅
  - `vest_perpetual_auth.py` ✅

- **Not Tested**:
  - `vest_perpetual_api_order_book_data_source.py` ❌
  - `vest_perpetual_user_stream_data_source.py` ❌
  - `vest_perpetual_derivative.py` ❌

### Coverage Goal
- Target: >80% code coverage for all modules
- Current: ~50% (4 out of 7 main modules fully tested)

## Next Steps for Full Implementation

### Priority 1: Order Book Data Source
1. Implement REST methods:
   - `_request_order_book_snapshot()` using `GET /depth`
   - `get_funding_info()` using `GET /funding/history`
2. Implement WebSocket methods:
   - `_connected_websocket_assistant()` with public WS URL
   - `_subscribe_channels()` for depth and trades
   - `_channel_originating_message()` for message routing
   - `_parse_order_book_diff_message()`
   - `_parse_trade_message()`
3. Write comprehensive tests with `aioresponses` and `NetworkMockingAssistant`

### Priority 2: User Stream Data Source
1. Implement listenKey management:
   - `_get_listen_key()`: POST /account/listenKey
   - `_ping_listen_key()`: PUT /account/listenKey
   - `_delete_listen_key()`: DELETE /account/listenKey
   - `_manage_listen_key_task_loop()`: Periodic refresh
2. Implement WebSocket:
   - `_connected_websocket_assistant()` with private WS URL (includes listenKey)
   - `_subscribe_channels()` for account_private
   - `_process_user_stream_event()`: Parse ORDER/LP/TRANSFER
3. Write tests for listenKey lifecycle and event processing

### Priority 3: Main Derivative Connector
1. Implement core trading methods:
   - `_place_order()`: POST /orders with signature
   - `_place_cancel()`: POST /orders/cancel with signature
   - `_request_order_status()`: GET /orders
   - `_all_trade_updates_for_order()`: Parse fills from orders
2. Implement account management:
   - `_update_balances()`: GET /account → balances
   - `_update_positions()`: GET /account → positions
   - `_set_trading_pair_leverage()`: POST /account/leverage
3. Implement market data:
   - `_initialize_trading_pair_symbols_from_exchange_info()`: GET /exchangeInfo
   - `_format_trading_rules()`: Parse symbol rules
   - `_get_last_traded_price()`: GET /ticker/latest
4. Implement event handling:
   - `_user_stream_event_listener()`: Process ORDER/LP/TRANSFER → Events
   - `_status_polling_loop_fetch_updates()`: Polling fallback
5. Write extensive tests using generic test class pattern

### Priority 4: Integration and Testing
1. Register connector in Hummingbot:
   - Add to `connector_settings.py` or equivalent
   - Update `conf_global_TEMPLATE.yml` with config fields
2. End-to-end testing:
   - Manual testing with testnet
   - Integration tests with real API
3. Documentation:
   - Setup guide (how to get API keys, account_group)
   - Example configurations
   - Troubleshooting guide

## Architecture Reference

The implementation follows the standard Hummingbot perpetual connector architecture:

```
vest_perpetual_derivative.py (Main Connector)
    ├── VestPerpetualAuth (Authentication)
    ├── VestPerpetualAPIOrderBookDataSource (Market Data)
    │   ├── REST: /exchangeInfo, /depth, /ticker, /funding/history
    │   └── WebSocket: {symbol}@depth, {symbol}@trades
    ├── VestPerpetualUserStreamDataSource (Account Updates)
    │   ├── REST: /account/listenKey (POST/PUT/DELETE)
    │   └── WebSocket: account_private (ORDER, LP, TRANSFER events)
    └── Web Utilities (URL building, factories)
```

## API Documentation Reference

See `vest_perpetual_connector_tasks.md` for:
- Complete API endpoint mapping
- WebSocket channel formats
- Signature generation specifications
- Order event formats
- Detailed implementation requirements

## Testing

Run tests:
```bash
# Run all Vest perpetual tests
pytest test/hummingbot/connector/derivative/vest_perpetual/ -v

# Run specific test file
pytest test/hummingbot/connector/derivative/vest_perpetual/test_vest_perpetual_auth.py -v

# Run with coverage
coverage run -m pytest test/hummingbot/connector/derivative/vest_perpetual/
coverage report
```

## Contributing

When implementing remaining components:
1. Follow TDD approach (write tests first)
2. Reference equivalent implementations in `hyperliquid_perpetual`, `binance_perpetual`, `bybit_perpetual`
3. Use `aioresponses` for mocking REST requests
4. Use `NetworkMockingAssistant` for mocking WebSocket connections
5. Aim for >80% test coverage for each module
6. Document any deviations from Vest API docs

## Support

For questions or issues:
1. Review `vest_perpetual_connector_tasks.md` for detailed requirements
2. Check reference implementations in other perpetual connectors
3. Consult Vest API documentation: https://server-prod.hz.vestmarkets.com/docs (assumed)
