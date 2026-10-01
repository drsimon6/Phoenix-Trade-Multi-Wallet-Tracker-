```markdown
# Phoenix Trade Multi-Wallet Tracker 🦅

A lightweight, ultra-fast asynchronous Python monitoring bot designed to track target wallets on Phoenix Trade (Solana DEX) and send instant alert notifications directly to Telegram.

This project is built using pure Solana JSON-RPC API calls and `aiohttp`, making it extremely fast, resource-efficient, and free from heavy Web3 library dependencies.

---

## 📌 Project Structure

```text
Phoenix-Trade-Multi-Wallet-Tracker/
├── main.py
├── config.py                  # Primary instance configuration
├── config_high_volume.py      # (Optional) Secondary instance configuration
├── requirements.txt
├── README.md
└── .gitignore

```

---

## ✨ Features

* **⚡ Ultra-Fast Asynchronous Architecture:** Powered by `asyncio` and `aiohttp` for sub-second event processing and non-blocking Telegram notifications.
* **🔄 Dynamic Configuration Loader:** Launch multiple independent instances using different config files (e.g., `python3 main.py config_high_volume.py`).
* **🛡️ Auto-Failover RPC Rotation:** Rotates Helius API keys and automatically switches to secondary public Solana RPCs (Solana Beta, PublicNode, Ankr) whenever a `429 Too Many Requests` rate limit occurs.
* **🔇 Smart Anti-Spam Logging:** Suppresses log flooding during RPC rate limits, outputting concise status warnings at most once every 15 seconds.
* **🔍 Spot & Perps Support:** Identifies transactions across both **Phoenix Spot 🦅** and **Phoenix Eternal (Perps) ⚡**.
* **📊 Order Type Detection:** Parses transaction logs to classify intents (Limit Orders, Market Orders, Cancel Orders).
* **📲 Rich Telegram Alerts:** Includes wallet aliases, order action types, execution status, exact timestamps, direct Solscan transaction links, and live Phoenix portfolio links.

---

## 🛠️ Prerequisites

* Python 3.10 or higher
* Git installed on your system
* A Telegram Bot (Created via [@BotFather](https://www.google.com/search?q=https://t.me/BotFather))
* Your Telegram Chat ID (Obtained via [@userinfobot](https://www.google.com/search?q=https://t.me/userinfobot))
* One or more Helius API Keys (Recommended for low latency)

---

## 🚀 Quick Start (Local Setup)

### 1. Clone the Repository

```bash
git clone [https://github.com/drsimon6/Phoenix-Trade-Multi-Wallet-Tracker-.git](https://github.com/drsimon6/Phoenix-Trade-Multi-Wallet-Tracker-.git)
cd Phoenix-Trade-Multi-Wallet-Tracker-

```

### 2. Set Up Virtual Environment & Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

```

### 3. Create Configuration File

Create a `config.py` file in the project root:

```python
# === Bot Configuration ===

# Helius API Keys (Primary RPC)
HELIUS_API_KEYS = [
    "YOUR_HELIUS_API_KEY_1",
    # "YOUR_HELIUS_API_KEY_2",
]

# Backup Public RPCs (Auto-failover target if Helius hits 429)
RPC_URLS = [
    "[https://api.mainnet-beta.solana.com](https://api.mainnet-beta.solana.com)",
    "[https://solana-rpc.publicnode.com](https://solana-rpc.publicnode.com)",
    "[https://rpc.ankr.com/solana](https://rpc.ankr.com/solana)"
]

# Telegram Credentials
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

# Polling Interval in seconds (Recommended: 2 to 3 seconds to avoid rate limits)
POLL_INTERVAL = 3

# === Target Wallets ===
# Format: "WALLET_ADDRESS": "ALIAS_NAME"
TARGET_WALLETS = {
    "WALLET_ADDRESS_1": "Whale 1",
    "WALLET_ADDRESS_2": "Whale 2",
}

```

### 4. Run the Bot

```bash
# Default config (loads config.py)
python3 main.py

# Or specify a custom config file
python3 main.py config_high_volume.py

```

---

## 🌐 24/7 VPS Deployment (Ubuntu / Debian)

Follow this beginner-friendly, step-by-step guide to deploy and run your bot 24/7 on a Linux VPS using background `screen` sessions.

---

### Step 1: Update System & Install Required Packages
Update your server's package repository and install essential utilities (`git`, `python3`, `pip`, `venv`, and `screen`):

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install git python3 python3-pip python3-venv screen -y

```

---

### Step 2: Clone Repository & Navigate to Directory

Download the project code from GitHub and enter the project folder:

```bash
git clone [https://github.com/drsimon6/Phoenix-Trade-Multi-Wallet-Tracker-.git](https://github.com/drsimon6/Phoenix-Trade-Multi-Wallet-Tracker-.git)
cd Phoenix-Trade-Multi-Wallet-Tracker-

```

---

### Step 3: Create & Activate Virtual Environment

Set up an isolated Python environment to handle required dependencies:

```bash
# 1. Create a virtual environment named .venv
python3 -m venv .venv

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Install required dependencies
pip install -r requirements.txt

```

---

### Step 4: Create Configuration Files (Before Starting Screens)

Create and save your configuration file(s) before launching background processes.

#### 1. Primary Configuration (`config.py`):

```bash
nano config.py

```

* Paste your configuration code into the terminal editor.
* **How to save & exit in Nano:**
1. Press `Ctrl + O` (Write Out)
2. Press `Enter` (Confirm file name)
3. Press `Ctrl + X` (Exit editor)



#### 2. (Optional) High-Volume Configuration (`config_high_volume.py`):

If running a separate instance for high-volume wallets:

```bash
nano config_high_volume.py

```

* Paste your high-volume configuration code.
* Save and exit using `Ctrl + O` -> `Enter` -> `Ctrl + X`.

---

### Step 5: Launch Bot Instances in Background Screens

#### Instance 1: Normal Volume Tracker (`phoenix-normal`)

```bash
# 1. Create and enter a screen session named phoenix-normal
screen -S phoenix-normal

# 2. Activate the virtual environment inside the screen
source .venv/bin/activate

# 3. Launch the bot with default config
python3 main.py config.py

```

* **Detach Screen:** Press `Ctrl + A`, then press `D`. The bot will continue running safely in the background.

---

#### Instance 2: High-Volume Tracker (`phoenix-highvol`)

```bash
# 1. Create and enter a screen session named phoenix-highvol
screen -S phoenix-highvol

# 2. Activate the virtual environment inside the screen
source .venv/bin/activate

# 3. Launch the bot with high-volume config
python3 main.py config_high_volume.py

```

* **Detach Screen:** Press `Ctrl + A`, then press `D`.

---

### Step 6: Useful Screen Management Commands

| Action | Command |
| --- | --- |
| **List all active screens** | `screen -ls` |
| **Re-attach to normal instance** | `screen -r phoenix-normal` |
| **Re-attach to high-volume instance** | `screen -r phoenix-highvol` |
| **Detach from inside a screen** | Press `Ctrl + A` then press `D` |
| **Stop all running bots** | `pkill -f main.py` |
| **Kill a specific screen session** | `screen -XS phoenix-normal quit` |

```

```
