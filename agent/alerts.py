"""Alert delivery. Telegram when configured, otherwise the console. The disclaimer is added HERE, by code, never by the LLM."""
import os

import requests

DISCLAIMER = "Educational tool, not financial advice. Trading carries a risk of loss."


def send_alert(text: str) -> dict:
    full = f"{text}\n\n{DISCLAIMER}"
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    note = None
    if token and chat:
        try:
            r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                              json={"chat_id": chat, "text": full}, timeout=15)
            if r.ok:
                return {"sent": True, "channel": "telegram"}
            note = f"telegram HTTP {r.status_code}"
        except requests.RequestException as e:
            note = str(e).replace(token, "***")                      # never leak the bot token into logs
    print("\n" + "-" * 60 + "\n" + full + "\n" + "-" * 60)
    return {"sent": True, "channel": "console", **({"note": f"telegram failed: {note}"} if note else {})}
