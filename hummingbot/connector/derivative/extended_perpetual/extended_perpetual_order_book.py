"""Extended Perpetual Order Book."""
from hummingbot.core.data_type.order_book import OrderBook


class ExtendedPerpetualOrderBook(OrderBook):
    """
    Extended Perpetual order book.
    
    Uses standard OrderBook implementation as Extended Exchange
    provides standard bid/ask format with price levels.
    """
    pass
