

### ۱. به‌روزرسانی سرور و نصب ابزارهای مورد نیاز

این دستور را کپی کرده و در ترمینال بزنید:

```bash
sudo apt update && sudo apt install git python3 python3-pip python3-venv screen nano -y

```

---

### ۲. کلون کردن مخزن جدید و ورود به پوشه پروژه

```bash
git clone https://github.com/drsimon6/Phoenix-Trade-Multi-Wallet-Tracker-.git
cd Phoenix-Trade-Multi-Wallet-Tracker-

```

---

### ۳. ساخت محیط مجازی (Virtual Environment) و نصب پکیج‌ها

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

```

---

### ۴. ساخت فایل تنظیمات (`config.py`)

دستور زیر را بزنید تا ادیتور `nano` باز شود:

```bash
nano config.py

```

### ۵. اجرای ربات در یک صفحه مستقل (Screen)

یک صفحه جدید به اسم `phoenix-bot` باز کنید و ربات را اجرا کنید:

```bash
screen -S phoenix-bot
source .venv/bin/activate
```

```
python main.py

```

---

### ۶. خروج امن از Screen (بدون خاموش شدن ربات)

حالا برای اینکه ربات ۲۴ ساعته کار کند و بتوانید ترمینال را ببندید:

* دکمه‌های **`Ctrl + A`** را همزمان بگیرید و سپس دکمه **`D`** را بزنید.

---

📌 **دستورات کاربردی برای آینده:**

* **بازگشت به صفحه ربات:** `screen -r phoenix-bot`
* **مشاهده لیست صفحات فعال:** `screen -ls`
