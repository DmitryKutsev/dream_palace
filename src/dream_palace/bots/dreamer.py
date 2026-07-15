import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import Message

from dream_palace.agents import Orchestrator
from dream_palace.config import get_settings
from dream_palace.domain import IncomingMessage
from dream_palace.storage import FirebaseDreamStore


async def main() -> None:
    settings = get_settings()
    bot = Bot(settings.dreamer_bot_token)
    store = FirebaseDreamStore(settings.google_cloud_project, settings.firebase_storage_bucket)
    orchestrator = Orchestrator(store)
    dispatcher = Dispatcher()

    @dispatcher.message()
    async def receive(message: Message) -> None:
        if not message.from_user:
            return
        media_type = "voice" if message.voice else "image" if message.photo else None
        file_id = (
            message.voice.file_id
            if message.voice
            else message.photo[-1].file_id
            if message.photo
            else None
        )
        media = None
        if file_id:
            target = await bot.download(file_id)
            media = target.read() if target else None
        incoming = IncomingMessage(
            message.from_user.id, message.text or message.caption, media_type, media
        )
        try:
            result = orchestrator.handle(incoming)
            await message.answer(f"Handled as {result['intent']}.")
        except PermissionError:
            await message.answer("Access is pending. Register with The Dreamer Clerk first.")

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
