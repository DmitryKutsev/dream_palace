import asyncio

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from dream_palace.config import get_settings
from dream_palace.storage import FirebaseDreamStore


async def main() -> None:
    settings = get_settings()
    store = FirebaseDreamStore(settings.google_cloud_project, settings.firebase_storage_bucket)
    dispatcher = Dispatcher()

    @dispatcher.message(Command("register"))
    async def register(message: Message) -> None:
        parts = (message.text or "").split(maxsplit=1)
        if not message.from_user or len(parts) != 2 or "@" not in parts[1]:
            await message.answer("Use /register you@example.com")
            return
        store.register(message.from_user.id, message.from_user.username or "", parts[1])
        await message.answer("Registration submitted for administrator approval.")

    await dispatcher.start_polling(Bot(settings.clerk_bot_token))


if __name__ == "__main__":
    asyncio.run(main())
