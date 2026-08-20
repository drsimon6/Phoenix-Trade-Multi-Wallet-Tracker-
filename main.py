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

KNOWN_TOKENS = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "PhUsd11YkbjSaWjFncfAAmatntsjx3MgDR9B6g1ks3A": "phUSD",
    "So11111111111111111111111111111111111111112": "SOL",
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": "JUP",
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": "BONK"
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

    if raw_logs:
        logs_str = " ".join(raw_logs).lower()
        if any(kw in logs_str for kw in ["phoenix", "ember", "phusd", "phoenixz8"]):
            return True

    return False


def extract_inner_transfers(tx_details, parsed_tx, target_wallet):
    """استخراج عمیق جابه‌جایی توکن‌ها از Inner Instructions و Helius Token Transfers"""
    transfers = []

    # ۱. استخراج از Helius Token Transfers
    if parsed_tx and "tokenTransfers" in parsed_tx:
        for tt in parsed_tx.get("tokenTransfers", []):
            amt = float(tt.get("tokenAmount", 0) or 0)
            mint = tt.get("mint", "")
            symbol = KNOWN_TOKENS.get(mint, f"{mint[:4]}...{mint[-4:]}" if len(mint) > 8 else "Token")
            from_acc = tt.get("fromUserAccount", "")
            to_acc = tt.get("toUserAccount", "")

            if amt > 0:
                if to_acc == target_wallet or tt.get("userAccount") == target_wallet:
                    transfers.append(("🟢 دریافت/آزادشده", amt, symbol))
                elif from_acc == target_wallet:
                    transfers.append(("🔴 پرداخت/قفل‌شده", amt, symbol))
                else:
                    transfers.append(("⚡ جابه‌جایی در Vault", amt, symbol))

    # ۲. استخراج مستقیم از Inner Instructions شبکه سولانا
    if not transfers and tx_details and "meta" in tx_details:
        inner_instructions = tx_details["meta"].get("innerInstructions", [])
        for group in inner_instructions:
            for inst in group.get("instructions", []):
                parsed = inst.get("parsed")
                if isinstance(parsed, dict):
                    info = parsed.get("info", {})
                    inst_type = parsed.get("type")
                    if inst_type in ["transfer", "transferChecked"]:
                        amt = 0.0
                        if "tokenAmount" in info:
                            amt = float(info["tokenAmount"].get("uiAmount") or 0)
                        elif "amount" in info:
                            # در صورت جابه‌جایی با اعشار استاندارد
                            amt = float(info["amount"]) / 1e6

                        if amt > 0:
                            mint = info.get("mint", "")
                            symbol = KNOWN_TOKENS.get(mint, "USDC/Token")
                            transfers.append(("⚡ حجم درگیر در دستور", amt, symbol))

    return transfers


def parse_trade_details_comprehensive(parsed_tx, tx_details, raw_logs, target_wallet):
    logs_text = " ".join(raw_logs).lower() if raw_logs else ""
    
    if "placelimit" in logs_text or "place_limit" in logs_text:
        action_type = "📥 ثبت سفارش لیمیت (Limit Order)"
    elif "placemarket" in logs_text or "place_market" in logs_text:
        action_type = "⚡ معامله مارکت (Market Order)"
    elif "cancel" in logs_text:
        action_type = "❌ لغو سفارش (Cancel Order)"
    else:
        action_type = "⚡ معامله / مدیریت سفارش Phoenix"

    transfers = extract_inner_transfers(tx_details, parsed_tx, target_wallet)

    if transfers:
        lines = []
        base_amt = 0.0
        quote_amt = 0.0
        for label, amt, symbol in transfers:
            lines.append(f"{label}: <b>{amt:,.4f} {symbol}</b>")
            if symbol in ["USDC", "phUSD"]:
                quote_amt = amt
            else:
                base_amt = amt

        if base_amt > 0 and quote_amt > 0:
            calc_price = quote_amt / base_amt
            lines.append(f"💵 <b>قیمت محاسبه‌شده:</b> ${calc_price:,.4f}")

        details_text = "📊 <b>جزئیات حجم و توکن‌های معامله:</b>\n" + "\n".join(lines)
    elif parsed_tx and parsed_tx.get("description"):
        details_text = f"📊 <b>خلاصه شبکه:</b>\n<i>{parsed_tx.get('description')}</i>"
    else:
        details_text = "📝 <i>سفارش در اردر بوک ثبت/ویرایش شد (بدون جابه‌جایی آنی توکن).</i>"

    return action_type, details_text


def start_monitoring():
    print(f"🚀 Phoenix Deep Inner Instruction Engine Active...")
    last_processed_signatures = {}

    for wallet_addr, wallet_name in TARGET_WALLETS.items():
        sigs = get_latest_signatures(wallet_addr, limit=1)
        if sigs:
            last_processed_signatures[wallet_addr] = sigs[0]["signature"]
            print(f"✅ Registered [{wallet_name}]")
        else:
            last_processed_signatures[wallet_addr] = None
        time.sleep(0.2)

    send_telegram_alert("🚀 <b>Phoenix Tracker Engine Updated with Inner Instruction Parsing.</b>")

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
                        tx_details = get_transaction_details_rpc_fallback(sig)

                        raw_logs = []
                        if tx_details and "meta" in tx_details:
                            raw_logs = tx_details["meta"].get("logMessages", [])

                        if not is_phoenix_transaction(parsed_tx, raw_logs):
                            last_processed_signatures[wallet_addr] = sig
                            continue

                        action_type, trade_details = parse_trade_details_comprehensive(parsed_tx, tx_details, raw_logs, wallet_addr)
                        phoenix_portfolio_url = f"https://www.phoenix.trade/portfolio?ghost={wallet_addr}"

                        alert_text = (
                            f"🦅 <b>تراکنش جدید Phoenix ثبت شد!</b>\n\n"
                            f"🏷 <b>نام ولت:</b> {wallet_name}\n"
                            f"👤 <b>آدرس:</b> <code>{wallet_addr[:6]}...{wallet_addr[-4:]}</code>\n"
                            f"📌 <b>نوع دستور:</b> {action_type}\n"
                            f"📊 <b>وضعیت:</b> {status}\n"
                            f"⏰ <b>زمان:</b> {time_str}\n\n"
                            f"{trade_details}\n\n"
                            f"💡 <i>جهت مشاهده uPnL، قیمت لیکویید و پوزیشن‌های فعال:</i>\n"
                            f"🔗 <a href='https://solscan.io/tx/{sig}'>مشاهده تراکنش در Solscan</a>\n"
                            f"🦅 <a href='{phoenix_portfolio_url}'>مشاهده پورتفولیو زنده در Phoenix</a>"
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
