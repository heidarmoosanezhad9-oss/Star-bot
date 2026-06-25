FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# پیش‌فرض: اجرای ربات. روی Railway برای worker/beat/api این رو override کن (پایین README رو ببین)
CMD ["python", "-m", "app.bot.main"]
