from datetime import datetime
from ib_insync import Stock, util
from ibkr_bot.broker.ibkr_client import IBKRClient

client = IBKRClient()

print("Connecting...")
client.connect()

# AAPL como ejemplo
contract = Stock("AAPL", "SMART", "USD")

# Parámetros
bar_size = "5 mins"
duration = "2 D"          # 2 días
what_to_show = "TRADES"   # TRADES suele ser lo más común
use_rth = False           # False = incluye extended hours

print(f"Requesting historical data: {contract.symbol} | {bar_size} | {duration} | {what_to_show} | useRTH={use_rth}")

bars = client.ib.reqHistoricalData(
    contract,
    endDateTime="",
    durationStr=duration,
    barSizeSetting=bar_size,
    whatToShow=what_to_show,
    useRTH=use_rth,
    formatDate=1
)

df = util.df(bars)

if df.empty:
    print("❌ No historical data returned.")
else:
    print(f"✅ Got {len(df)} bars")
    print(df.tail(10))

    # Guardar CSV
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"data/{contract.symbol}_{bar_size.replace(' ', '')}_{duration.replace(' ', '')}_{ts}.csv"
    df.to_csv(out_path, index=False)
    print(f"💾 Saved to {out_path}")

client.disconnect()
print("Done.")
