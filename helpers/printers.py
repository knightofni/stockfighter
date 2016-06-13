"""
    Helpers classes to pretty print information

"""


def format_order_book(order_book):
    """
        ob : dict containing order book info, as returned by MarketMaket.order_book()
    """
    print('Type - Price -   Qty')
    # If you are buying a stock you are going to get the ask price
    asks = order_book.get('asks')
    if asks:
        for ask in asks:
            print('Ask  : {:>5} - {:>5}'.format(ask.get('price'), ask.get('qty')))
    else:
        print('No Asks')
    # If you are selling a stock, you are going to get the bid price
    bids = order_book.get('bids')

    print('----------------')
    if bids:
        for bid in bids:
            print('Bid  : {:>5} - {:>5}'.format(bid.get('price'), bid.get('qty')))
    else:
        print('No Bids')
