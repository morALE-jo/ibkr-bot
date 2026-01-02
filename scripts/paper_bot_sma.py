import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from ib_insync import Stock, MarketOrder, util

from ibkr_bot.broker.ibkr_client import IBKRClient


STATE_PATH = Path("state.json")


@dataclass
class BotConfig:
    symbol: str = "AAPL"
    exchange: str = "SMART"
    currency: str = "USD"

    bar_size: str = "5 mins"
    lookback: str = "3 D"          # suficiente para SMAs
    use_rth: bool = False

    sma_fast: int = 10
    sma_slow: int = 30

    qty: int = 1

    # “Capital educativo” para guardas (no necesariamente el NetLiq real de IB paper)
    paper_capital: float = 100_000.0
    max_trades_per_day: int = 6
    daily_loss_limit: float = 500.0   # si pierde > $500 en el día, se apaga (educativo)

    # Loop
    poll_seconds: int = 60  # chequea cada 60s; solo actúa si hay vela nueva


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {
        "last_bar_time": None,
        "position": 0,               # 0 = flat, 1 = long
        "entry_price": None,
        "trades_today": 0,
        "day": None,                 # YYYY-MM-DD (UTC)
        "daily_pnl": 0.0,
        "last_signal": None,         # 0/1
        "last_action": None,
        "updated_at": None,
    }


def save_state(state: dict) -> None:
    state["updated_at"] = utc_now_iso()
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def ensure_day_rollover(state: dict) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    if state.get("day") != today:
        state["day"] = today
        state["trades_today"] = 0
        state["daily_pnl"] = 0.0


def compute_signal(df: pd.DataFrame, fast: int, slow: int) -> tuple[int | None, pd.Timestamp | None, float | None]:
    """
    Retorna: (signal, last_bar_time, last_close)
      signal = 1 si sma_fast > sma_slow, 0 si no, None si no hay data suficiente
    """
    if df.empty:
        return None, None, None

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df["sma_fast"] = df["close"].rolling(fast).mean()
    df["sma_slow"] = df["close"].rolling(slow).mean()

    last = df.iloc[-1]
    if pd.isna(last["sma_fast"]) or pd.isna(last["sma_slow"]):
        return None, last["date"], float(last["close"])

    signal = 1 if float(last["sma_fast"]) > float(last["sma_slow"]) else 0
    return signal, last["date"], float(last["close"])


def place_market_order(ib, contract, action: str, qty: int):
    order = MarketOrder(action, qty)
    trade = ib.placeOrder(contract, order)
    ib.sleep(1)
    return trade


def main():
    cfg = BotConfig()

    # Permitir overrides por env si quiere
    cfg.symbol = os.getenv("BOT_SYMBOL", cfg.symbol)
    cfg.qty = int(os.getenv("BOT_QTY", str(cfg.qty)))
    cfg.sma_fast = int(os.getenv("BOT_SMA_FAST", str(cfg.sma_fast)))
    cfg.sma_slow = int(os.getenv("BOT_SMA_SLOW", str(cfg.sma_slow)))
    cfg.paper_capital = float(os.getenv("BOT_PAPER_CAPITAL", str(cfg.paper_capital)))
    cfg.max_trades_per_day = int(os.getenv("BOT_MAX_TRADES_DAY", str(cfg.max_trades_per_day)))
    cfg.daily_loss_limit = float(os.getenv("BOT_DAILY_LOSS_LIMIT", str(cfg.daily_loss_limit)))
    cfg.poll_seconds = int(os.getenv("BOT_POLL_SECONDS", str(cfg.poll_seconds)))

    state = load_state()
    ensure_day_rollover(state)
    save_state(state)

    client = IBKRClient()

    print(f"[{utc_now_iso()}] 🔌 Connecting...")
    client.connect()

    contract = Stock(cfg.symbol, cfg.exchange, cfg.currency)

    print(
        f"[{utc_now_iso()}] 🤖 Running SMA bot on {cfg.symbol} | {cfg.bar_size} | fast={cfg.sma_fast} slow={cfg.sma_slow} | qty={cfg.qty}"
    )
    print(f"[{utc_now_iso()}] 🧾 Paper capital (educational): {cfg.paper_capital:.2f} | Daily loss limit: {cfg.daily_loss_limit:.2f}")

    # Loop
    while True:
        try:
            ensure_day_rollover(state)

            # Guardas “hard”
            if state["trades_today"] >= cfg.max_trades_per_day:
                print(f"[{utc_now_iso()}] 🛑 Max trades/day reached ({state['trades_today']}). Sleeping.")
                save_state(state)
                time.sleep(cfg.poll_seconds)
                continue

            if state["daily_pnl"] <= -abs(cfg.daily_loss_limit):
                print(f"[{utc_now_iso()}] 🛑 Daily loss limit hit (PnL={state['daily_pnl']:.2f}). Stopping bot.")
                save_state(state)
                break

            # Pedir histórico (API)
            bars = client.ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr=cfg.lookback,
                barSizeSetting=cfg.bar_size,
                whatToShow="TRADES",
                useRTH=cfg.use_rth,
                formatDate=1,
            )

            df = util.df(bars)
            signal, last_bar_time, last_close = compute_signal(df, cfg.sma_fast, cfg.sma_slow)

            if signal is None:
                print(f"[{utc_now_iso()}] ⏳ Not enough data for SMAs yet. Sleeping.")
                time.sleep(cfg.poll_seconds)
                continue

            # Solo actuar si hay vela nueva (evita spam)
            last_bar_iso = str(last_bar_time)
            if state["last_bar_time"] == last_bar_iso:
                time.sleep(cfg.poll_seconds)
                continue

            state["last_bar_time"] = last_bar_iso

            prev_signal = state.get("last_signal")
            state["last_signal"] = signal

            print(f"[{utc_now_iso()}] 📈 New bar {last_bar_iso} | close={last_close:.2f} | signal={signal} (prev={prev_signal})")

            # Reglas de trading (simple):
            # - Si signal pasa a 1: entrar long si está flat
            # - Si signal pasa a 0: salir si está long
            action_taken = None

            # Entrada
            if state["position"] == 0 and prev_signal == 0 and signal == 1:
                print(f"[{utc_now_iso()}] 🟢 Entry condition met. Placing BUY {cfg.qty} {cfg.symbol} (paper).")
                trade = place_market_order(client.ib, contract, "BUY", cfg.qty)

                # Para el ejercicio, usamos close como entry_price (no fill real)
                state["position"] = 1
                state["entry_price"] = float(last_close)
                state["trades_today"] += 1
                action_taken = f"BUY_{cfg.qty}"

                print(f"[{utc_now_iso()}] ✅ Order status: {trade.orderStatus.status}")

            # Salida
            elif state["position"] == 1 and prev_signal == 1 and signal == 0:
                print(f"[{utc_now_iso()}] 🔴 Exit condition met. Placing SELL {cfg.qty} {cfg.symbol} (paper).")
                trade = place_market_order(client.ib, contract, "SELL", cfg.qty)

                # PnL educativo (close - entry)
                entry = float(state["entry_price"]) if state["entry_price"] is not None else float(last_close)
                trade_pnl = (float(last_close) - entry) * cfg.qty
                state["daily_pnl"] += trade_pnl

                state["position"] = 0
                state["entry_price"] = None
                state["trades_today"] += 1
                action_taken = f"SELL_{cfg.qty}"

                print(f"[{utc_now_iso()}] ✅ Order status: {trade.orderStatus.status}")
                print(f"[{utc_now_iso()}] 💰 Trade PnL (educational): {trade_pnl:.2f} | Daily PnL: {state['daily_pnl']:.2f}")

            state["last_action"] = action_taken
            save_state(state)

            time.sleep(cfg.poll_seconds)

        except KeyboardInterrupt:
            print(f"\n[{utc_now_iso()}] 🧯 Stopping (KeyboardInterrupt). Saving state and disconnecting.")
            save_state(state)
            break
        except Exception as e:
            print(f"[{utc_now_iso()}] ⚠️ Error: {e}. Saving state, sleeping 10s, and continuing.")
            save_state(state)
            time.sleep(10)

    client.disconnect()
    print(f"[{utc_now_iso()}] 👋 Disconnected. Bye.")


if __name__ == "__main__":
    main()
