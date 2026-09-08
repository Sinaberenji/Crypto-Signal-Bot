import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from signal_engine.generator import SignalGenerator
from telegram.bot import TelegramBot
from api.redis_client import redis_client
from config.settings import settings
import asyncio
import traceback
import sys


async def run_signal_bot():
    generator = SignalGenerator()
    bot = TelegramBot()

    try:
        print("Starting signal scan...")
        signals = await generator.scan_all()

        if not signals:
            print("No signals found")
            await bot.send_message("🔍 هیچ سیگنالی در این بازه یافت نشد.")
            return {"status": "ok", "signals": 0, "message": "No signals found"}

        print(f"Found {len(signals)} raw signals")

        filtered_signals = []
        for signal in signals:
            if await redis_client.check_and_mark(signal):
                filtered_signals.append(signal)
            else:
                print(f"Duplicate signal filtered: {signal.symbol} {signal.signal_type.value}")

        print(f"After deduplication: {len(filtered_signals)} signals")

        if filtered_signals:
            sent = await bot.send_signals_batch(filtered_signals)
            return {"status": "ok", "signals_found": len(signals), "signals_sent": sent}
        else:
            await bot.send_message("🔍 سیگنال‌های جدیدی یافت نشد (همه تکراری بودند).")
            return {"status": "ok", "signals": 0, "message": "All signals were duplicates"}

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"Error: {error_msg}")
        traceback.print_exc()
        await bot.send_error(error_msg)
        return {"status": "error", "message": error_msg}

    finally:
        await generator.close()
        await bot.close()
        await redis_client.close()


def handler(request):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_signal_bot())
        loop.close()
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": str(result).replace("'", '"')
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": f'{{"status": "error", "message": "{str(e)}"}}'
        }


if __name__ == "__main__":
    result = asyncio.run(run_signal_bot())
    print(result)
