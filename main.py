import time
import requests
from datetime import datetime
import sys
import itertools
import re

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

# دیکشنری کامل تمام توکن‌ها، سهام‌ها و کمودیتی‌ها
KNOWN_TOKENS = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "PhUsd11YkbjSaWjFncfAAmatntsjx3MgDR9B6g1ks3A": "phUSD",
    "So11111111111111111111111111111111111111112": "SOL",
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": "JUP",
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": "BONK",
    "BTC": "BTC", "ETH": "ETH", "GOLD": "GOLD", "CRCL": "CRCL", "HYPE": "HYPE",
    "SNDK": "SNDK", "ARM": "ARM", "MSTR": "MSTR", "LIT": "LIT", "NBIS": "NBIS",
    "HOOD": "HOOD", "CBRS": "CBRS", "MU": "MU", "AMD": "AMD", "ZEC": "ZEC",
    "MON": "MON", "SPCX": "SPCX", "PUMP": "PUMP", "QCOM": "QCOM", "CRWV": "CRWV",
    "AMZN": "AMZN", "INTC": "INTC", "TSLA": "TSLA", "NVDA": "NVDA", "ASML": "ASML",
    "TSM": "TSM", "FARTCOIN": "FARTCOIN", "AAPL": "AAPL", "GOOGL": "GOOGL",
    "META": "META", "AMAT": "AMAT", "WLD": "WLD", "MET": "MET", "BNB": "BNB",
    "MSFT": "MSFT", "ENA": "ENA", "ADA": "ADA", "COIN": "COIN", "NEAR": "NEAR",
    "PLTR": "PLTR", "ANSEM": "ANSEM", "WTIOIL": "WTIOIL", "SUI": "SUI",
    "COPPER": "COPPER", "RENDER": "RENDER", "AAVE": "AAVE", "CRV": "CRV",
    "AVGO": "AVGO", "SKHY": "SKHY", "JTO": "JTO", "SILVER": "SILVER",
    "VIRTUAL": "VIRTUAL", "MORPHO": "MORPHO", "XLM": "XLM", "XPL": "XPL",
    "ONDO": "ONDO", "VVV": "VVV", "BABA": "BABA", "TAO": "TAO", "DOGE": "DOGE",
    "XRP": "XRP", "LINK": "LINK", "TRX": "TRX", "FET": "FET", "MEGA": "MEGA",
    "SKR": "SKR", "CHIP": "CHIP"
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
    return []


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


def extract_trade_data(parsed_tx, tx_details, raw_logs, target_wallet):
    """استخراج پیشرفته توکن، حجم، قیمت و جهت معامله"""
    trade_info = []
    base_asset = None
    amount = 0.0
    price = 0.0

    # ۱. اسکن لاگ‌ها برای شناسایی مارکت و مقادیر
    full_text = " ".join(raw_logs) if raw_logs else ""
    if parsed_tx and parsed_tx.get("description"):
        full_text += " " + parsed_tx.get("description")

    # پیدا کردن نام توکن از لیست کامل
    for token_symbol in KNOWN_TOKENS.values():
        if token_symbol in ["USDC", "phUSD"]:
            continue
        pattern = r"\bداده‌های ورودی پردازش شده و به یک ساختار دیکشنری استاندارد پایتون (Python Dictionary) تبدیل شدند. همچنین یک کد پایتون جهت استخراج خودکار این فرمت متنی قرار داده شده است.

### ساختار دیکشنری پایتون (داده‌های استخراج‌شده)

```python
market_data = {
    "BTC": {"leverage": "40x", "price": "$71,842", "change_24h": "11.55%", "volume": "$41,936,854", "open_interest": "$7,250,402", "funding_rate": "-0.0030%"},
    "GOLD": {"leverage": "25xISO", "price": "$4,487.10", "change_24h": "2.85%", "volume": "$890,926", "open_interest": "$167,647", "funding_rate": "0.0006%"},
    "ETH": {"leverage": "25x", "price": "$2,286.50", "change_24h": "19.17%", "volume": "$17,456,566", "open_interest": "$5,587,118", "funding_rate": "0.0023%"},
    "SOL": {"leverage": "25x", "price": "$87.55", "change_24h": "13.29%", "volume": "$8,376,511", "open_interest": "$2,651,575", "funding_rate": "0.0027%"},
    "CRCL": {"leverage": "10x", "price": "$84.840", "change_24h": "19.13%", "volume": "$1,969,040", "open_interest": "$34,013", "funding_rate": "0.0020%"},
    "HYPE": {"leverage": "10x", "price": "$73.334", "change_24h": "25.81%", "volume": "$1,894,398", "open_interest": "$372,198", "funding_rate": "0.0045%"},
    "SNDK": {"leverage": "15x", "price": "$1,590.50", "change_24h": "-1.01%", "volume": "$1,644,540", "open_interest": "$332,999", "funding_rate": "0.0006%"},
    "ARM": {"leverage": "10x", "price": "$249.03", "change_24h": "-0.54%", "volume": "$1,640,357", "open_interest": "$58,767", "funding_rate": "0.0008%"},
    "MSTR": {"leverage": "10x", "price": "$114.431", "change_24h": "23.35%", "volume": "$1,297,391", "open_interest": "$50,778", "funding_rate": "0.0018%"},
    "LIT": {"leverage": "5x", "price": "$2.8096", "change_24h": "23.16%", "volume": "$987,973", "open_interest": "$172,668", "funding_rate": "0.0028%"},
    "NBIS": {"leverage": "10x", "price": "$228.67", "change_24h": "-5.83%", "volume": "$880,851", "open_interest": "$35,980", "funding_rate": "0.0058%"},
    "HOOD": {"leverage": "10x", "price": "$101.17", "change_24h": "10.91%", "volume": "$850,721", "open_interest": "$14,528", "funding_rate": "0.0009%"},
    "CBRS": {"leverage": "10x", "price": "$216.28", "change_24h": "-0.73%", "volume": "$828,508", "open_interest": "$7,376", "funding_rate": "-0.0031%"},
    "MU": {"leverage": "15x", "price": "$945.40", "change_24h": "1.43%", "volume": "$772,737", "open_interest": "$741,185", "funding_rate": "0.0033%"},
    "AMD": {"leverage": "10x", "price": "$468.74", "change_24h": "-2.22%", "volume": "$638,782", "open_interest": "$53,974", "funding_rate": "0.0029%"},
    "ZEC": {"leverage": "10x", "price": "$560.78", "change_24h": "10.47%", "volume": "$628,981", "open_interest": "$143,335", "funding_rate": "0.0014%"},
    "MON": {"leverage": "5x", "price": "$0.025342", "change_24h": "16.12%", "volume": "$620,274", "open_interest": "$122,687", "funding_rate": "0.0035%"},
    "SPCX": {"leverage": "15x", "price": "$137.65", "change_24h": "-3.16%", "volume": "$550,388", "open_interest": "$214,190", "funding_rate": "0.0006%"},
    "PUMP": {"leverage": "10x", "price": "$0.0033111", "change_24h": "11.11%", "volume": "$488,710", "open_interest": "$48,349", "funding_rate": "-0.0008%"},
    "QCOM": {"leverage": "10x", "price": "$162.57", "change_24h": "2.37%", "volume": "$479,345", "open_interest": "$87,343", "funding_rate": "0.0026%"},
    "CRWV": {"leverage": "10x", "price": "$91.44", "change_24h": "0.05%", "volume": "$404,713", "open_interest": "$1,420", "funding_rate": "0.0012%"},
    "AMZN": {"leverage": "20x", "price": "$265.92", "change_24h": "2.04%", "volume": "$363,858", "open_interest": "$53,692", "funding_rate": "0.0008%"},
    "INTC": {"leverage": "10x", "price": "$93.20", "change_24h": "-1.81%", "volume": "$325,188", "open_interest": "$42,274", "funding_rate": "0.0000%"},
    "TSLA": {"leverage": "20x", "price": "$348.83", "change_24h": "3.77%", "volume": "$293,143", "open_interest": "$225,669", "funding_rate": "0.0021%"},
    "NVDA": {"leverage": "20x", "price": "$218.55", "change_24h": "-0.69%", "volume": "$251,278", "open_interest": "$235,744", "funding_rate": "0.0010%"},
    "ASML": {"leverage": "10x", "price": "$1,763.10", "change_24h": "-1.67%", "volume": "$243,809", "open_interest": "$12,500", "funding_rate": "0.0007%"},
    "TSM": {"leverage": "10x", "price": "$413.56", "change_24h": "0.00%", "volume": "$230,783", "open_interest": "$154,485", "funding_rate": "0.0033%"},
    "FARTCOIN": {"leverage": "10x", "price": "$0.15544", "change_24h": "8.94%", "volume": "$211,730", "open_interest": "$38,089", "funding_rate": "0.0020%"},
    "AAPL": {"leverage": "20x", "price": "$315.98", "change_24h": "2.04%", "volume": "$191,178", "open_interest": "$202,885", "funding_rate": "0.0009%"},
    "GOOGL": {"leverage": "20x", "price": "$343.78", "change_24h": "0.22%", "volume": "$169,092", "open_interest": "$245,966", "funding_rate": "0.0019%"},
    "META": {"leverage": "20x", "price": "$550.04", "change_24h": "0.99%", "volume": "$164,043", "open_interest": "$294,719", "funding_rate": "0.0019%"},
    "AMAT": {"leverage": "10x", "price": "$497.21", "change_24h": "-2.50%", "volume": "$161,742", "open_interest": "$23,111", "funding_rate": "0.0012%"},
    "WLD": {"leverage": "10x", "price": "$0.36338", "change_24h": "14.52%", "volume": "$151,097", "open_interest": "$2,845", "funding_rate": "0.0008%"},
    "MET": {"leverage": "5x", "price": "$0.21309", "change_24h": "24.02%", "volume": "$145,471", "open_interest": "$10,578", "funding_rate": "-0.0030%"},
    "BNB": {"leverage": "10x", "price": "$642.63", "change_24h": "6.59%", "volume": "$142,814", "open_interest": "$89,653", "funding_rate": "0.0016%"},
    "MSFT": {"leverage": "20x", "price": "$483.37", "change_24h": "0.51%", "volume": "$140,068", "open_interest": "$32,495", "funding_rate": "0.0004%"},
    "ENA": {"leverage": "10x", "price": "$0.09799", "change_24h": "16.23%", "volume": "$97,763", "open_interest": "$39,204", "funding_rate": "0.0031%"},
    "ADA": {"leverage": "10x", "price": "$0.19119", "change_24h": "9.90%", "volume": "$95,759", "open_interest": "$6,456", "funding_rate": "-0.0031%"},
    "COIN": {"leverage": "10x", "price": "$172.72", "change_24h": "17.91%", "volume": "$93,541", "open_interest": "$11,257", "funding_rate": "0.0028%"},
    "NEAR": {"leverage": "10x", "price": "$1.7649", "change_24h": "10.14%", "volume": "$85,018", "open_interest": "$120,850", "funding_rate": "0.0018%"},
    "PLTR": {"leverage": "10x", "price": "$174.82", "change_24h": "2.37%", "volume": "$84,831", "open_interest": "$93,453", "funding_rate": "0.0015%"},
    "ANSEM": {"leverage": "3xISO", "price": "$0.24049", "change_24h": "-0.12%", "volume": "$76,190", "open_interest": "$76,945", "funding_rate": "0.0048%"},
    "WTIOIL": {"leverage": "20xISO", "price": "$86.55", "change_24h": "1.90%", "volume": "$75,945", "open_interest": "$30,002", "funding_rate": "0.0000%"},
    "JUP": {"leverage": "10x", "price": "$0.18894", "change_24h": "13.28%", "volume": "$69,562", "open_interest": "$106,654", "funding_rate": "0.0018%"},
    "SUI": {"leverage": "10x", "price": "$0.72405", "change_24h": "10.17%", "volume": "$65,307", "open_interest": "$29,499", "funding_rate": "0.0015%"},
    "COPPER": {"leverage": "20xISO", "price": "$6.5722", "change_24h": "0.72%", "volume": "$65,019", "open_interest": "$116,021", "funding_rate": "0.0041%"},
    "RENDER": {"leverage": "5x", "price": "$1.4006", "change_24h": "10.50%", "volume": "$63,921", "open_interest": "$20,979", "funding_rate": "-0.0009%"},
    "AAVE": {"leverage": "10x", "price": "$97.50", "change_24h": "10.93%", "volume": "$63,358", "open_interest": "$8,247", "funding_rate": "0.0006%"},
    "CRV": {"leverage": "10x", "price": "$0.26961", "change_24h": "13.91%", "volume": "$62,045", "open_interest": "$191", "funding_rate": "-0.0035%"},
    "AVGO": {"leverage": "10x", "price": "$366.62", "change_24h": "-3.41%", "volume": "$61,418", "open_interest": "$39,796", "funding_rate": "0.0042%"},
    "SKHY": {"leverage": "10x", "price": "$163.89", "change_24h": "1.78%", "volume": "$60,672", "open_interest": "$105,189", "funding_rate": "0.0038%"},
    "JTO": {"leverage": "5x", "price": "$0.5957", "change_24h": "8.49%", "volume": "$59,639", "open_interest": "$129,553", "funding_rate": "-0.0002%"},
    "SILVER": {"leverage": "25xISO", "price": "$66.863", "change_24h": "5.72%", "volume": "$56,615", "open_interest": "$32,137", "funding_rate": "0.0024%"},
    "VIRTUAL": {"leverage": "5x", "price": "$0.65237", "change_24h": "14.30%", "volume": "$55,534", "open_interest": "$51,857", "funding_rate": "-0.0009%"},
    "MORPHO": {"leverage": "5x", "price": "$2.2298", "change_24h": "10.23%", "volume": "$52,295", "open_interest": "$48,440", "funding_rate": "0.0002%"},
    "XLM": {"leverage": "5x", "price": "$0.17762", "change_24h": "13.78%", "volume": "$51,206", "open_interest": "$11,220", "funding_rate": "-0.0012%"},
    "XPL": {"leverage": "10x", "price": "$0.08222", "change_24h": "8.24%", "volume": "$44,458", "open_interest": "$55,124", "funding_rate": "0.0000%"},
    "ONDO": {"leverage": "10x", "price": "$0.35045", "change_24h": "8.47%", "volume": "$37,782", "open_interest": "$35,554", "funding_rate": "-0.0012%"},
    "VVV": {"leverage": "5x", "price": "$14.264", "change_24h": "1.83%", "volume": "$31,566", "open_interest": "$129,353", "funding_rate": "0.0097%"},
    "BABA": {"leverage": "10x", "price": "$126.69", "change_24h": "-0.06%", "volume": "$30,483", "open_interest": "$13,857", "funding_rate": "0.0023%"},
    "TAO": {"leverage": "5x", "price": "$209.30", "change_24h": "9.01%", "volume": "$30,360", "open_interest": "$134,929", "funding_rate": "0.0007%"},
    "DOGE": {"leverage": "10x", "price": "$0.076695", "change_24h": "9.55%", "volume": "$28,793", "open_interest": "$15,927", "funding_rate": "0.0000%"},
    "XRP": {"leverage": "15x", "price": "$1.151", "change_24h": "14.64%", "volume": "$28,478", "open_interest": "$55,517", "funding_rate": "0.0000%"},
    "LINK": {"leverage": "10x", "price": "$10.6113", "change_24h": "9.08%", "volume": "$20,106", "open_interest": "$1,592", "funding_rate": "-0.0006%"},
    "TRX": {"leverage": "10x", "price": "$0.33467", "change_24h": "0.50%", "volume": "$16,408", "open_interest": "$19,546", "funding_rate": "-0.0001%"},
    "FET": {"leverage": "5x", "price": "$0.13377", "change_24h": "10.31%", "volume": "$16,088", "open_interest": "$811", "funding_rate": "-0.0010%"},
    "MEGA": {"leverage": "5x", "price": "$0.03525", "change_24h": "10.92%", "volume": "$15,837", "open_interest": "$27,474", "funding_rate": "-0.0025%"},
    "SKR": {"leverage": "3xISO", "price": "$0.007450", "change_24h": "7.43%", "volume": "$15,779", "open_interest": "$11,782", "funding_rate": "0.0000%"},
    "CHIP": {"leverage": "5x", "price": "$0.02782", "change_24h": None, "volume": None, "open_interest": None, "funding_rate": None}
}
