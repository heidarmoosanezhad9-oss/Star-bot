# Telegram Growth Platform — فاز ۱ (بک‌اند + ربات)

پلتفرم رشد تلگرام با اقتصاد الماس، جوین کانال برای کسب الماس، سفارش خودکار ممبر و تبلیغ کانال،
رفرال، میشن/اچیومنت، VIP، Trust Score، آنتی‌فرود پایه، گیفت‌کد، تیکت پشتیبانی و پنل مدیریت از داخل ربات.

موارد حذف‌شده طبق درخواست: استارز، ری‌اکشن، بازدید، رأی‌گیری، مارکت‌پلیس کامل (فروشنده/اسکرو/کمیسیون/حراج اسپانسر).

## ⚠️ یک نکته مهم قبل از اجرا
این نوع ربات (تبادل عضو/جوین در ازای امتیاز) رشد مصنوعی ایجاد می‌کنه و ممکنه با قوانین تلگرام درباره
اسپم/تعامل غیرواقعی در تضاد باشه. مسئولیت رعایت قوانین تلگرام و استفاده‌ی درست با خودته.

---

## ساختار پروژه

```
app/
  config.py          تنظیمات از .env
  database.py        اتصال async به PostgreSQL
  redis_client.py     اتصال Redis
  seed.py            دیتای اولیه (VIP/میشن/اچیومنت)
  models/            مدل‌های SQLAlchemy
  services/          منطق اصلی (کیف پول، سفارش، رفرال، VIP، تراست، آنتی‌فرود...)
  bot/               ربات Aiogram 3.x (هندلرها، کیبوردها، میدلورها)
  tasks/             Celery (ریفیل پشتیبان، تکمیل خودکار تبلیغ، بردکاست)
  api/               FastAPI سبک (فعلاً فقط healthcheck)
migrations/          اسکلت Alembic (اختیاری برای آینده)
docker-compose.yml   اجرای کامل لوکال
Dockerfile           ایمیج مشترک همه سرویس‌ها
```

## پیش‌نیازها
- یک بات تلگرام از @BotFather (توکن)
- آیدی عددی خودت به‌عنوان اونر (از @userinfobot بگیر)
- یک کانال تلگرامی که **ربات توش ادمین باشه** (همون کانال جمع‌آوری سفارش‌ها)

## متغیرهای محیطی (`.env`)
از `.env.example` کپی کن و مقادیر فیک رو با مقادیر واقعی جابه‌جا کن:
- `BOT_TOKEN` , `OWNER_ID` , `COLLECTOR_CHANNEL_ID`
- `DATABASE_URL` (روی Railway از پلاگین Postgres می‌گیری)
- `REDIS_URL` / `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` (روی Railway از پلاگین Redis می‌گیری - هر سه می‌تونن همون یک Redis باشن با دیتابیس‌های 0/1/2)

---

## 🚀 دیپلوی روی Railway (با Git)

1. یه ریپازیتوری گیت‌هاب بساز و کل پوشه‌ی پروژه رو پوش کن.
2. روی [railway.app](https://railway.app) یک پروژه‌ی جدید بساز و ریپازیتوری رو وصل کن.
3. از «New» → **Database → PostgreSQL** و **Database → Redis** اضافه کن. ریلوی خودش `DATABASE_URL` و `REDIS_URL` می‌سازه.
4. روی همون پروژه، **۳ سرویس جدا** از همین ریپازیتوری بساز (هر کدوم Dockerfile یکسان، فقط Start Command فرق داره):
   - **bot** → Start Command: `python -m app.bot.main`
   - **worker** → Start Command: `celery -A app.tasks.celery_app worker --loglevel=info`
   - **beat** → Start Command: `celery -A app.tasks.celery_app beat --loglevel=info`
   - (اختیاری) **api** → Start Command: `uvicorn app.api.main:app --host 0.0.0.0 --port 8000`
5. روی هر ۳-۴ سرویس، متغیرهای محیطی بالا رو ست کن (می‌تونی Postgres/Redis رو به همه‌شون Reference بدی تا یکی باشه).
6. Deploy بزن. توی سرویس `bot` لاگ `Bot starting polling...` باید بیاد یعنی آنلاینه.

> نکته: چون از Polling استفاده شده (نه Webhook)، نیازی به دامنه/HTTPS برای خود ربات نیست؛ فقط دیتابیس و Redis باید در دسترس باشن.

## 🖥 اجرای لوکال با Docker (اگه به PC دسترسی پیدا کردی)
```bash
cp .env.example .env   # و مقادیرش رو واقعی کن
docker compose up --build
```

---

## ✅ تست end-to-end سفارش ممبر
1. ربات رو به یک کانال تستی، **ادمین** کن با دسترسی «دعوت کاربران» و «مدیریت چت».
2. توی PV ربات: `🛒 ثبت سفارش` → `👥 سفارش ممبر` → یوزرنیم کانال رو بفرست → تعداد رو بفرست → تایید کن.
3. سفارش خودکار تایید و توی کانال جمع‌آوری (`COLLECTOR_CHANNEL_ID`) پست میشه.
4. با یک اکانت دیگه روی دکمه‌ی پست کلیک کن (باید قبلش عضو کانال هدف شده باشه) → الماس می‌گیره و پیشرفت سفارش بالا میره.
5. وقتی اون یوزر از کانال هدف لفت بده، ریفیل خودکار فعال میشه (نیاز به بازبینی پیشرفت داره).

## دستورات ادمین (فقط برای `OWNER_ID`)
- `/setconfig کلید مقدار` — مثلا `/setconfig join_reward 15`
- `/ban آیدی_عددی [دلیل]` و `/unban آیدی_عددی`
- `/adjustwallet آیدی_عددی مقدار` (منفی = برداشت)
- دکمه‌ی `🛠 پنل مدیریت` → آمار کلی، بردکاست، ساخت گیفت‌کد، تنظیمات

---

## 🗺 نقشه فاز ۲ (هنوز ساخته نشده)
- پنل ادمین وب (React + TailwindCSS) روی همین FastAPI
- Automation Builder بدون‌کد (IF/THEN)
- Dynamic Menu Builder بدون‌کد
- Lottery System
- Event System با ضریب پاداش (مدل `Event` ساخته شده ولی هنوز در reward_service اعمال نمیشه)
- Alembic migration واقعی به‌جای `init_models()`
