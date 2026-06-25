"""FastAPI سبک - فعلاً فقط healthcheck؛ پایه‌ی API برای پنل ادمین وب در فاز ۲"""
from fastapi import FastAPI

from app.api.routers import health

app = FastAPI(title="Telegram Growth Platform API")
app.include_router(health.router)
