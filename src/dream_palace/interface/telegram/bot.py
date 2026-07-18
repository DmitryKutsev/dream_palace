"""python-telegram-bot application: one bot carrying all Dream Palace roles."""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from dream_palace.service.dream_service import DreamService
from dream_palace.service.telegram_client import TelegramClient
from dream_palace.shared.domain import ApprovalStatus, IncomingMessage


def build_application(
    client: TelegramClient, service: DreamService, admins: frozenset[int], webapp_url: str
) -> Application:
    async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        message, user = update.effective_message, update.effective_user
        if not message or not user:
            return
        if webapp_url:
            await client.send_webapp_button(
                user.id,
                "Welcome to Dream Palace. Open the app to browse and analyse your dreams, "
                "or just send me a dream as text, voice, or photo.",
                "Open Dream Palace",
                webapp_url,
            )
        else:
            await message.reply_text("Welcome to Dream Palace. Send me a dream to record it.")

    async def register(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        message, user = update.effective_message, update.effective_user
        if not message or not user:
            return
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) != 2 or "@" not in parts[1]:
            await message.reply_text("Use /register you@example.com")
            return
        await service.register(user.id, user.username or "", parts[1])
        await message.reply_text("Registration submitted for administrator approval.")

    def set_status(status: ApprovalStatus, command: str):
        async def handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
            message, user = update.effective_message, update.effective_user
            if not message or not user:
                return
            if user.id not in admins:
                await message.reply_text("Administrator access required.")
                return
            parts = (message.text or "").split(maxsplit=1)
            if len(parts) != 2 or not parts[1].isdigit():
                await message.reply_text(f"Use /{command} TELEGRAM_ID")
                return
            target_id = int(parts[1])
            await service.set_approval(target_id, status)
            await message.reply_text(f"User {target_id} is now {status.value}.")

        return handler

    async def receive(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        message, user = update.effective_message, update.effective_user
        if not message or not user:
            return
        media_type, file_id = None, None
        if message.voice:
            media_type, file_id = "voice", message.voice.file_id
        elif message.video:
            media_type, file_id = "video", message.video.file_id
        elif message.video_note:
            media_type, file_id = "video", message.video_note.file_id
        elif message.photo:
            media_type, file_id = "image", message.photo[-1].file_id
        media = await client.download_file(file_id) if file_id else None
        incoming = IncomingMessage(user.id, message.text or message.caption, media_type, media)
        try:
            _, text = await service.save_dream(incoming)
        except PermissionError:
            await message.reply_text("Access is pending. Register and wait for approval.")
            return
        if text:
            await message.reply_text(f"Dream recorded:\n\n{text}"[:4000])
        else:
            await message.reply_text("Dream recorded, but I could not transcribe the media.")

    application = ApplicationBuilder().bot(client.bot).updater(None).build()
    approve = set_status(ApprovalStatus.APPROVED, "approve")
    reject = set_status(ApprovalStatus.REJECTED, "reject")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("register", register))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("reject", reject))
    application.add_handler(MessageHandler(~filters.COMMAND, receive))
    return application
