"""A LINE webhook backed by a Tauon agent.

Install the example dependencies and run locally:

    uv run --with line-bot-sdk --with flask python examples/line_bot.py

Expose port 8000 with a public HTTPS tunnel, then use its ``/callback`` URL
as the webhook URL in the LINE Developers Console.
"""

from __future__ import annotations

import asyncio
import os

from flask import Flask, abort, request
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from tauon import define_agent, run_agent, use_model

MAX_INPUT_CHARS = 4_000
MAX_REPLY_CHARS = 5_000


@define_agent
def LineBotAgent() -> str:
    """Configure the agent used for LINE text messages."""
    use_model(os.getenv("TAUON_MODEL", "gpt-4.1-mini"))
    return (
        "You are a helpful LINE chat assistant. Keep replies concise and plain text. "
        "Do not claim to have performed actions you cannot perform."
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _run_agent(message: str) -> str:
    # Flask's route is synchronous, while Tauon's agent API is async.
    return asyncio.run(run_agent(LineBotAgent, message, timeout=30))


def create_app() -> Flask:
    """Create the Flask app and configure LINE signature/API access."""
    parser = WebhookParser(_required_env("LINE_CHANNEL_SECRET"))
    configuration = Configuration(access_token=_required_env("LINE_CHANNEL_ACCESS_TOKEN"))
    app = Flask(__name__)

    @app.post("/callback")
    def callback() -> tuple[str, int] | str:
        # Read the raw body before parsing; LINE signs this exact content.
        body = request.get_data(as_text=True)
        signature = request.headers.get("X-Line-Signature", "")
        try:
            events = parser.parse(body, signature)
        except InvalidSignatureError:
            abort(400)
        except (KeyError, TypeError, UnicodeDecodeError, ValueError):
            abort(400)

        with ApiClient(configuration) as api_client:
            line_api = MessagingApi(api_client)
            for event in events:
                if not isinstance(event, MessageEvent):
                    continue
                if not isinstance(event.message, TextMessageContent):
                    continue
                if not event.reply_token:
                    continue

                user_text = event.message.text.strip()[:MAX_INPUT_CHARS]
                try:
                    reply = _run_agent(user_text) or "I couldn't think of a reply."
                except Exception:
                    app.logger.exception("Agent failed while handling a LINE message")
                    reply = "Sorry, I couldn't process that message right now."

                line_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=reply[:MAX_REPLY_CHARS])],
                    )
                )

        return "OK"

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
