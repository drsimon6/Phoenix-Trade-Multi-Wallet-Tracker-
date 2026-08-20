import asyncio
import aiohttp
import time
from datetime import datetime
import sys

try:
    import config
except ImportError:
    print("\n⚠️ Error: 'config.py' not found!")
    sys.exit(1)

TARGET_WALLETS = config.TARGET_WALLETS
POLL_INTERVAL = getattr(config, 'POLL_INTERVAL', 1)  # کاهش فاصله بررسی به ۱ ثانیه
TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = config.TELEGRAM_CHAT_ID

RPC_URLS = getattr(config, 'RPC_URLS', [
    "https://api.mainnet-beta.solana.com",
    "https://solana-rpc.publicnode.com"
])


async def send_telegram_alert(session: aiohttp.ClientSession, message: str):
    """ارسال سریع و غیرمسدودکننده به تلگرام"""
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
        async with session.post(url, json=payload, timeout=3) as resp:
            pass
    except Exception as e:
        print(f"⚠️ Telegram Error: {e}")


async def fetch_rpc(session: aiohttp.ClientSession, method: str, params: list):
    """اجرای سریع درخواست‌های RPC"""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    for rpc_url in RPC_URLS:
        try:
            async with session.post(rpc_url, json=payload, timeout=2.5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "result" in data:
                        return data["result"]
        except Exception:
            continue
    return None


def quick_detect_action(logs: list) -> str:
    """تشخیص فوری نوع دستور از روی لاگ‌های متنی بدون کندی سرعت"""
    if not logs:
        return "⚡ معامله / مدیریت سفارش Phoenix"
    
    logs_str = " ".join(logs).lower()
    if "placelimit" in logs_str or "place_limit" in logs_str:
        return "📥 ثبت سفارش لیمیت (Limit Order)"
    elif "placemarket" in logs_str or "place_market" in logs_str:
        return "⚡ معامله مارکت (Market Order)"
    elif "cancel" in logs_str:
        return "❌ لغو سفارش (Cancel Order)"
    
    return "⚡ معامله / مدیریت سفارش Phoenix"


async def monitor_wallet(session: aiohttp.ClientSession, wallet_addr: str, wallet_name: str, last_signatures: dict):
    """بررسی سریع تراکنش‌های ولت"""
    sigs = await fetch_rpc(session, "getSignaturesForAddress", [wallet_addr, {"limit": 3}])
    if not sigs:
        return

    last_sig = last_signatures.get(wallet_addr)
    if last_sig is None:
        last_signatures[wallet_addr] = sigs[0]["signature"]
        print(f"✅ Fast Monitoring set for [{wallet_name}]")
        return

    new_sigs = []
    for sig_info in sigs:
        sig = sig_info["signature"]
        if sig == last_sig:
            break
        new_sigs.append(sig_info)

    if new_sigs:
        # به‌روزرسانی سریع آخرین امضا
        last_signatures[wallet_addr] = new_sigs[0]["signature"]

        for sig_info in reversed(new_sigs):
            sig = sig_info["signature"]
            err = sig_info.get("err")
            block_time = sig_info.get("blockTime")
            
            time_str = datetime.fromtimestamp(block_time).strftime('%Y-%m-%d %H:%M:%S') if block_time else "Unknown"
            status = "❌ Failed" if err else "✅ Success"

            # استخراج سبک لاگ‌ها جهت تعیین نوع دستور
            tx_info = await fetch_rpc(session, "getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
            raw_logs = tx_info.get("meta", {}).get("logMessages", []) if tx_info else []
            
            action_type = quick_detect_action(raw_logs)
            phoenix_portfolio_url = f"https://www.phoenix.trade/portfolio?ghost={wallet_addr}"

            alert_text = (
                f"🦅 <b>تراکنش جدید Phoenix ثبت شد!</b>\n\n"
                f"🏷 <b>نام ولت:</b> {wallet_name}\n"
                f"👤 <b>آدرس:</b> <code>{wallet_addr[:6]}...{wallet_addr[-4:]}</code>\n"
                f"📌 <b>نوع دستور:</b> {action_type}\n"
                f"📊 <b>وضعیت:</b> {status}\n"
                f"⏰ <b>زمان:</b> {time_str}\n\n"
                f"💡 <i>جهت مشاهده جزئیات پوزیشن و پورتفولیو:</i>\n"
                f"🔗 <a href='https://solscan.io/tx/{sig}'>مشاهده تراکنش در Solscan</a>\n"
                f"🦅 <a href='{phoenix_portfolio_url}'>مشاهده پورتفولیو زنده در Phoenix</a>"
            )

            # ارسال آنلاین و بی‌درنگ
            asyncio.create_task(send_telegram_alert(session, alert_text))
            print(f"⚡ FAST Alert sent for {sig[:8]}")


async def main():
    print("🚀 Ultra-Fast Phoenix Tracker Active...")
    last_signatures = {}

    async with aiohttp.ClientSession() as session:
        # اعلان شروع به تلگرام
        await send_telegram_alert(session, "🚀 <b>High-Speed Phoenix Engine Started.</b>")

        while True:
            start_time = time.time()
            
            tasks = [
                monitor_wallet(session, addr, name, last_signatures)
                for addr, name in TARGET_WALLETS.items()
            ]
            await asyncio.gather(*tasks)

            # تنظیم زمان خواب پویا برای حفظ فاصله زمانی دقیق
            elapsed = time.time() - start_time
            sleep_time = max(0.1, POLL_INTERVAL - elapsed)
            await asyncio.sleep(sleep_time)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot Stopped.")
