import time
import requests
from datetime import datetime
import sys
import itertools

# بررسی وجود فایل تنظیمات
try:
    import config
except ImportError:
    print("\n⚠️ Error: 'config.py' not found! Please create it before running.")
    sys.exit(1)

# بارگذاری تنظیمات
TARGET_WALLETS = config.TARGET_WALLETS
POLL_INTERVAL = getattr(config, 'POLL_INTERVAL', 3)
TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = config.TELEGRAM_CHAT_ID

# بارگذاری لیست کلیدهای هلیوس
HELIUS_API_KEYS = getattr(config, 'HELIUS_API_KEYS', [])
if not HELIUS_API_KEYS and hasattr(config, 'HELIUS_API_KEY') and config.HELIUS_API_KEY:
    HELIUS_API_KEYS = [config.HELIUS_API_KEY]

# ساخت عمومی iterator چرخشی برای کلیدهای هلیوس
helius_key_cycle = itertools.cycle(HELIUS_API_KEYS) if HELIUS_API_KEYS else None

DEFAULT_RPCS = [f"https://mainnet.helius-rpc.com/?api-key={k}" for k in HELIUS_API_KEYS] + [
    "https://api.mainnet-beta.solana.com",
    "https://solana-rpc.publicnode.com"
]
RPC_URLS = getattr(config, 'RPC_URLS', DEFAULT_RPCS)

PHOENIX_PROGRAM_IDS = {
    "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY",  # Phoenix DEX Main Program
    "EMBERpYNE6ehWmXymZZS2skiFmCa9V5dp14e1iduM5qy",  # Ember Collateral/Margin Program
    "PhUsd11YkbjSaWjFncfAAmatntsjx3MgDR9B6g1ks3A",  # Phoenix USDC Mint
}

session = requests.Session()
session.headers.update({
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
})


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
        session.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"⚠️ Telegram Alert Error: {e}")


def get_latest_signatures(wallet_address: str, limit: int = 5):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [wallet_address, {"limit": limit}]
    }
    
    for rpc_url in RPC_URLS:
        try:
            res = session.post(rpc_url, json=payload, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if "result" in data:
                    return data["result"]
        except Exception:
            continue
            
    return []


def get_parsed_transaction_helius(signature: str):
    """دریافت اطلاعات دکود شده با چرخش بین کلیدهای Helius"""
    if not HELIUS_API_KEYS:
        return None

    # بررسی تک‌تک کلیدها به صورت چرخشی در صورت بروز خطا
    for _ in range(len(HELIUS_API_KEYS)):
        current_key = next(helius_key_cycle)
        url = f"https://api.helius.xyz/v0/transactions?api-key={current_key}"
        payload = {"transactions": [signature]}
        
        try:
            res = session.post(url, json=payload, timeout=6)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
            elif res.status_code == 429:
                # کلید به سقف درخواست رسیده؛ سوییچ فوری به کلید بعدی
                continue
        except Exception:
            continue

    return None


def is_phoenix_transaction(parsed_tx, raw_logs=None) -> bool:
    if parsed_tx:
        source = str(parsed_tx.get("source", "")).upper()
        if "PHOENIX" in source or "EMBER" in source:
            return True

        for inst in parsed_tx.get("instructions", []):
            if inst.get("programId", "") in PHOENIX_PROGRAM_IDS:
                return True

        for acc in parsed_tx.get("accountData", []):
            if acc.get("account", "") in PHOENIX_PROGRAM_IDS:
                return True

    if raw_logs:
        logs_str = " ".join(raw_logs).lower()
        if any(kw in logs_str for kw in ["phoenix", "ember", "phusd", "phoenixz8"]):
            return True

    return False


def extract_phoenix_trade_details(parsed_tx):
    if not parsed_tx:
        return "Phoenix Activity", "جزئیات تکمیلی دریافت نشد."

    description = parsed_tx.get("description", "بدون شرح متنی")
    tx_type = parsed_tx.get("type", "UNKNOWN")

    transfers_summary = []
    for tt in parsed_tx.get("tokenTransfers", []):
        amount = tt.get("tokenAmount", 0)
        mint = tt.get("mint", "")
        symbol = f"{mint[:4]}...{mint[-4:]}" if len(mint) > 8 else "Token"
        transfers_summary.append(f"• {amount} ({symbol})")

    for nt in parsed_tx.get("nativeTransfers", []):
        sol_amount = nt.get("amount", 0) / 1e9
        if sol_amount > 0.001:
            transfers_summary.append(f"• {sol_amount:.4f} SOL")

    details_str = f"<b>شرح حرکت:</b> {description}\n"
    if transfers_summary:
        details_str += "<b>حجم جابجایی:</b>\n" + "\n".join(transfers_summary[:4])

    return f"⚡ {tx_type}", details_str


def get_transaction_details_rpc_fallback(signature: str):
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
            res = session.post(rpc_url, json=payload, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if "result" in data and data["result"]:
                    return data["result"]
        except Exception:
            continue
    return None


def start_monitoring():
    print(f"🚀 Phoenix Monitoring Bot Started - Loaded {len(HELIUS_API_KEYS)} Helius API Key(s)...")
    last_processed_signatures = {}

    for wallet_addr, wallet_name in TARGET_WALLETS.items():
        sigs = get_latest_signatures(wallet_addr, limit=1)
        if sigs:
            last_processed_signatures[wallet_addr] = sigs[0]["signature"]
            print(f"✅ Registered [{wallet_name}] - Last Sig: {sigs[0]['signature'][:10]}...")
        else:
            last_processed_signatures[wallet_addr] = None
        time.sleep(0.2)

    send_telegram_alert(f"🚀 <b>Phoenix Monitoring Bot is live with Multi-Key Helius ({len(HELIUS_API_KEYS)} Keys).</b>")

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

                        parsed_tx = get_parsed_transaction_helius(sig)
                        raw_logs = []
                        if not parsed_tx:
                            tx_details = get_transaction_details_rpc_fallback(sig)
                            if tx_details and "meta" in tx_details:
                                raw_logs = tx_details["meta"].get("logMessages", [])

                        if not is_phoenix_transaction(parsed_tx, raw_logs):
                            print(f"ℹ️ Skipping non-Phoenix transaction: {sig[:8]}...")
                            last_processed_signatures[wallet_addr] = sig
                            continue

                        if parsed_tx:
                            action_type, trade_details = extract_phoenix_trade_details(parsed_tx)
                        else:
                            action_type = "⚡ Phoenix Contract Interaction"
                            trade_details = "جزئیات تکمیلی دریافت نشد."

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
                        print(f"🚀 Alert Sent for {sig[:10]}!")
                        last_processed_signatures[wallet_addr] = sig

                time.sleep(0.2)
            time.sleep(POLL_INTERVAL)
        except Exception as e:
            print(f"⚠️ Loop Error: {e}")
            time.sleep(3)


if __name__ == "__main__":
    start_monitoring()
