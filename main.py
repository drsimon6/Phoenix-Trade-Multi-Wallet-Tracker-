import time
import requests
from datetime import datetime
import sys
import itertools

try:
    import config
except ImportError:
    print("\n⚠️ Error: 'config.py' not found! Please create it before running.")
    sys.exit(1)

TARGET_WALLETS = config.TARGET_WALLETS
POLL_INTERVAL = getattr(config, 'POLL_INTERVAL', 3)
TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = config.TELEGRAM_CHAT_ID

HELIUS_API_KEYS = getattr(config, 'HELIUS_API_KEYS', [])
if not HELIUS_API_KEYS and hasattr(config, 'HELIUS_API_KEY') and config.HELIUS_API_KEY:
    HELIUS_API_KEYS = [config.HELIUS_API_KEY]

helius_key_cycle = itertools.cycle(HELIUS_API_KEYS) if HELIUS_API_KEYS else None

DEFAULT_RPCS = [f"https://mainnet.helius-rpc.com/?api-key={k}" for k in HELIUS_API_KEYS] + [
    "https://api.mainnet-beta.solana.com",
    "https://solana-rpc.publicnode.com"
]
RPC_URLS = getattr(config, 'RPC_URLS', DEFAULT_RPCS)

PHOENIX_PROGRAM_IDS = {
    "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY",
    "EMBERpYNE6ehWmXymZZS2skiFmCa9V5dp14e1iduM5qy",
    "PhUsd11YkbjSaWjFncfAAmatntsjx3MgDR9B6g1ks3A",
}

# شناسه توکن‌های شناخته‌شده جهت تشخیص مارکت و قیمت
KNOWN_TOKENS = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "PhUsd11YkbjSaWjFncfAAmatntsjx3MgDR9B6g1ks3A": "phUSD",
    "So11111111111111111111111111111111111111112": "SOL",
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": "JUP",
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": "BONK"
}

PHOENIX_INSTRUCTION_MAP = {
    "placelimitorder": "📥 ثبت سفارش لیمیت",
    "placemarketorder": "⚡ معامله مارکت",
    "swap": "🔄 معامله آنی (Swap)",
    "cancelorder": "❌ لغو سفارش",
    "depositfunds": "📥 واریز مارجین / پورتفولیو",
    "withdrawfunds": "📤 برداشت از پورتفولیو",
    "initializeaccount": "🆕 افتتاح حساب Phoenix",
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
    if not HELIUS_API_KEYS:
        return None

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
                continue
        except Exception:
            continue
    return None


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


def is_phoenix_transaction(parsed_tx, raw_logs=None) -> bool:
    if parsed_tx:
        source = str(parsed_tx.get("source", "")).upper()
        if "PHOENIX" in source or "EMBER" in source:
            return True

        for inst in parsed_tx.get("instructions", []):
            if inst.get("programId", "") in PHOENIX_PROGRAM_IDS:
                return True

        for inner_group in parsed_tx.get("innerInstructions", []):
            for inst in inner_group.get("instructions", []):
                if inst.get("programId", "") in PHOENIX_PROGRAM_IDS:
                    return True

    if raw_logs:
        logs_str = " ".join(raw_logs).lower()
        if any(kw in logs_str for kw in ["phoenix", "ember", "phusd", "phoenixz8"]):
            return True

    return False


def parse_trade_metrics(parsed_tx, target_wallet):
    """محاسبه دقیق جهت معامله (خرید/فروش)، جفت‌ارز، حجم و قیمت میانگین اجرا"""
    if not parsed_tx:
        return None

    incoming_tokens = []
    outgoing_tokens = []

    # بررسی انتقال توکن‌ها
    for tt in parsed_tx.get("tokenTransfers", []):
        amount = float(tt.get("tokenAmount", 0))
        mint = tt.get("mint", "")
        symbol = KNOWN_TOKENS.get(mint, f"{mint[:4]}...{mint[-4:]}")
        
        if tt.get("toUserAccount") == target_wallet and amount > 0:
            incoming_tokens.append({"symbol": symbol, "amount": amount, "mint": mint})
        elif tt.get("fromUserAccount") == target_wallet and amount > 0:
            outgoing_tokens.append({"symbol": symbol, "amount": amount, "mint": mint})

    # بررسی انتقال SOL
    for nt in parsed_tx.get("nativeTransfers", []):
        amount = float(nt.get("amount", 0)) / 1e9
        if amount > 0.005:
            if nt.get("toUserAccount") == target_wallet:
                incoming_tokens.append({"symbol": "SOL", "amount": amount, "mint": "SOL"})
            elif nt.get("fromUserAccount") == target_wallet:
                outgoing_tokens.append({"symbol": "SOL", "amount": amount, "mint": "SOL"})

    # تحلیل خرید یا فروش
    side = "UNKNOWN"
    base_asset = "Asset"
    quote_asset = "USDC"
    base_amount = 0.0
    quote_amount = 0.0

    in_usdc = next((t for t in incoming_tokens if t["symbol"] in ["USDC", "phUSD"]), None)
    out_usdc = next((t for t in outgoing_tokens if t["symbol"] in ["USDC", "phUSD"]), None)

    in_crypto = next((t for t in incoming_tokens if t["symbol"] not in ["USDC", "phUSD"]), None)
    out_crypto = next((t for t in outgoing_tokens if t["symbol"] not in ["USDC", "phUSD"]), None)

    if out_usdc and in_crypto:
        side = "🟢 BUY (خرید / Long)"
        base_asset = in_crypto["symbol"]
        quote_asset = out_usdc["symbol"]
        base_amount = in_crypto["amount"]
        quote_amount = out_usdc["amount"]
    elif in_usdc and out_crypto:
        side = "🔴 SELL (فروش / Short)"
        base_asset = out_crypto["symbol"]
        quote_asset = in_usdc["symbol"]
        base_amount = out_crypto["amount"]
        quote_amount = in_usdc["amount"]

    price = (quote_amount / base_amount) if base_amount > 0 else 0.0

    return {
        "market": f"{base_asset}/{quote_asset}",
        "side": side,
        "size": f"{base_amount:,.4f} {base_asset}",
        "value": f"{quote_amount:,.2f} {quote_asset}",
        "price": f"${price:,.4f}" if price > 0 else "N/A"
    }


def start_monitoring():
    print(f"🚀 Phoenix Advanced Perps/Spot Tracker Active ({len(HELIUS_API_KEYS)} Keys)...")
    last_processed_signatures = {}

    for wallet_addr, wallet_name in TARGET_WALLETS.items():
        sigs = get_latest_signatures(wallet_addr, limit=1)
        if sigs:
            last_processed_signatures[wallet_addr] = sigs[0]["signature"]
            print(f"✅ Registered [{wallet_name}] - Last Sig: {sigs[0]['signature'][:10]}...")
        else:
            last_processed_signatures[wallet_addr] = None
        time.sleep(0.2)

    send_telegram_alert("🚀 <b>Phoenix Advanced Perps Tracker Online.</b>")

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
                        
                        if not is_phoenix_transaction(parsed_tx):
                            tx_details = get_transaction_details_rpc_fallback(sig)
                            if tx_details and "meta" in tx_details:
                                raw_logs = tx_details["meta"].get("logMessages", [])

                        if not is_phoenix_transaction(parsed_tx, raw_logs):
                            print(f"ℹ️ Skipping non-Phoenix transaction: {sig[:8]}...")
                            last_processed_signatures[wallet_addr] = sig
                            continue

                        # استخراج سنجه‌های معامله
                        metrics = parse_trade_metrics(parsed_tx, wallet_addr)
                        phoenix_portfolio_url = f"https://www.phoenix.trade/portfolio?ghost={wallet_addr}"

                        if metrics and metrics["side"] != "UNKNOWN":
                            trade_info_block = (
                                f"📊 <b>Market:</b> {metrics['market']}\n"
                                f"🎯 <b>Side:</b> {metrics['side']}\n"
                                f"📏 <b>Size:</b> {metrics['size']}\n"
                                f"💵 <b>Position Value:</b> {metrics['value']}\n"
                                f"🏷 <b>Execution Price:</b> {metrics['price']}\n"
                            )
                        else:
                            trade_info_block = "📝 <b>نوع دستور:</b> تغییر تنظیمات حساب / مدیریت سفارشات"

                        alert_text = (
                            f"🦅 <b>تراکنش جدید Phoenix ثبت شد!</b>\n\n"
                            f"🏷 <b>نام ولت:</b> {wallet_name}\n"
                            f"👤 <b>آدرس:</b> <code>{wallet_addr[:6]}...{wallet_addr[-4:]}</code>\n"
                            f"📊 <b>وضعیت:</b> {status}\n"
                            f"⏰ <b>زمان:</b> {time_str}\n\n"
                            f"{trade_info_block}\n\n"
                            f"💡 <i>جهت مشاهده uPnL، قیمت لیکویید و Margin زنده به لینک پورتفولیو مراجعه کنید:</i>\n"
                            f"🔗 <a href='https://solscan.io/tx/{sig}'>مشاهده تراکنش در Solscan</a>\n"
                            f"🦅 <a href='{phoenix_portfolio_url}'>مشاهده پورتفولیو زنده در Phoenix</a>"
                        )
                        send_telegram_alert(alert_text)
                        print(f"🚀 Detailed Alert Sent for {sig[:10]}!")
                        last_processed_signatures[wallet_addr] = sig

                time.sleep(0.2)
            time.sleep(POLL_INTERVAL)
        except Exception as e:
            print(f"⚠️ Loop Error: {e}")
            time.sleep(3)


if __name__ == "__main__":
    start_monitoring()
