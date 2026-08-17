# === Bot Configuration ===
# Set your Solana RPC URL. (Use Helius/QuickNode for lower latency)
RPC_URL = "https://api.mainnet-beta.solana.com"

# Set your Telegram Bot Token (e.g., "123456789:AAHg...")
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# Set your Telegram Chat ID (e.g., "987654321")
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

# Polling interval in seconds
POLL_INTERVAL = 3

# === Wallets to Monitor ===
# Add wallets here in the format: "WALLET_ADDRESS": "ALIAS"
# Example:
# TARGET_WALLETS = {
#     "FIRST_WALLET_ADDRESS": "Wallet 1 (Trader A)",
#     "SECOND_WALLET_ADDRESS": "Wallet 2 (Trader B)",
# }
TARGET_WALLETS = {
    "wallet1": "Sample Wallet", # Pre-add one sample for testing
}

# Helius API Key for enhanced transaction parsing
HELIUS_API_KEY = "your-helius-api-key-here"
