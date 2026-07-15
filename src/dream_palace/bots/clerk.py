from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from dream_palace.domain import ApprovalStatus
from dream_palace.storage import FirebaseDreamStore


def build_dispatcher(bot: Bot, store: FirebaseDreamStore, admins: frozenset[int]) -> Dispatcher:
    dispatcher = Dispatcher()

    @dispatcher.message(Command("register"))
    async def register(message: Message) -> None:
        parts = (message.text or "").split(maxsplit=1)
        if not message.from_user or len(parts) != 2 or "@" not in parts[1]:
            await message.answer("Use /register you@example.com")
            return
        store.register(message.from_user.id, message.from_user.username or "", parts[1])
        for admin_id in admins:
            await bot.send_message(
                admin_id,
                f"Registration from @{message.from_user.username or '-'} "
                f"({message.from_user.id}, {parts[1]}). Approve with "
                f"/approve {message.from_user.id} or reject with /reject {message.from_user.id}.",
            )
        await message.answer("Registration submitted for administrator approval.")

    async def set_status(message: Message, status: ApprovalStatus, command: str) -> None:
        if not message.from_user or message.from_user.id not in admins:
            await message.answer("Administrator access required.")
            return
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) != 2 or not parts[1].isdigit():
            await message.answer(f"Use /{command} TELEGRAM_ID")
            return
        user_id = int(parts[1])
        store.set_approval(user_id, status)
        await bot.send_message(user_id, f"Your Dream Palace registration is {status.value}.")
        await message.answer(f"User {user_id} is now {status.value}.")

    @dispatcher.message(Command("approve"))
    async def approve(message: Message) -> None:
        await set_status(message, ApprovalStatus.APPROVED, "approve")

    @dispatcher.message(Command("reject"))
    async def reject(message: Message) -> None:
        await set_status(message, ApprovalStatus.REJECTED, "reject")

    return dispatcher
