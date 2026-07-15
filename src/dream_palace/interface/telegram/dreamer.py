from aiogram import Bot, Dispatcher
from aiogram.types import Message

from dream_palace.agents import Orchestrator
from dream_palace.shared.domain import IncomingMessage
from dream_palace.tools import DreamStore


def build_dispatcher(bot: Bot, store: DreamStore) -> Dispatcher:
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

    return dispatcher
