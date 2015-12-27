# stockfighter

Python API for https://www.stockfighter.io/

- To set up, rename the file `template_config.ini` to `config.ini` and copy your API key 
- create a virtual environment with the provided `environement.yml`. Requires conda.
At the root of this repo :  `conda-env create`

- Example use :
```
GM = stockfighter.GameMaster()
GM.start('sell_side')       # or GM.restart()

# Used to interact with stockfighter API & websockets
MB = stockfighter.MarketBroker(gm=GM)           
# Used to pass orders, and keeps an internal state of own book (pending orders + position)
TB = stockfighter.TraderBook(marketbroker=MB)   

quote = MB.current_quote()

print(quote)

ask        7383
askSize      77
bid        7311
bidSize     423
spread       72
Name: 2015-12-27 06:12:29.105297+00:00, dtype: float64

TB.sell(qty=50, price=quote.ask)
TB.buy(qty=75, price=quote.bid)
TB.buy(qty=100, order_type='market')

position, open_buy, open_sell = TB.get_own_book()

print(position)
100
print(open_buy)
75
print(open_sell)
50


```



