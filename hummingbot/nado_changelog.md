# Nado API Changelog

This document tracks all changes to the Nado API.

## December 22, 2025

### Archive Indexer: Orders & Matches fields
* Added `closed_amount (x18)` and `realized_pnl (x18)` to archive indexer responses for both orders and matches.

---

## December 11, 2025

### Risk System Updates

#### Spread Weight Caps
* Introduced upper bounds for spread weights to manage risk at extreme leverage levels:
    * `initial_spread_weight`: Maximum 0.99
    * `maintenance_spread_weight`: Maximum 0.994
* **Impact:**
    * Existing markets (≤20x leverage): No change in behavior
    * Future high-leverage markets (30x+): Spread positions will have capped health benefits
    * Prevents extreme leverage abuse via spread positions
* **Technical Details:**
    * Base spread weight calculated as: `spread_weight = 1 - (1 - product_weight) / 5`
    * Final spread weight: `min(spread_weight, cap)`
    * Cap applies during health calculations for spread positions

#### Minimum Liquidation Penalties
* Introduced minimum distance requirements between oracle price and liquidation price:
    * Non-spread liquidations: Minimum 0.5% from oracle price
    * Spread liquidations: Minimum 0.25% from oracle price
* **Impact:**
    * Ensures liquidators always have sufficient incentive to execute liquidations
    * Prevents unprofitable liquidation scenarios for low-volatility assets
    * Particularly important for high-leverage positions where natural penalties may be very small
* **Technical Details:**
    * Non-spread longs: `oracle_price × (1 - max((1 - maint_asset_weight) / 5, 0.005))`
    * Non-spread shorts: `oracle_price × (1 + max((maint_liability_weight - 1) / 5, 0.005))`
    * Spread selling: `spot_price × (1 - max((1 - perp_maint_asset_weight) / 10, 0.0025))`
    * Spread buying: `spot_price × (1 + max((maint_liability_weight - 1) / 10, 0.0025))`

### API Response Changes
* No breaking changes to API response structure
* Health calculations and liquidation prices automatically reflect new risk parameters

### Documentation Updates
* See Subaccounts & Health for spread weight cap details
* See Liquidations for minimum liquidation penalty details

---

## December 1, 2025

### Query Enhancements

#### Pre-State Simulation for SubaccountInfo Query
* Added `pre_state` parameter to `SubaccountInfo` query
    * Type: string (accepts "true" or "false")
    * When set to "true" along with `txns`, returns a `pre_state` object in the response
    * `pre_state` contains the subaccount state before the simulated transactions were applied
    * Useful for comparing before/after states when simulating trades
    * `pre_state` includes:
        * `healths`: Health information before transactions
        * `health_contributions`: Per-product health contributions before transactions
        * `spot_balances`: Spot balances before transactions
        * `perp_balances`: Perpetual balances before transactions
* **Use Cases:**
    * Position simulation and preview
    * Risk analysis for potential trades
    * UI/UX for showing before/after comparisons
    * Testing transaction impacts without on-chain execution

---

## November 20, 2025 - Initial Launch

### Core Changes

1.  **Removal of LP Functionality**
    * `SubaccountInfo` no longer has:
        * `lp_balance` in `spot_balances` and `perp_balances`
        * `lp_state` in `spot_products` and `perp_products`
        * `lp_spread_x18` in `book_info` of both `spot_products` and `perp_products`
    * Historical events no longer include:
        * `net_entry_lp_unrealized`
        * `net_entry_lp_cumulative`

2.  **Removal of Redundant Fields**
    * `SubaccountInfo` no longer has:
        * `last_cumulative_multiplier_x18` in balance of `spot_balances`

3.  **Products Config Model Updates**
    * Added: `withdraw_fee_x18` and `min_deposit_rate_x18` to `spot_products.config`

4.  **Products Risk Model Updates**
    * Added: `price_x18` to both `spot_products.risk` and `perp_products.risk`
    * Removed: `large_position_penalty_x18`

5.  **Deposit Rate Query**
    * Removed: `min_deposit_rates` query
    * Use `min_deposit_rate_x18` in `spot_products.config` instead

### Market Structure Changes

6.  **Removal of Virtual Books**
    * `Contracts` query no longer returns `book_addrs`
    * `PlaceOrder` verify contract is now `address(product_id)`
    * Example: product 18 → `0x0000000000000000000000000000000000000012`

7.  **Minimum Size denomination**
    * `min_size` is now USDT0 denominated (not base denominated)
    * `min_size = 10` → minimum order size = 10 USDT0 (`order_price * order_amount`)
    * `size_increment` remains base denominated
    * Example: BTC with `size_increment = 0.0001` and `min_size = 20`:
        * ✅ Valid: 100,000 * 0.0002 = 20 USDT0
        * ❌ Invalid: 100,000 * 0.0001 = 10 USDT0
        * ❌ Invalid: 100,000 * 0.00025 (not multiple of 0.0001)

### Orders & Signing

8.  **Place Orders Execute**
    * Added: `place_orders_execute` - place multiple orders in a single request
    * Accepts array of orders with same structure as `place_order`
    * Optional `stop_on_failure` parameter to stop processing remaining orders on first failure
    * Returns array of results with digest (if successful) or error (if failed) for each order
    * Rate limit weight calculated per order

9.  **EIP712 Order Struct Update**
```solidity
struct Order {
    bytes32 sender;
    int128 priceX18;
    int128 amount;
    uint64 expiration;
    uint64 nonce;
    uint128 appendix;
}
```
* New field: `appendix`
* All order flags (IOC, post-only, reduce-only, triggers) moved into `appendix`
* `expiration` is now strictly a timestamp
* `appendix` bitfield:

| value | reserved | trigger | reduce only | order type | isolated | version |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 64 bits | 50 bits | 2 bits | 1 bit | 2 bits | 1 bit | 8 bits |

* Special encodings:
    * `trigger = 2` or `3` → value encodes TWAP settings (`times`, `slippage_x6`)
    * `isolated = 1` → value encodes isolated margin
* Constraints:
    * Isolated orders cannot be TWAP
    * TWAP orders must use IOC execution type

10. **TWAP Order Execution**
    * Added `list_twap_executions` query to trigger service
    * TWAP orders track individual execution status (pending, executed, failed, cancelled)
    * TWAP execution statuses include execution time and engine response data

11. **Trigger Service Rate Limits**
    * Updated trigger order limits from 100 pending orders per subaccount to 25 pending orders per product per subaccount

12. **EIP712 Domain Change**
    * Signing domain updated from Vertex → Nado

### Query Updates

13. **max_order_size**
    * Added: `isolated` parameter - when set to true, calculates max order size for an isolated margin position. Defaults to false.

14. **orders Query**
    * Added: `trigger_types` parameter - filter orders by trigger type(s)

15. **Historical Events**
    * Added: `quote_volume_cumulative` - tracks cumulative trading volume for the subaccount in quote units
    * Available in: `events` and `subaccount_snapshots` queries

16. **subaccount_snapshots Query**
    * Added: `active` parameter - filter snapshots by position status
        * `true`: returns only products with non-zero balance at the timestamp
        * `false`: returns products with event history before the timestamp (default)

17. **Trigger Orders**
    * Added: `placed_at` field - timestamp when trigger order should be placed

18. **Removal of summary Query**
    * Removed: `summary` query from indexer API
    * Use `subaccount_data_snapshots` query instead for historical subaccount data

19. **Query Renaming**
    * Renamed: `usdc_price` → `quote_price` query

20. **Multi-Subaccount events, matches, orders**
    * The indexer `events`, `matches`, and `orders` queries now accept a `subaccounts` array so you can fetch history for multiple subaccounts in a single request instead of fanning out per subaccount. Please note that the old single-subaccount version is no longer supported.

### Streams

21. **OrderUpdate**
    * Can now subscribe across all products by setting `product_id = null`
    * `product_id` type changed from `u32` → `Option<u32>`

22. **Fill**
    * Added: `fee`, `submission_idx`, and `appendix`
    * Can now subscribe across all products by setting `product_id = null`

23. **PositionChange**
    * Can now subscribe across all products by setting `product_id = null`
    * `product_id` type changed from `u32` → `Option<u32>`
    * Added: `isolated` - indicates whether the position change is for an isolated margin position

24. **FundingPayment**
    * New stream: `FundingPayment`
    * Param: `product_id: u32`
    * Emits hourly funding payment events

25. **Liquidation**
    * New stream: `Liquidation`
    * Param: `product_id` or `null` (all products)
    * Emits liquidation info (liquidator, liquidatee, amount, price)

26. **LatestCandlestick**
    * New stream: `LatestCandlestick`
    * Params: `product_id`, `granularity` (seconds)
    * Emits candlestick updates on every trade

27. **FundingRate**
    * New stream: `FundingRate`
    * Param: `product_id` or `null` (all products)
    * Emits funding rate updates every 20 seconds
    * `funding_rate_x18` and `update_time` values are identical to those from the Funding Rate indexer endpoints
