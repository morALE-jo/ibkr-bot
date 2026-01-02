from ibkr_bot.broker.ibkr_client import IBKRClient


def main():
    client = IBKRClient()

    print("🔌 Connecting to IBKR...")
    if not client.connect():
        print("❌ Could not connect")
        return

    print("✅ Connected to IBKR")

    summary = client.account_summary()
    print("📊 Account summary (first 5 rows):")
    for row in summary[:5]:
        print(f"{row.tag}: {row.value}")

    client.disconnect()
    print("👋 Disconnected")


if __name__ == "__main__":
    main()