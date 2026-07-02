-- این رو یک‌بار روی دیتابیس Postgres پروژه (Railway) اجرا کن
-- بدون این، ربات موقع استفاده از فیچرهای جدید خطا میده چون ستون‌ها وجود ندارن

ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS warnings_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(32) NULL;
