"""Thin wrapper over python-telegram-bot's Bot for outbound Telegram calls."""

from __future__ import annotations

import logging

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramClient:
    """Outbound Telegram operations used by services and handlers."""

    def __init__(self, token: str) -> None:
        self.bot = Bot(token)

    async def send_message(self, chat_id: int, text: str) -> None:
        await self.bot.send_message(chat_id=chat_id, text=text)

    async def send_webapp_button(self, chat_id: int, text: str, label: str, url: str) -> None:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(label, web_app=WebAppInfo(url=url))]]
        )
        await self.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)

    async def notify_all(self, chat_ids: frozenset[int], text: str) -> None:
        for chat_id in chat_ids:
            try:
                await self.bot.send_message(chat_id=chat_id, text=text)
            except TelegramError:  # one unreachable admin must not fail the operation
                logger.warning("could not notify admin %s", chat_id)

    async def download_file(self, file_id: str) -> bytes:
        file = await self.bot.get_file(file_id)
        return bytes(await file.download_as_bytearray())
