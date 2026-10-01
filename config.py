# === Bot Configuration ===

# Telegram Settings
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

# Polling Interval in seconds (1 for high-speed tracking)
POLL_INTERVAL = 1

# Helius API Keys (Add multiple keys to prevent rate limits)
HELIUS_API_KEYS = [
    "YOUR_HELIUS_API_KEY_1",
    # "YOUR_HELIUS_API_KEY_2",  # Optional secondary key
]

# Backup Public RPC URLs
RPC_URLS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-rpc.publicnode.com"
]

# === Wallets to Monitor ===
# Format: "WALLET_ADDRESS": "ALIAS / NAME"
TARGET_WALLETS = {
    "11111111111111111111111111111111": "Sample Wallet 💎",
}
