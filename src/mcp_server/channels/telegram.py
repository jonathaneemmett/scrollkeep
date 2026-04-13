from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from mcp_server.channels import Channel
from mcp_server.config import get_settings

log = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT = 4096


class TelegramChannel(Channel):

    @property
    def name(self) -> str:
        return "telegram"

    def __init__(self) -> None:
        super().__init__()
        settings = get_settings()

        token = settings.telegram_bot_token
        if not token:
            raise ValueError(
                "Telegram bot token is required"
            )
        self._token = token.get_secret_value()

        self._allowed_chat_ids: set[int] = set(
            settings.telegram_allowed_chat_ids or []
        )
        self._app: Application | None = None
        self._stop_event = asyncio.Event()

    def _is_allowed(self, chat_id: int) -> bool:
        if not self._allowed_chat_ids:
            return True
        return chat_id in self._allowed_chat_ids

    async def _handle_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        chat = update.effective_chat
        if chat and self._is_allowed(chat.id):
            await update.message.reply_text(
                "Scrollkeep ready. Send me a message."
            )

    async def _handle_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        chat = update.effective_chat
        msg = update.message
        if not chat or not msg or not msg.text:
            return

        if not self._is_allowed(chat.id):
            log.warning(
                "Rejected message from unauthorized chat %s",
                chat.id,
            )
            return

        await chat.send_action("typing")

        try:
            response = await self.handle_message(
                str(chat.id), msg.text
            )
        except Exception:
            log.exception("Error handling message from chat %s", chat.id)
            await msg.reply_text("An error occurred. Please try again.")
            return

        for i in range(
            0, len(response), TELEGRAM_MESSAGE_LIMIT
        ):
            end = i + TELEGRAM_MESSAGE_LIMIT
            await msg.reply_text(response[i:end])

    async def start(self) -> None:
        self._app = (
            Application.builder()
            .token(self._token)
            .build()
        )
        self._app.add_handler(
            CommandHandler("start", self._handle_start)
        )
        self._app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._handle_message,
            )
        )

        await self.setup()
        await self._app.initialize()
        await self._app.start()

        settings = get_settings()
        webhook_url = settings.telegram_webhook_url
        updater = self._app.updater

        if webhook_url:
            log.info(
                "Starting Telegram channel (webhook: %s)",
                webhook_url,
            )
            await updater.start_webhook(
                listen="0.0.0.0",
                port=settings.telegram_webhook_port,
                url_path="/telegram",
                webhook_url=f"{webhook_url}/telegram",
            )
        else:
            log.info("Starting Telegram channel (polling)")
            await updater.start_polling()

        await self._stop_event.wait()

    async def stop(self) -> None:
        if self._stop_event.is_set():
            return
        self._stop_event.set()
        if self._app:
            if self._app.updater:
                await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
