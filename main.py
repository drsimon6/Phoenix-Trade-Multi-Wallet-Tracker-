import time
import requests
from datetime import datetime
import config # Import user configuration

# Replace old constants with config values
TARGET_WALLETS = config.TARGET_WALLETS
RPC_URL = config.RPC_URL
TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = config.TELEGRAM_CHAT_ID
POLL_INTERVAL = config.POLL_INTERVAL


def send_telegram_alert(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"⚠️ Telegram Alert Error: {e}")


def get_latest_signatures(wallet_address: str, limit: int = 3):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [wallet_address, {"limit": limit}]
    }
    try:
        response = requests.post(RPC_URL, json=payload, timeout=10)
        data = response.json()
        if "result" in data:
            return data["result"]
    except Exception as e:
        print(f"⚠️ Solana RPC Error: {e}")
    return []


def get_transaction_details(signature: str):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
        ]
    }
    try:
        response = requests.post(RPC_URL, json=payload, timeout=10)
        data = response.json()
        if "result" in data and data["result"]:
            return data["result"]
    except Exception as e:
        print(f"⚠️ Transaction Details Error: {e}")
    return None


def parse_logs_for_phoenix(logs):
    if not logs:
        return "General Solana Transaction"
    logs_str = " ".join(logs).lower()
    if "ember" in logs_str or "phusd" in logs_str:
        return "🔥 Phoenix Activity (Margin / Deposit / Withdraw)"
    elif "place" in logs_str or "order" in logs_str:
        return "⚡ Place / Fill Order"
    elif "cancel" in logs_str:
        return "❌ Cancel Order"
    elif "swap" in logs_str:
        return "🔄 Instant Swap"
    else:
        return "📊 Phoenix Contract Interaction"


def start_monitoring():
    print("🚀 Phoenix Wallet Monitoring Bot Started...")
    last_processed_signatures = {}

    for wallet_addr, wallet_name in TARGET_WALLETS.items():
        initial_sigs = get_latest_signatures(wallet_addr, limit=1)
        last_processed_signatures[wallet_addr] = initial_sigs[0]["signature"] if initial_sigs else None
        time.sleep(0.3)

    send_telegram_alert("🚀 <b>Phoenix Monitoring Bot is live and listening for new transactions.</b>")

    while True:
        try:
            for wallet_addr, wallet_name in TARGET_WALLETS.items():
                signatures = get_latest_signatures(wallet_addr, limit=5)
                if not signatures:
                    continue

                last_sig = last_processed_signatures.get(wallet_addr)
                new_txs = []
                for sig_info in signatures:
                    sig = sig_info["signature"]
                    if sig == last_sig:
                        break
                    new_txs.append(sig_info)

                if new_txs:
                    for tx_info in reversed(new_txs):
                        sig = tx_info["signature"]
                        err = tx_info.get("err")
                        block_time = tx_info.get("blockTime")
                        
                        time_str = datetime.fromtimestamp(block_time).strftime('%Y-%m-%d %H:%M:%S') if block_time else "Unknown"
                        status = "❌ Failed" if err else "✅ Success"

                        tx_details = get_transaction_details(sig)
                        logs = tx_details["meta"]["logMessages"] if tx_details and "meta" in tx_details and tx_details["meta"].get("logMessages") else []
                        action_summary = parse_logs_for_phoenix(logs)

                        alert_text = (
                            f"🔔 <b>New Transaction Detected!</b>\n\n"
                            f"🏷 <b>Wallet Alias:</b> {wallet_name}\n"
                            f"👤 <b>Address:</b> <code>{wallet_addr[:6]}...{wallet_addr[-4:]}</code>\n"
                            f"📌 <b>Activity:</b> {action_summary}\n"
                            f"📊 <b>Status:</b> {status}\n"
                            f"⏰ <b>Time:</b> {time_str}\n\n"
                            f"🔗 <a href='https://solscan.io/tx/{sig}'>View on Solscan</a>"
                        )
                        send_telegram_alert(alert_text)
                        last_processed_signatures[wallet_addr] = sig

                time.sleep(0.3)
            time.sleep(POLL_INTERVAL)
        except Exception as e:
            print(f"⚠️ Main Loop Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    start_monitoring()
