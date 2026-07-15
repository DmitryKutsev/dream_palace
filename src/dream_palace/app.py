"""Dream Palace application composition root."""

from dream_palace.interface.telegram import create_telegram_app
from dream_palace.shared.config import get_settings

app = create_telegram_app(get_settings())
