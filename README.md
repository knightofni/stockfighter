# stockfighter

Python API for https://www.stockfighter.io/

- To set up, rename the file `template_config.ini` to `config.ini` and copy your API key 
- create a virtual environment with the provided `environement.yml`. Requires conda.
At the root of this repo :  `conda-env create`

- Example use :
```
GM = stockfighter.GameMaster()
GM.start('sell_side')       # or GM.restart()

MM = stockfighter.MarketBroker(gm=GM)           # Used to interact with stockfighter API & websockets
TB = stockfighter.TraderBook(marketbroker=MM)   # Used to pass orders, and keeps an internal state of own book (pending orders + position)

quote = MM.current_quote()

TB.sell(qty=100,price=quote.ask)
TB.buy(qty=100,price=quote.bid)

position, open_buy, open_sell = TB.get_own_book()
```



