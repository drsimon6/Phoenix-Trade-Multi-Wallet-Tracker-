```markdown
# Phoenix Trade Multi-Wallet Tracker 🦅

A lightweight, ultra-fast asynchronous Python monitoring bot designed to track target wallets on Phoenix Trade (a Solana DEX) and send instant alert notifications directly to Telegram.

This project is built using pure Solana JSON-RPC API calls and `aiohttp`, making it extremely fast, resource-efficient, and free from heavy Web3 library dependencies.

## 📌 Project Structure

```text
Phoenix-Trade-Multi-Wallet-Tracker/
├── main.py
├── config.py
├── requirements.txt
├── README.md
└── .gitignore

```

## ✨ Features

* ⚡ **Ultra-Fast Asynchronous Architecture**: Powered by `asyncio` and `aiohttp` for sub-second event processing and non-blocking Telegram notifications.
* 🔑 **Multi-Key RPC Rotation**: Automatically cycles through multiple Helius API keys to eliminate rate-limiting (`429 Too Many Requests`) issues.
* 🛡️ **Smart Crank & System Filtering**: Uses `Signer` verification to filter out automated exchange/crank bot transactions, alerting you only when a target wallet manually executes an order.
* 🔍 **Order Type Detection**: Identifies transaction intents (Limit Orders, Market Orders, Cancel Orders) directly from transaction logs.
* 📲 **Rich Telegram Notifications**: Formatted alerts featuring execution status, exact timestamps, direct Solscan transaction links, and live Phoenix portfolio viewing URLs.
* 🛠️ **Lightweight & Independent**: Pure Python REST implementation with minimal dependencies and low memory usage.

## 🛠️ Prerequisites

* Python 3.10 or higher
* Git installed on your system
* A Telegram Bot (Created via [@BotFather](https://t.me/BotFather))
* Your Telegram Chat ID (Obtained via [@userinfobot](https://t.me/userinfobot))
* One or more [Helius API Keys](https://helius.dev/) for low-latency RPC access

## 🚀 Quick Start (Local Setup)

### 1. Clone the Repository

```bash
git clone [https://github.com/drsimon6/Phoenix-Trade-Multi-Wallet-Tracker-.git](https://github.com/drsimon6/Phoenix-Trade-Multi-Wallet-Tracker-.git)
cd Phoenix-Trade-Multi-Wallet-Tracker-

```

### 2. Set Up Virtual Environment & Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt

```

### 3. Configure Credentials

Create a `config.py` file in the project root directory:

```python
# === Bot Configuration ===

# Helius API Keys (Add one or more keys for automatic load balancing/rotation)
HELIUS_API_KEYS = [
    "YOUR_HELIUS_API_KEY_1",
    # "YOUR_HELIUS_API_KEY_2",
]

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

# Polling interval in seconds
POLL_INTERVAL = 1

# === Wallets to Monitor ===
# Format: "WALLET_ADDRESS": "ALIAS_NAME"
TARGET_WALLETS = {
    "WALLET 1": "W1",
    "WALLET 2": "W2",
}

```

### 4. Run the Bot

```bash
python3 main.py

```

---

## 🌐 24/7 VPS Deployment (Ubuntu / Debian)

Follow these steps to deploy and run the bot continuously on a Linux VPS.

### 1. Install System Dependencies

```bash
sudo apt update && sudo apt install git python3 python3-pip python3-venv screen -y

```

### 2. Clone Repository & Navigate

```bash
git clone [https://github.com/drsimon6/Phoenix-Trade-Multi-Wallet-Tracker-.git](https://github.com/drsimon6/Phoenix-Trade-Multi-Wallet-Tracker-.git)
cd Phoenix-Trade-Multi-Wallet-Tracker-

```

### 3. Create Virtual Environment & Install Requirements

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

```

*(If installing system-wide without venv on Python 3.12+, use: `pip install -r requirements.txt --break-system-packages`)*

### 4. Create Configuration File

```bash
nano config.py

```

*(Paste your `config.py` content, fill in your credentials/wallets, save with `Ctrl + O`, press `Enter`, and exit with `Ctrl + X`)*

### 5. Run Inside a Dedicated Screen Session

Launch a background screen session named `phoenix-bot`:

```bash
screen -S phoenix-bot
source .venv/bin/activate
python3 main.py

```

### 6. Detach & Re-attach Screen Session

* **Safely Detach**: Press `Ctrl + A`, then press `D`. The bot will continue running in the background.
* **Re-attach Later**: To check logs or manage execution, run:
```bash
screen -r phoenix-bot

```



---

## 🗺️ Project Roadmap

* [x] **Phase 1: Asynchronous Engine & Anti-Rate Limit**
* Switch to `aiohttp` non-blocking architecture.
* Implement multi-key Helius RPC rotation.
* Add `Signer` verification to filter out exchange crank/system transactions.


* [ ] **Phase 2: Telegram Interactivity & Settings**
* Add interactive bot commands (`/add_wallet`, `/remove_wallet`, `/list`).
* SQLite database integration for storing transaction history and wallet metrics.
* Custom alert filters (e.g., toggle Cancel Order notifications or minimum volume threshold).


* [ ] **Phase 3: Sub-100ms Latency & Analytics**
* Upgrade from polling to Helius Webhooks / Solana Geyser WebSocket streams.
* Real-time estimated PnL and trade execution price calculation in Telegram alerts.
* Multi-DEX support (Drift Protocol & OpenBook).



---

## ⚠️ Disclaimer

This project is created strictly for educational and monitoring purposes. It does not constitute financial advice, nor does it include automated trading or copy-trading capabilities.

```

```
