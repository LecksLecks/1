import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # Telegram ID администратора

# Рабочие часы барбершопа
WORK_START = 10  # 10:00
WORK_END = 20   # 20:00
SLOT_DURATION = 60  # минут (длительность одной записи)

# Список мастеров
MASTERS = [
    {"id": 1, "name": "Алексей"},
    {"id": 2, "name": "Михаил"},
    {"id": 3, "name": "Дмитрий"},
]

# Каталог услуг
SERVICES = [
    {"id": 1, "name": "Стрижка машинкой", "price": 800, "duration": 30},
    {"id": 2, "name": "Стрижка ножницами", "price": 1000, "duration": 45},
    {"id": 3, "name": "Стрижка + борода", "price": 1500, "duration": 60},
    {"id": 4, "name": "Оформление бороды", "price": 700, "duration": 30},
    {"id": 5, "name": "Королевское бритьё", "price": 1200, "duration": 45},
    {"id": 6, "name": "Детская стрижка", "price": 600, "duration": 30},
]

# Дни недели (0=пн, 6=вс)
WORK_DAYS = [0, 1, 2, 3, 4, 5]  # пн-сб, воскресенье выходной
