# Crypto Signal Bot

سیستم تحلیل تکنیکال و سیگنال‌دهی خودکار کریپتو با استراتژی محافظه‌کارانه (ریسک کم) - روی Vercel + GitHub Actions

## ویژگی‌ها

- **تحلیل تکنیکال کامل**: EMA 50/200، RSI، MACD، حمایت/مقاومت، حجم
- **استراتژی محافظه‌کارانه**: سیگنال فقط وقتی همه شرایط هم‌زمان برقرار باشند
- **فیلتر تکرار**: Upstash Redis برای جلوگیری از سیگنال‌های تکراری
- **نوتیفیکیشن تلگرام**: ارسال سیگنال با جزئیات کامل (ورود، حد ضرر، حد سود، R:R)
- **Serverless**: اجرا روی Vercel (بدون سرور مداوم)
- **زمان‌بندی ساعتی**: GitHub Actions هر ساعت یک بار اجرا می‌شود
- **رایگان**: تمام سرویس‌ها لایه رایگان دارند

## استراتژی سیگنال‌دهی

سیگنال **فقط** وقتی صادر می‌شود که **همه** این شرایط برقرار باشند:

| شرط | توضیح |
|------|-------|
| **روند ۴h** | EMA 50 > EMA 200 (لاغ) یا EMA 50 < EMA 200 (شرت) |
| **RSI** | در ناحیه اشباع فروش/خرید + برگشت (RSI < 30 و بالا رفتن، یا RSI > 70 و پایین آمدن) |
| **MACD** | کراس تأییدکننده (MACD خط سیگنال رو می‌شکنه + هیستوگرم تقویت میشه) |
| **حمایت/مقاومت** | نزدیکی به سطح معتبر (حداقل ۲ لمسی، فاصله < ۰.۵٪) |
| **حجم** | حجم فعلی > ۱.۲x میانگین ۲۰ روزه |
| **ریسک/ریوارد** | حداقل ۱:۲ |

## معماری

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  GitHub Actions │────▶│  Vercel Function │────▶│  Telegram Bot   │
│  (هر ساعت)      │     │  (Python 3.11)   │     │  (نوتیفیکیشن)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐     ┌─────────────────┐
                       │  Coinex API      │     │  Upstash Redis  │
                       │  (داده‌های-OHLCV) │     │  (Anti-duplicate)│
                       └──────────────────┘     └─────────────────┘
```

## پیش‌نیازها

- اکانت GitHub
- اکانت Vercel (رایگان)
- اکانت Upstash (رایگان - ۱۰ هزار درخواست/روز)
- بات تلگرام (از طریق @BotFather)

---

## راهنمای ست‌آپ قدم‌به‌قدم

### ۱. ساخت بات تلگرام و دریافت توکن

1. در تلگرام به **@BotFather** پیام دهید
2. دستور `/newbot` را بفرستید
3. نام بات را وارد کنید (مثال: `My Crypto Signals`)
4. یوزرنیم بات را وارد کنید (باید با `bot` تمام شود، مثل `mycryptosignals_bot`)
5. **توکن را کپی کنید** - فرمت: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`

### ۲. پیدا کردن Chat ID

**روش ۱ (کاربر عادی):**
1. به **@userinfobot** پیام دهید
2. `Id` نمایش داده شده را کپی کنید (مثال: `123456789`)

**روش ۲ (گروه/کانال):**
1. بات را به گروه/کانال اضافه کنید
2. به **@RawDataBot** پیام دهید
3. در پیام‌های دریافتی `chat.id` را پیدا کنید (برای گروه منفی است، مثل `-1001234567890`)

### ۳. ست‌آپ Upstash Redis (رایگان)

1. به [upstash.com](https://upstash.com) بروید و ثبت‌نام کنید
2. روی **Create Database** کلیک کنید
3. نام دیتابیس: `crypto-signals`
4. Region: 가까운 지역 انتخاب کنید (مثل `us-east-1`)
5. نوع: **Redis** (نه Vector)
6. پس از ایجاد، به تب **REST API** بروید
7. **UPSTASH_REDIS_REST_URL** و **UPSTASH_REDIS_REST_TOKEN** را کپی کنید

### ۴. Fork و کلون ریپازیتوری

```bash
git clone https://github.com/YOUR_USERNAME/crypto-signal-bot.git
cd crypto-signal-bot
```

### ۵. تنظیم متغیرهای محیطی در GitHub

1. در GitHub به **Settings > Secrets and variables > Actions** بروید
2. **New repository secret** برای هر یک از موارد زیر:

| نام | مقدار |
|-----|-------|
| `TELEGRAM_BOT_TOKEN` | توکن از قدم ۱ |
| `TELEGRAM_CHAT_ID` | Chat ID از قدم ۲ |
| `UPSTASH_REDIS_REST_URL` | URL از قدم ۳ |
| `UPSTASH_REDIS_REST_TOKEN` | Token از قدم ۳ |

### ۶. دیپلوی روی Vercel

**روش ۱: از طریق Vercel Dashboard (پیشنهادی)**
1. به [vercel.com](https://vercel.com) بروید و با GitHub لاگین کنید
2. **Add New Project** > Import Git Repository
3. ریپازیتوری `crypto-signal-bot` را انتخاب کنید
4. **Framework Preset**: Other
5. **Root Directory**: `crypto-signal-bot` (اگر در ساب‌فولدر است)
6. Environment Variables را اضافه کنید (همان ۴ متغیر بالا)
7. **Deploy** را بزنید

**روش ۲: از طریق CLI**
```bash
cd crypto-signal-bot
npm install -g vercel
vercel login
vercel --prod
```
متغیرهای محیطی را در داشبورد Vercel > Project > Settings > Environment Variables اضافه کنید.

### ۷. فعال‌سازی GitHub Actions

1. در ریپازیتوری GitHub به تب **Actions** بروید
2. اگر disabled است، **Enable workflows** را بزنید
3. Workflow `Hourly Crypto Signal Scan` به صورت خودکار هر ساعت اجرا می‌شود
4. برای تست دستی: **Run workflow** > **Run workflow**

### ۸. تست اولیه

در GitHub Actions > Workflow > **Run workflow** بزنید. در تلگرام باید پیام استارت‌آپ دریافت کنید:
```
🤖 بات سیگنال کریپتو فعال شد
📊 مانیتورینگ: 10 جفت ارز
...
```

سپس در لاگ‌های Action نتیجه اسکن را ببینید.

---

## تنظیمات سفارشی‌سازی

فایل `config/settings.py` را ویرایش کنید:

```python
TRADING_PAIRS = ["BTCUSDT", "ETHUSDT", ...]  # جفت‌های مورد نظر
MAX_SIGNALS_PER_RUN = 3                       # حداکثر سیگنال در اجرا
RISK_REWARD_MIN = 2.0                         # حداقل R:R
SIGNAL_COOLDOWN_HOURS = 4                     # کول‌داون تکرار سیگنال
TIMEFRAME_TREND = "4hour"                     # تایم‌فریم روند
TIMEFRAME_ENTRY = "1hour"                     # تایم‌فریم ورود
```

### تغییر نمادها
برای Top 20 یا نمادهای خاص، لیست `TRADING_PAIRS` را تغییر دهید. نام‌ها باید دقیقاً با فرمت Coinex باشند (مثال: `BTCUSDT`، `ETHUSDT`).

---

## ساختار پروژه

```
crypto-signal-bot/
├── api/
│   ├── index.py           # Vercel entry point
│   ├── coinex.py          # Coinex API client
│   └── redis_client.py    # Upstash Redis client
├── analyzer/
│   ├── technical.py       # اندیکاتورها (EMA, RSI, MACD, ATR, SMA)
│   └── market_structure.py# روند، حمایت/مقاومت، ساختار بازار
├── signal/
│   └── generator.py       # موتور سیگنال‌دهی
├── telegram/
│   └── bot.py             # بات تلگرام
├── config/
│   └── settings.py        # تنظیمات مرکزی
├── tests/
│   └── test_indicators.py # تست‌های واحد
├── .github/workflows/
│   └── hourly-signal.yml  # GitHub Actions
├── vercel.json            # تنظیمات Vercel
├── requirements.txt
├── .env.example
└── README.md
```

---

## مانیتورینگ و عیب‌یابی

### لاگ‌های GitHub Actions
- تب **Actions** >Workflow run > job > step `Run signal scanner`

### لاگ‌های Vercel
- Dashboard > Project > Functions > View Logs

### تست لوکال
```bash
cd crypto-signal-bot
cp .env.example .env
# .env را پر کنید
pip install -r requirements.txt
python api/index.py
```

### چک‌لیست خطاهای رایج

| خطا | دلیل | راه‌حل |
|-----|------|--------|
| `401 Unauthorized` (Telegram) | توکن اشتباه | توکن را در GitHub Secrets چک کنید |
| `Chat not found` | Chat ID اشتباه | Chat ID را با @userinfobot تایید کنید |
| `Upstash connection failed` | URL/Token اشتباه | Credentials را در Upstash کپی کنید |
| `No signals found` | شرایط برقرار نشده | طبیعی است - صبر کنید |
| `Vercel function timeout` | زمان‌بر بودن تحلیل | `maxDuration` در vercel.json را افزایش دهید |

---

## امنیت

- **هیچ API Key خصوصی Coinex لازم نیست** (داده‌های عمومی)
- توکن‌ها فقط در GitHub Secrets و Vercel Env Vars ذخیره می‌شوند
- Upstash فقط برای ددوپلیکیشن سیگنال استفاده می‌شود
- کد در ریپازیتوری عمومی امن است (بدون секрет)

---

## مجوز

MIT License - آزاد برای استفاده شخصی و تجاری

---

## پشتیبانی

برای گزارش باگ یا پیشنهاد فیچر، Issue در GitHub باز کنید.