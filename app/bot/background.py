"""
هلپر اجرای کارهای پشت‌صحنه (مثل ارسال بردکاست) بدون نیاز به Celery.
نکته‌ی مهم: اگه فقط asyncio.create_task(...) صدا بزنیم و خروجیش رو جایی نگه نداریم،
پایتون ممکنه تسک رو قبل از تمومش شدن garbage-collect کنه (چون event loop فقط
weak reference به تسک‌ها نگه می‌داره). برای همین باید یه reference قوی نگه داریم.
"""
import asyncio

_background_tasks: set[asyncio.Task] = set()


def fire_and_forget(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task
