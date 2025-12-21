import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    bot_token: int
    admin_id: int
    db_path: str = "/data/bot.db"

def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set")
    
    admin_id_raw = os.getenv("ADMIN_ID")
    if not admin_id_raw:
        raise RuntimeError("ADMIN_ID is not set")
    
    db_path = os.getenv("DB_PATH", "/data/bot.db")

    return Settings(
        bot_token=bot_token,
        admin_id=int(admin_id_raw),
        db_path=db_path,
    )