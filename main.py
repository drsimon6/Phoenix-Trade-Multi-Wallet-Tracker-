import time
import requests
from datetime import datetime
import sys

# بررسی وجود فایل تنظیمات
try:
    import config
except ImportError:
    print("\n⚠️ Error: 'config.py' not found! Please create it before running.")
    sys.exit(1)

# بارگذاری تنظیمات
TARGET_WALLETS = config.TARGET_WALLETS
RPC_URLS = getattr(config, 'RPC_URLS', ["https://api.mainnet-beta.solana.com"])
TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = config.TELEGRAM_CHAT_ID
POLL_INTERVAL = config.POLL_INTERVAL
HELIUS_API_KEY = getattr(config, 'HELIUS_API_KEY', '')

# شناسه‌های اختصاصی قراردادهای Phoenix روی شبکه سولانا
PHOENIX_PROGRAM_IDS = {
    "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY",  # Phoenix DEX Main Program
    "EMBERpYNE6ehWmXymZZS2skiFmCa9V5dp14e1iduM5qy",  # Ember Collateral/Margin Program
    "PhUsd11YkbjSaWjFncfAAmatntsjx3MgDR9B6g1ks3A",  # Phoenix USDC Mint
}


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


def get_latest_signatures(wallet_address: str, limit: int = 5):
    """دریافت لیست تراکنش‌ها با قابلیت Fallback روی چند RPC"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [wallet_address, {"limit": limit}]
    }
    
    for rpc_url in RPC_URLS:
        try:
            response = requests.post(rpc_url, json=payload, timeout=6)
            data = response.json()
            if "result" in data:
                return data["result"]
        except Exception:
            # در صورت خطا روی RPC جاری، سیستم سراغ RPC بعدی در لیست می‌رود
            continue
            
    print("⚠️ All RPCs failed to fetch signatures.")
    return []


def get_parsed_transaction_helius(signature: str):
    """دریافت جزییات دکود شده تراکنش مستقیماً از API هلیوس"""
    if not HELIUS_API_KEY:
        return None
        
    url = f"https://api.helius.xyz/v0/transactions?api-key={HELIUS_API_KEY}"
    payload = {"transactions": [signature]}
    
    try:
        response = requests.post(url, json=payload, timeout=8)
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0]
    except Exception as e:
        print(f"⚠️ Helius Parse API Error: {e}")
    return None


def is_phoenix_transaction(parsed_tx, raw_logs=None) -> bool:
    """بررسی اختصاصی تراکنش‌های Phoenix / Ember"""
    if parsed_tx:
        source = str(parsed_tx.get("source", "")).upper()
        if "PHOENIX" in source or "EMBER" in source:
            return True

        instructions = parsed_tx.get("instructions", [])
        for inst in instructions:
            program_id = inst.get("programId", "")
            if program_id in PHOENIX_PROGRAM_IDS:
                return True

        account_data = parsed_tx.get("accountData", [])
        for acc in account_data:
            account_key = acc.get("account", "")
            if account_key in PHOENIX_PROGRAM_IDS:
                return True

    if raw_logs:
        logs_str = " ".join(raw_logs).lower()
        if any(keyword in logs_str for keyword in ["phoenix", "ember", "phusd", "phoenixz8"]):
            return True

    return False


def extract_phoenix_trade_details(parsed_tx):
    """استخراج جزئیات معامله"""
    if not parsed_tx:
        return "Phoenix Activity", "جزئیات تکمیلی دریافت نشد."

    description = parsed_tx.get("description", "بدون شرح متنی")
    tx_type = parsed_tx.get("type", "UNKNOWN")

    token_transfers = parsed_tx.get("tokenTransfers", [])
    native_transfers = parsed_tx.get("nativeTransfers", [])

    transfers_summary = []
    
    for tt in token_transfers:
        amount = tt.get("tokenAmount", 0)
        mint = tt.get("mint", "")
        symbol = f"{mint[:4]}...{mint[-4:]}" if len(mint) > 8 else "Token"
        transfers_summary.append(f"• {amount} ({symbol})")

    for nt in native_transfers:
        sol_amount = nt.get("amount", 0) / 1e9
        if sol_amount > 0.001:
            transfers_summary.append(f"• {sol_amount:.4f} SOL")

    details_str = f"<b>شرح حرکت:</b> {description}\n"
    if transfers_summary:
        details_str += "<b>حجم جابجایی:</b>\n" + "\n".join(transfers_summary[:4])

    return f"⚡ {tx_type}", details_str


def get_transaction_details_rpc_fallback(signature: str):
    """دریافت اطلاعات خام تراکنش با سیستم سوئیچ خودکار بین RPCها"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
        ]
    }
    for rpc_url in RPC_URLS:
        try:
            response = requests.post(rpc_url, json=payload, timeout=6)
            data = response.json()
            if "result" in data and data["result"]:
                return data["result"]
        except Exception:
            continue
    return None


def start_monitoring():
    print("🚀 Phoenix Wallet Monitoring Bot Started (Multi-RPC Failover Active)...")
    last_processed_signatures = {}

    for wallet_addr, wallet_name in TARGET_WALLETS.items():
        initial_sigs = get_latest_signatures(wallet_addr, limit=1)
        last_processed_signatures[wallet_addr] = initial_sigs[0]["signature"] if initial_sigs else None
        time.sleep(0.3)

    send_telegram_alert("🚀 <b>Phoenix Monitoring Bot is live (Multi-RPC Enabled).</b>")

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

                        # ۱. دریافت جزییات دکود شده از هلیوس
                        parsed_tx = get_parsed_transaction_helius(sig)
                        
                        raw_logs = []
                        if not parsed_tx:
                            tx_details = get_transaction_details_rpc_fallback(sig)
                            raw_logs = tx_details["meta"]["logMessages"] if tx_details and "meta" in tx_details and tx_details["meta"].get("logMessages") else []

                        # ۲. فیلتر کردن تراکنش‌های غیرمرتبط با Phoenix
                        if not is_phoenix_transaction(parsed_tx, raw_logs):
                            print(f"ℹ️ Skipping non-Phoenix transaction: {sig[:8]}...")
                            last_processed_signatures[wallet_addr] = sig
                            continue

                        # ۳. ساخت متن گزارش
                        if parsed_tx:
                            action_type, trade_details = extract_phoenix_trade_details(parsed_tx)
                        else:
                            action_type = "⚡ Phoenix Contract Interaction"
                            trade_details = "جزئیات پیشرفته در دسترس نیست."

                        phoenix_portfolio_url = f"https://www.phoenix.trade/portfolio?ghost={wallet_addr}"

                        alert_text = (
                            f"🦅 <b>تراکنش جدید Phoenix ثبت شد!</b>\n\n"
                            f"🏷 <b>نام ولت:</b> {wallet_name}\n"
                            f"👤 <b>آدرس:</b> <code>{wallet_addr[:6]}...{wallet_addr[-4:]}</code>\n"
                            f"📌 <b>نوع دستور:</b> {action_type}\n"
                            f"📊 <b>وضعیت:</b> {status}\n"
                            f"⏰ <b>زمان:</b> {time_str}\n\n"
                            f"📝 {trade_details}\n\n"
                            f"🔗 <a href='https://solscan.io/tx/{sig}'>مشاهده تراکنش در Solscan</a>\n"
                            f"🦅 <a href='{phoenix_portfolio_url}'>مشاهده پورتفولیو در Phoenix</a>"
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
