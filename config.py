# config.py
from dataclasses import dataclass
from environs import Env

@dataclass
class BotConfig:
    token: str
    admin_ids: list[int]

@dataclass
class Config:
    bot: BotConfig

def load_config(path: str = ".env") -> Config:
    env = Env()
    env.read_env(path)

    return Config(
        bot=BotConfig(
            token=env.str("BOT_TOKEN"),
            admin_ids=list(map(int, env.list("ADMIN_IDS"))),
        )
    )

# Максимальное кол-во часов в день (для валидации админа)
# (с 9:00 до 20:00 = 11 часов)
MAX_DAILY_HOURS = 11
