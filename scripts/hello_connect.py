from ibkr_bot.broker.ibkr_client import IBKRClient

client = IBKRClient()

print("Connecting...")
client.connect()

print("Account values:")
for row in client.account_summary():
    if row.tag in ("NetLiquidation", "AvailableFunds", "Currency"):
        print(f"{row.tag}: {row.value}")

client.disconnect()
print("Done.")