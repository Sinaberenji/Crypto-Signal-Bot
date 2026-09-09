import httpx
import asyncio
from typing import List, Optional
from config.settings import settings
from signal_engine.generator import TradeSignal, SignalType, SignalQuality


class TelegramBot:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        if not self.token or not self.chat_id:
            print("Telegram credentials not configured")
            return False

        # Telegram limit is 4096 chars
        if len(text) > 4000:
            text = text[:3950] + "\n\n... <i>(truncated)</i>"

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json().get("ok", False)
        except Exception as e:
            print(f"Telegram send error: {e}")
            # Try without parse_mode if HTML fails
            if parse_mode == "HTML":
                payload.pop("parse_mode", None)
                try:
                    response = await self.client.post(url, json=payload)
                    response.raise_for_status()
                    return response.json().get("ok", False)
                except Exception as e2:
                    print(f"Telegram send error (no parse_mode): {e2}")
            return False

    async def send_signal(self, signal: TradeSignal) -> bool:
        emoji = "🟢" if signal.signal_type == SignalType.LONG else "🔴"
        quality_emoji = {
            SignalQuality.STRONG: "💎",
            SignalQuality.MODERATE: "⭐",
            SignalQuality.WEAK: "⚠️"
        }.get(signal.quality, "")

        direction = "LONG 📈" if signal.signal_type == SignalType.LONG else "SHORT 📉"

        text = (
            f"{emoji} <b>سیگنال {direction}</b> {quality_emoji}\n\n"
            f"💎 <b>نماد:</b> {signal.symbol}\n"
            f"💰 <b>قیمت ورود:</b> {signal.entry_price:.4f}\n"
            f"🛑 <b>حد ضرر:</b> {signal.stop_loss:.4f}\n"
            f"🎯 <b>حد سود:</b> {signal.take_profit:.4f}\n"
            f"⚖️ <b>ریسک/ریوارد:</b> 1:{signal.risk_reward:.2f}\n"
            f"📊 <b>کیفیت:</b> {signal.quality.value}\n\n"
            f"📝 <b>تحلیل:</b>\n{signal.reason}\n\n"
            f"⏰ {self._format_time(signal.timestamp)}"
        )
        return await self.send_message(text)

    async def send_signals_batch(self, signals: List[TradeSignal]) -> int:
        if not signals:
            await self.send_message("🔍 هیچ سیگنالی در این بازه یافت نشد.")
            return 0

        sent = 0
        for signal in signals:
            if await self.send_signal(signal):
                sent += 1
            await asyncio.sleep(0.5)

        summary = (
            f"\n📋 <b>خلاصه اجرا:</b> {sent}/{len(signals)} سیگنال ارسال شد\n"
            f"🟢 لاغ: {sum(1 for s in signals if s.signal_type == SignalType.LONG)}\n"
            f"🔴 شرت: {sum(1 for s in signals if s.signal_type == SignalType.SHORT)}"
        )
        await self.send_message(summary)
        return sent

    async def send_startup_message(self) -> bool:
        text = (
            "🤖 <b>بات سیگنال کریپتو فعال شد</b>\n\n"
            f"📊 مانیتورینگ: {len(settings.TRADING_PAIRS)} جفت ارز\n"
            f"⏰ تایم‌فریم روند: {settings.TIMEFRAME_TREND}\n"
            f"⏰ تایم‌فریم ورود: {settings.TIMEFRAME_ENTRY}\n"
            f"🎯 حداکثر سیگنال در اجرا: {settings.MAX_SIGNALS_PER_RUN}\n"
            f"⚖️ حداقل R:R: 1:{settings.RISK_REWARD_MIN}\n\n"
            "✅ سیستم به‌روزرسانی‌های ساعتی آغاز شد"
        )
        return await self.send_message(text)

    async def send_error(self, error: str) -> bool:
        text = f"❌ <b>خطا در سیگنال‌دهی:</b>\n<code>{error}</code>"
        return await self.send_message(text)

    @staticmethod
    def _format_time(timestamp: int) -> str:
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    async def close(self):
        await self.client.aclose()