"""
Daily WhatsApp alert scheduler.
Runs at 09:00 IST, checks filing deadlines + recon issues.
"""
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.gst import ReconciliationResult
from app.models.gst_return import GSTReturn, ReturnStatus, ReturnType
from app.models.user import User
from app.models.whatsapp import WhatsAppAlertLog
from app.services.whatsapp_client import send_template, send_text

scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")


def _current_period() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year}-{now.month:02d}"


def _days_until_deadline(day_of_month: int) -> int:
    now = datetime.now(timezone.utc)
    target = now.replace(day=day_of_month, hour=0, minute=0, second=0, microsecond=0)
    if target < now:
        # next month
        if now.month == 12:
            target = target.replace(year=now.year + 1, month=1)
        else:
            target = target.replace(month=now.month + 1)
    return (target - now).days


async def run_daily_alerts() -> None:
    gstr1_days = _days_until_deadline(11)
    gstr3b_days = _days_until_deadline(20)

    async with AsyncSessionLocal() as db:
        users = await db.execute(
            select(User).where(
                User.whatsapp_verified == True,
                User.whatsapp_alerts_enabled == True,
            )
        )
        for user in users.scalars():
            prefs = user.whatsapp_alert_prefs or {"deadlines": True, "recon": True, "itc_expiry": True}
            period = _current_period()

            if prefs.get("deadlines"):
                await _check_deadlines(user, period, gstr1_days, gstr3b_days, db)

            if prefs.get("recon"):
                await _check_recon(user, period, db)

            await db.commit()


async def _check_deadlines(
    user: User, period: str, gstr1_days: int, gstr3b_days: int, db
) -> None:
    from sqlalchemy import select
    from app.models.business import Business

    business = await db.scalar(select(Business).where(Business.user_id == user.id))
    if not business:
        return

    checks = [
        (ReturnType.GSTR1, "GSTR-1", 11, gstr1_days),
        (ReturnType.GSTR3B, "GSTR-3B", 20, gstr3b_days),
    ]

    for return_type, label, due_day, days_left in checks:
        if days_left > 3:
            continue

        ret = await db.scalar(
            select(GSTReturn).where(
                GSTReturn.business_id == business.id,
                GSTReturn.period == period,
                GSTReturn.return_type == return_type,
            )
        )
        if ret and ret.status == ReturnStatus.FILED:
            continue

        alert_key = f"deadline_{return_type.value}_{period}"
        already_sent = await db.scalar(
            select(WhatsAppAlertLog).where(
                WhatsAppAlertLog.user_id == user.id,
                WhatsAppAlertLog.template_name == alert_key,
            )
        )
        if already_sent:
            continue

        due_date = f"{period}-{due_day:02d}"
        msg = (
            f"⏰ *Filing Reminder*\n"
            f"Your *{label}* for {period} is due by {due_date}.\n"
            f"{'Status: Not yet filed.' if not ret else f'Status: {ret.status.value.replace(chr(95), chr(32)).title()}'}\n"
            f"Open the dashboard to file: bemyca.in/returns"
        )
        await send_text(user.whatsapp_number, msg)
        db.add(WhatsAppAlertLog(
            user_id=user.id,
            template_name=alert_key,
            wa_number=user.whatsapp_number,
        ))


async def _check_recon(user: User, period: str, db) -> None:
    from app.models.business import Business
    from app.models.gst import ReconciliationResult

    business = await db.scalar(
        select(Business).where(Business.user_id == user.id)
    )
    if not business:
        return

    issues = await db.scalar(
        select(func.count()).where(
            ReconciliationResult.business_id == business.id,
            ReconciliationResult.period == period,
            ReconciliationResult.status.in_(["missing_in_2b", "amount_mismatch"]),
        )
    )
    if not issues:
        return

    alert_key = f"recon_issues_{period}"
    already_sent = await db.scalar(
        select(WhatsAppAlertLog).where(
            WhatsAppAlertLog.user_id == user.id,
            WhatsAppAlertLog.template_name == alert_key,
        )
    )
    if already_sent:
        return

    msg = (
        f"⚠️ *Reconciliation Alert*\n"
        f"*{issues}* invoice(s) have mismatches in GSTR-2B for {period}.\n"
        f"Unresolved mismatches can block ITC. Review at bemyca.in/reconciliation"
    )
    await send_text(user.whatsapp_number, msg)
    db.add(WhatsAppAlertLog(
        user_id=user.id,
        template_name=alert_key,
        wa_number=user.whatsapp_number,
    ))


def start_scheduler() -> None:
    scheduler.add_job(
        run_daily_alerts,
        CronTrigger(hour=9, minute=0, timezone="Asia/Kolkata"),
        id="daily_alerts",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
