from ibkr_bot.broker.ibkr_client import IBKRClient
from ib_insync import Stock

client = IBKRClient()

"""
En IBKR, el market data type se controla con reqMarketDataType:
1 = live
3 = delayed
4 = delayed-frozen
"""

print("Connecting...")
client.connect()

contract = Stock("AAPL", "SMART", "USD")

def request_and_print():
    ticker = client.ib.reqMktData(contract, "", False, False)
    client.ib.sleep(2)
    print(f"Bid: {ticker.bid} | Ask: {ticker.ask} | Last: {ticker.last}")
    print(f"Close: {ticker.close} | High: {ticker.high} | Low: {ticker.low}")
    return ticker

print("Requesting LIVE market data...")
client.ib.reqMarketDataType(1)
ticker = request_and_print()

# Si no hay data, probamos delayed
if (ticker.last != ticker.last) and (ticker.bid != ticker.bid) and (ticker.ask != ticker.ask):  # NaN check
    print("No live data. Switching to DELAYED market data...")
    client.ib.reqMarketDataType(3)
    request_and_print()

client.disconnect()
print("Done.")
