### Instrucciones

1️⃣ Crear el virtual environment (en la raíz del repo)
python3 -m venv .venv

2️⃣ Activar el venv

macOS / Linux
source .venv/bin/activate

Windows (PowerShell)
.venv\Scripts\Activate.ps1

3️⃣ Actualizar pip (buena práctica)
pip install --upgrade pip

4️⃣ Instalar dependencias del proyecto

Lo que está en pyproject.toml:

pip install -e .



Intended Project Tree


ibkr-bot/
├─ README.md
├─ pyproject.toml
├─ uv.lock / poetry.lock          # según el manager que elija
├─ .gitignore
├─ .env.example
├─ config/
│  ├─ settings.example.yaml
│  └─ logging.yaml
├─ src/
│  └─ ibkr_bot/
│     ├─ __init__.py
│     ├─ main.py                  # entrypoint CLI
│     ├─ config.py                # carga env/yaml, validación
│     ├─ logging_setup.py
│     ├─ broker/
│     │  ├─ __init__.py
│     │  ├─ ibkr_client.py        # connect/disconnect, wrappers
│     │  ├─ contracts.py          # helpers (stocks/futures/etc)
│     │  └─ orders.py             # market/limit/bracket builders
│     ├─ data/
│     │  ├─ __init__.py
│     │  ├─ market_data.py        # streaming/snapshots
│     │  └─ historical.py         # candles/historical pulls
│     ├─ strategy/
│     │  ├─ __init__.py
│     │  ├─ base.py               # interface Strategy
│     │  └─ sample_strategy.py    # placeholder
│     ├─ risk/
│     │  ├─ __init__.py
│     │  ├─ sizing.py             # position sizing
│     │  └─ guards.py             # daily loss, max trades, etc
│     ├─ execution/
│     │  ├─ __init__.py
│     │  └─ executor.py           # signal -> orders, state machine
│     ├─ backtest/
│     │  ├─ __init__.py
│     │  └─ engine.py             # simple backtest runner (MVP)
│     └─ utils/
│        ├─ time.py
│        └─ math.py
├─ scripts/
│  ├─ hello_connect.py            # conecta y trae account summary
│  ├─ hello_marketdata.py         # pide bid/ask/last
│  └─ hello_paper_order.py        # manda orden paper (controlada)
├─ tests/
│  └─ test_smoke.py
└─ docker/                        # opcional (no obligatorio hoy)
   ├─ Dockerfile
   └─ docker-compose.yml
