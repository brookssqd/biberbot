import discord
from discord.ext import commands, tasks
import random
import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import json
import discord.utils
from functools import wraps
import time
import traceback

# ==================== НАСТРОЙКИ ====================
import os
TOKEN = os.environ.get('TOKEN')

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Основные настройки
ADMIN_ROLE = "Admin"
CURRENCY_NAME = "Бибсы"
CURRENCY_EMOJI = "💰"
COMMAND_CHANNEL = "тест"
TRANSFER_FEE = 0.1
GIFT_PRICE = 4000
BIEBER_ESCAPE_INTERVAL = 1800

# Настройки семьи
FAMILY_UPGRADE_COSTS = {1: 8000, 2: 13000, 3: 19000, 4: 30000, 5: 50000}
FAMILY_HOURLY_BONUSES = {0: 0, 1: 10, 2: 20, 3: 50, 4: 100, 5: 180}

# Настройки карт
CARD_DROP_COOLDOWN = 43200  # 12 часов
user_last_card_drop = {}

# ==================== КОЛЛЕКЦИОННЫЕ КАРТОЧКИ ====================
COLLECTIBLE_CARDS = {
    "baby_jb": {
        "name": "Бибер в клипе 'Baby'",
        "rarity": "common",
        "emoji": "👶",
        "image": "https://media.giphy.com/media/3o7abB06u9bNzA8LC8/giphy.gif",
        "description": "Молодой Бибер покоряет мир!"
    },
    "purpose_jb": {
        "name": "Бибер эпохи Purpose",
        "rarity": "rare",
        "emoji": "🎤",
        "image": "https://media.giphy.com/media/l0MYEqE5x6Fqw3FJu/giphy.gif",
        "description": "Серьезный и взрослый Бибер"
    },
    "changes_jb": {
        "name": "Бибер в тату",
        "rarity": "epic",
        "emoji": "🔥",
        "image": "https://media.giphy.com/media/26gR2qDOkuj2GZgR2/giphy.gif",
        "description": "Бибер с новым стилем"
    },
    "justice_jb": {
        "name": "Бибер Justice Tour",
        "rarity": "legendary",
        "emoji": "👑",
        "image": "https://media.giphy.com/media/l1J9wL8w2rY2Fk4iE/giphy.gif",
        "description": "Бибер на сцене!"
    },
    "bieber_ghost": {
        "name": "Призрак Бибера",
        "rarity": "mythic",
        "emoji": "👻",
        "image": "https://media.giphy.com/media/3o7abB06u9bNzA8LC8/giphy.gif",
        "description": "Редчайшая карта! Бибер-призрак"
    },
    "bieber_angel": {
        "name": "Ангел Бибер",
        "rarity": "mythic",
        "emoji": "😇",
        "image": "https://media.giphy.com/media/3o7abB06u9bNzA8LC8/giphy.gif",
        "description": "Божественная карта!"
    },
    "bieber_demon": {
        "name": "Демон Бибер",
        "rarity": "legendary",
        "emoji": "😈",
        "image": "https://media.giphy.com/media/3o7abB06u9bNzA8LC8/giphy.gif",
        "description": "Темная сторона Бибера"
    },
    "bieber_christmas": {
        "name": "Рождественский Бибер",
        "rarity": "rare",
        "emoji": "🎄",
        "image": "https://media.giphy.com/media/3o7abB06u9bNzA8LC8/giphy.gif",
        "description": "Бибер в праздничном настроении"
    },
    "bieber_acoustic": {
        "name": "Акустический Бибер",
        "rarity": "epic",
        "emoji": "🎸",
        "image": "https://media.giphy.com/media/3o7abB06u9bNzA8LC8/giphy.gif",
        "description": "Бибер с гитарой"
    }
}

CARD_RARITY_COLORS = {
    "common": discord.Color.light_grey(),
    "rare": discord.Color.blue(),
    "epic": discord.Color.purple(),
    "legendary": discord.Color.gold(),
    "mythic": discord.Color.magenta()
}

# ==================== СЕКРЕТНЫЕ КОМБИНАЦИИ ====================
SECRET_COMBOS = {
    "молиться→проповедь→покаяться": {
        "reward": 500,
        "message": "🔓 **СЕКРЕТНАЯ КОМБИНАЦИЯ!** Ты прошел путь истинного belieber! +500 бибсов!",
        "rarity": "common"
    },
    "поцелуй→обнять→угостить": {
        "reward": 300,
        "message": "🔓 **РОМАНТИЧЕСКИЙ ВЕЧЕР!** Твоя забота о других принесла плоды! +300 бибсов!",
        "rarity": "common"
    },
    "молиться→молиться→молиться": {
        "reward": 200,
        "message": "🔓 **ИСТИННАЯ ВЕРА!** Три молитвы подряд услышаны! +200 бибсов!",
        "rarity": "common"
    },
    "предложить→принять-предложение": {
        "reward": 1000,
        "message": "🔓 **СВАДЕБНЫЙ БОНУС!** Поздравляем молодоженов! +1000 бибсов!",
        "rarity": "common"
    },
    "молиться→проповедь→покаяться→экстаз→молиться": {
        "reward": 2000,
        "message": "🔓 **ПРОСВЕТЛЕНИЕ!** Ты достиг высшего уровня поклонения! +2000 бибсов и карта Ангел Бибер!",
        "rarity": "epic",
        "card": "bieber_angel"
    },
    "поцелуй→обнять→угостить→занятьсялюбовью→подарок": {
        "reward": 1500,
        "message": "🔓 **ИДЕАЛЬНЫЕ ОТНОШЕНИЯ!** Ты мастер романтики! +1500 бибсов!",
        "rarity": "rare"
    },
    "дуэль→принять→бой→дуэль→бой": {
        "reward": 2500,
        "message": "🔓 **НЕПОБЕДИМЫЙ ВОИН!** Твои победы в дуэлях впечатляют! +2500 бибсов!",
        "rarity": "epic"
    },
    "предложить→принять-предложение→добавитьребенка→улучшитьсемью→моясемья": {
        "reward": 5000,
        "message": "🔓 **СЕМЕЙНАЯ САГА!** Твоя семья — пример для подражания! +5000 бибсов и карта Justice Бибер!",
        "rarity": "legendary",
        "card": "justice_jb"
    }
}

# ==================== ПЕРСОНАЛИЗИРОВАННЫЕ ПОЗДРАВЛЕНИЯ ====================
PERSONALIZED_COMPLIMENTS = {
    "balance_milestone": [
        "У тебя {balance} {emoji} {name}! Бибер бы гордился!",
        "Вау! {balance} {emoji} {name}! Ты настоящий фанат!",
        "{name}, с таким балансом {balance} {emoji} ты можешь купить билет на концерт Бибера!",
        "Твой баланс {balance} {emoji} {name} — это мощь! 🔥"
    ],
    "random": [
        "Ты {role} {name}!",
        "Бибер заметил тебя, {name}!",
        "{name}, ты сияешь как звезда!",
        "Фанаты в восторге от тебя, {name}!",
        "Ты {name} из тысячи!"
    ]
}

# ==================== ЭМОДЗИ ДЛЯ РЕАКЦИЙ ====================
COMMAND_REACTIONS = {
    "молиться": ["🙏", "✨", "🕯️"],
    "проповедь": ["📖", "✝️", "🙌"],
    "экстаз": ["🎉", "🔥", "💫"],
    "покаяться": ["😢", "💔", "🕊️"],
    "поцелуй": ["💋", "💕", "😘"],
    "обнять": ["🤗", "💞", "🫂"],
    "ударить": ["👊", "💥", "😤"],
    "угостить": ["🍬", "🍪", "☕"],
    "занятьсялюбовью": ["💖", "💗", "💓"],
    "подарок": ["🎁", "🎀", "✨"],
    "дуэль": ["⚔️", "🏆", "🎯"]
}

# Авто-реакции на ключевые слова
AUTO_REACTIONS = {
    "бибер": "👶",
    "bibber": "👶",
    "biber": "👶",
    "благослови": "🙏",
    "спасибо": "💖",
    "помоги": "🆘",
    "победа": "🏆",
    "круто": "🔥",
    "класс": "👍",
    "супер": "⭐",
    "люблю": "💕",
    "фанат": "💛"
}

# ==================== КЛАСС ДЛЯ АНИМАЦИИ ====================
class LoadingAnimation:
    def __init__(self, ctx, text: str = "Обработка", emoji: str = "🔄"):
        self.ctx = ctx
        self.text = text
        self.emoji = emoji
        self.message = None
        self.frames = ["🟢", "🟡", "🔴", "🟡"]
        self.running = False
    
    async def start(self):
        self.running = True
        self.message = await self.ctx.send(f"{self.emoji} {self.text}...")
        asyncio.create_task(self._animate())
    
    async def _animate(self):
        frame_index = 0
        while self.running:
            frame = self.frames[frame_index % len(self.frames)]
            await self.message.edit(content=f"{frame} {self.text}... {self.emoji}")
            frame_index += 1
            await asyncio.sleep(0.5)
    
    async def stop(self, success: bool = True, result_text: str = ""):
        self.running = False
        emoji = "✅" if success else "❌"
        await self.message.edit(content=f"{emoji} {result_text}" if result_text else f"{emoji} Готово!")

def create_embed(title: str, description: str = "", color: discord.Color = None, 
                 thumbnail: str = None, image: str = None, footer: str = None,
                 author: discord.Member = None, timestamp: bool = True) -> discord.Embed:
    if color is None:
        color = discord.Color.gold()
    
    embed = discord.Embed(
        title=f"✨ {title} ✨",
        description=description,
        color=color,
        timestamp=datetime.now() if timestamp else None
    )
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    if image:
        embed.set_image(url=image)
    
    if footer:
        embed.set_footer(text=f"{footer} 🙏 BiberBOT")
    else:
        embed.set_footer(text="🙏 BiberBOT")
    
    if author:
        embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
    
    return embed

# ==================== БАЗА ДАННЫХ ====================
class DatabaseManager:
    def __init__(self, db_path: str = 'biberbot.db'):
        self.db_path = db_path
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def execute(self, query: str, params: tuple = ()):
        conn = self._get_conn()
        try:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"[DB ERROR] {e}")
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def fetch_one(self, query: str, params: tuple = ()):
        conn = self._get_conn()
        try:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def fetch_all(self, query: str, params: tuple = ()):
        conn = self._get_conn()
        try:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

db = DatabaseManager()

# ==================== ИНИЦИАЛИЗАЦИЯ БД ====================
def init_db():
    queries = [
        """CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            last_pray TIMESTAMP,
            last_sermon TIMESTAMP,
            last_repent TIMESTAMP,
            last_ecstasy TIMESTAMP,
            artifacts TEXT DEFAULT '{}',
            cards TEXT DEFAULT '[]',
            completed_combos TEXT DEFAULT '[]',
            personal_role INTEGER,
            personal_tag TEXT,
            last_proposal TIMESTAMP,
            last_divorce TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        "CREATE INDEX IF NOT EXISTS idx_users_balance ON users(balance DESC)",
        
        """CREATE TABLE IF NOT EXISTS families (
            family_id INTEGER PRIMARY KEY AUTOINCREMENT,
            spouse1_id INTEGER,
            spouse2_id INTEGER,
            children TEXT DEFAULT '[]',
            level INTEGER DEFAULT 1,
            family_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        """CREATE TABLE IF NOT EXISTS marriage_proposals (
            proposal_id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id INTEGER,
            to_id INTEGER,
            proposal_text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        """CREATE TABLE IF NOT EXISTS active_duels (
            channel_id INTEGER PRIMARY KEY,
            challenger_id INTEGER,
            target_id INTEGER,
            amount INTEGER,
            accepted BOOLEAN DEFAULT 0,
            fighters_ready TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        """CREATE TABLE IF NOT EXISTS bieber_catch (
            user_id INTEGER PRIMARY KEY,
            catches INTEGER DEFAULT 0,
            fake_catches INTEGER DEFAULT 0
        )""",
        
        """CREATE TABLE IF NOT EXISTS duels (
            user_id INTEGER,
            date TEXT,
            count INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, date)
        )""",
        
        """CREATE TABLE IF NOT EXISTS logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER,
            command TEXT,
            details TEXT
        )""",
        
        """CREATE TABLE IF NOT EXISTS gifts (
            gift_id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id INTEGER,
            to_user_id INTEGER,
            gift_type TEXT,
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        """CREATE TABLE IF NOT EXISTS confessions (
            confession_id INTEGER PRIMARY KEY AUTOINCREMENT,
            confession_text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    ]
    
    for query in queries:
        try:
            db.execute(query)
        except Exception as e:
            print(f"Ошибка: {e}")

# ==================== ФУНКЦИИ РАБОТЫ С БАЛАНСОМ ====================
def add_balance(user_id: int, amount: int) -> int:
    """Универсальная функция для изменения баланса. Возвращает новый баланс."""
    try:
        # Создаём пользователя если нет
        db.execute("""
            INSERT OR IGNORE INTO users (user_id, balance, artifacts, cards, completed_combos, created_at) 
            VALUES (?, 0, '{}', '[]', '[]', ?)
        """, (user_id, datetime.now().isoformat()))
        
        # Обновляем баланс
        db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        
        # Получаем новый баланс
        result = db.fetch_one("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        new_balance = result["balance"] if result else 0
        
        print(f"[BALANCE] {user_id}: {amount:+d} -> {new_balance}")
        
        # Логируем
        log_action(user_id, "balance_change", f"Amount: {amount}, New: {new_balance}")
        
        return new_balance
    except Exception as e:
        print(f"[ERROR] add_balance: {e}")
        traceback.print_exc()
        result = db.fetch_one("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        return result["balance"] if result else 0

def get_balance(user_id: int) -> int:
    """Получить текущий баланс напрямую из БД"""
    try:
        result = db.fetch_one("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        if not result:
            db.execute("""
                INSERT INTO users (user_id, balance, artifacts, cards, completed_combos, created_at) 
                VALUES (?, 0, '{}', '[]', '[]', ?)
            """, (user_id, datetime.now().isoformat()))
            return 0
        return result["balance"]
    except Exception as e:
        print(f"[ERROR] get_balance: {e}")
        return 0

# Для обратной совместимости
def get_user_balance(user_id: int) -> int:
    return get_balance(user_id)

def update_user_balance(user_id: int, amount: int) -> int:
    return add_balance(user_id, amount)

def log_action(user_id: int, command: str, details: str = ""):
    try:
        db.execute(
            "INSERT INTO logs (timestamp, user_id, command, details) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), user_id, command, details)
        )
    except Exception as e:
        print(f"Ошибка логирования: {e}")

def get_user_data(user_id: int) -> dict:
    """Получить данные пользователя (всегда свежие из БД)"""
    result = db.fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    
    if not result:
        db.execute("""
            INSERT INTO users (user_id, balance, artifacts, cards, completed_combos, created_at) 
            VALUES (?, 0, '{}', '[]', '[]', ?)
        """, (user_id, datetime.now().isoformat()))
        result = db.fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    
    if not result:
        return {
            "balance": 0,
            "last_pray": None,
            "last_sermon": None,
            "last_repent": None,
            "last_ecstasy": None,
            "artifacts": {},
            "cards": [],
            "completed_combos": [],
            "personal_role": None,
            "personal_tag": None,
            "last_proposal": None,
            "last_divorce": None
        }
    
    artifacts = {}
    cards = []
    completed_combos = []
    
    try:
        if result.get("artifacts"):
            artifacts = json.loads(result["artifacts"])
    except:
        artifacts = {}
    
    try:
        if result.get("cards"):
            cards = json.loads(result["cards"])
    except:
        cards = []
    
    try:
        if result.get("completed_combos"):
            completed_combos = json.loads(result["completed_combos"])
    except:
        completed_combos = []
    
    return {
        "balance": result.get("balance", 0),
        "last_pray": result.get("last_pray"),
        "last_sermon": result.get("last_sermon"),
        "last_repent": result.get("last_repent"),
        "last_ecstasy": result.get("last_ecstasy"),
        "artifacts": artifacts,
        "cards": cards,
        "completed_combos": completed_combos,
        "personal_role": result.get("personal_role"),
        "personal_tag": result.get("personal_tag"),
        "last_proposal": result.get("last_proposal"),
        "last_divorce": result.get("last_divorce")
    }

def update_user_data(user_id: int, data: dict):
    """Обновить данные пользователя"""
    try:
        db.execute("""
            UPDATE users SET 
                balance = ?,
                last_pray = ?,
                last_sermon = ?,
                last_repent = ?,
                last_ecstasy = ?,
                artifacts = ?,
                cards = ?,
                completed_combos = ?,
                personal_role = ?,
                personal_tag = ?,
                last_proposal = ?,
                last_divorce = ?
            WHERE user_id = ?
        """, (
            data["balance"],
            data["last_pray"],
            data["last_sermon"],
            data["last_repent"],
            data["last_ecstasy"],
            json.dumps(data["artifacts"]),
            json.dumps(data["cards"]),
            json.dumps(data["completed_combos"]),
            data["personal_role"],
            data["personal_tag"],
            data["last_proposal"],
            data["last_divorce"],
            user_id
        ))
    except Exception as e:
        print(f"[DB ERROR] Ошибка обновления: {e}")

# ==================== ФУНКЦИИ ДЛЯ КАРТОЧЕК ====================
def add_card_to_user(user_id: int, card_id: str) -> bool:
    """
    Добавить карточку пользователю
    Возвращает True если карта добавлена, False если уже есть
    """
    if card_id not in COLLECTIBLE_CARDS:
        print(f"[ERROR] Карта {card_id} не найдена в коллекции")
        return False
    
    # Получаем текущие карты пользователя напрямую из БД
    user_data = db.fetch_one("SELECT cards FROM users WHERE user_id = ?", (user_id,))
    cards = []
    
    if user_data and user_data["cards"]:
        try:
            cards = json.loads(user_data["cards"])
        except json.JSONDecodeError:
            print(f"[ERROR] Ошибка парсинга cards для {user_id}")
            cards = []
    
    # Проверяем, есть ли уже такая карта
    if card_id in cards:
        print(f"[DEBUG] У пользователя {user_id} уже есть карта {card_id}")
        return False
    
    # Добавляем карту
    cards.append(card_id)
    
    # Обновляем в БД
    try:
        db.execute("UPDATE users SET cards = ? WHERE user_id = ?", (json.dumps(cards), user_id))
        print(f"[CARD] Пользователю {user_id} добавлена карта {card_id}")
        log_action(user_id, "add_card", card_id)
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка при добавлении карты: {e}")
        return False

def get_random_card() -> str:
    """
    Получить случайную карту с учетом редкости
    Вероятности выпадения:
    - Обычные (baby_jb): 30%
    - Редкие (purpose_jb, christmas): 35%
    - Эпические (changes_jb, acoustic): 25%
    - Легендарные (justice_jb, demon): 9%
    - Мифические (ghost, angel): 3%
    """
    cards = list(COLLECTIBLE_CARDS.keys())
    weights = {
        "baby_jb": 30,           # 30% - обычная
        "purpose_jb": 20,        # 20% - редкая
        "bieber_christmas": 15,  # 15% - редкая
        "changes_jb": 15,        # 15% - эпическая
        "bieber_acoustic": 10,   # 10% - эпическая
        "justice_jb": 5,         # 5% - легендарная
        "bieber_demon": 4,       # 4% - легендарная
        "bieber_ghost": 2,       # 2% - мифическая
        "bieber_angel": 1        # 1% - мифическая
    }
    
    # Преобразуем веса в список для random.choices
    weight_list = [weights.get(card, 5) for card in cards]
    return random.choices(cards, weights=weight_list)[0]

def get_user_cards_collection(user_id: int) -> dict:
    """
    Получить коллекцию карт пользователя с группировкой по редкости
    Возвращает словарь:
    {
        "common": [список карт],
        "rare": [список карт],
        "epic": [список карт],
        "legendary": [список карт],
        "mythic": [список карт],
        "total": количество карт,
        "total_possible": всего карт в игре
    }
    """
    # Получаем карты пользователя из БД
    user_data = db.fetch_one("SELECT cards FROM users WHERE user_id = ?", (user_id,))
    cards = []
    
    if user_data and user_data["cards"]:
        try:
            cards = json.loads(user_data["cards"])
        except json.JSONDecodeError:
            print(f"[ERROR] Ошибка парсинга cards для {user_id}")
            cards = []
    
    # Инициализируем структуру коллекции
    collection = {
        "common": [],
        "rare": [],
        "epic": [],
        "legendary": [],
        "mythic": [],
        "total": len(cards),
        "total_possible": len(COLLECTIBLE_CARDS)
    }
    
    # Группируем карты по редкости
    for card_id in cards:
        if card_id in COLLECTIBLE_CARDS:
            rarity = COLLECTIBLE_CARDS[card_id]["rarity"]
            collection[rarity].append(card_id)
    
    return collection

async def try_drop_card(ctx, command: str):
    """
    Проверяет шанс выпадения карты после команды
    Кулдаун: 12 часов (43200 секунд)
    """
    user_id = ctx.author.id
    current_time = datetime.now()
    
    # Проверяем кулдаун (12 часов)
    if user_id in user_last_card_drop:
        time_since_last = (current_time - user_last_card_drop[user_id]).total_seconds()
        if time_since_last < CARD_DROP_COOLDOWN:
            # Кулдаун ещё не прошёл
            return False
    
    # Шансы выпадения для разных команд
    chances = {
        "молиться": 8,      # 8% шанс
        "проповедь": 8,     # 8% шанс
        "экстаз": 5,        # 5% шанс
        "покаяться": 3,     # 3% шанс
        "дуэль": 4,         # 4% шанс за победу в дуэли
        "подарок": 2        # 2% шанс
    }
    
    chance = chances.get(command, 1)  # По умолчанию 1%
    
    # Проверяем выпадение
    if random.randint(1, 100) <= chance:
        card_id = get_random_card()
        card_info = COLLECTIBLE_CARDS[card_id]
        
        # Добавляем карту пользователю
        if add_card_to_user(user_id, card_id):
            # Обновляем время последнего выпадения
            user_last_card_drop[user_id] = current_time
            
            # Создаём красивое сообщение о получении карты
            embed = create_embed(
                title=f"🎴 НОВАЯ КАРТА!",
                description=f"Ты получил карту **{card_info['name']}** {card_info['emoji']}\n"
                           f"Редкость: **{card_info['rarity'].upper()}**\n\n"
                           f"{card_info['description']}\n\n"
                           f"⏳ Следующая карта выпадет через **12 часов**!",
                color=CARD_RARITY_COLORS.get(card_info["rarity"], discord.Color.gold()),
                image=card_info["image"],
                footer="Собирай все карты Бибера!"
            )
            await ctx.send(embed=embed)
            return True
    
    return False

# ==================== ФУНКЦИИ ДЛЯ КОМБИНАЦИЙ ====================
# ==================== ФУНКЦИИ ДЛЯ КОМБИНАЦИЙ ====================

def check_secret_combo(user_id: int, command_sequence: list) -> Optional[Tuple[str, dict]]:
    """
    Проверить, есть ли секретная комбинация
    Возвращает (combo_str, combo_data) или None
    """
    combo_str = "→".join(command_sequence)
    
    # Проверяем точное совпадение
    if combo_str in SECRET_COMBOS:
        combo_data = SECRET_COMBOS[combo_str]
        
        # Проверяем, не выполнил ли пользователь эту комбинацию ранее
        user_data = db.fetch_one("SELECT completed_combos FROM users WHERE user_id = ?", (user_id,))
        completed_combos = []
        
        if user_data and user_data["completed_combos"]:
            try:
                completed_combos = json.loads(user_data["completed_combos"])
            except:
                completed_combos = []
        
        # Если уже выполнял, не даём награду повторно
        if combo_str in completed_combos:
            return None
        
        return (combo_str, combo_data)
    
    return None

def complete_combo(user_id: int, combo_str: str):
    """Отметить комбинацию как выполненную"""
    user_data = db.fetch_one("SELECT completed_combos FROM users WHERE user_id = ?", (user_id,))
    completed_combos = []
    
    if user_data and user_data["completed_combos"]:
        try:
            completed_combos = json.loads(user_data["completed_combos"])
        except:
            completed_combos = []
    
    if combo_str not in completed_combos:
        completed_combos.append(combo_str)
        db.execute("UPDATE users SET completed_combos = ? WHERE user_id = ?", 
                  (json.dumps(completed_combos), user_id))

user_command_history = {}

async def check_combos(ctx):
    """
    Проверить комбинации после каждой команды
    """
    user_id = ctx.author.id
    
    if user_id not in user_command_history:
        user_command_history[user_id] = []
    
    # Добавляем текущую команду в историю
    user_command_history[user_id].append(ctx.command.name)
    
    # Храним последние 10 команд
    if len(user_command_history[user_id]) > 10:
        user_command_history[user_id] = user_command_history[user_id][-10:]
    
    # Проверяем комбинации разной длины (от 2 до 7 команд)
    for length in range(2, min(8, len(user_command_history[user_id]) + 1)):
        sequence = user_command_history[user_id][-length:]
        result = check_secret_combo(user_id, sequence)
        
        # ВАЖНО: проверяем, что result не None
        if result is not None:
            combo_str, combo_data = result
            
            # Начисляем награду
            db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", 
                      (combo_data["reward"], user_id))
            
            card_reward = ""
            if "card" in combo_data:
                if add_card_to_user(user_id, combo_data["card"]):
                    card_info = COLLECTIBLE_CARDS[combo_data["card"]]
                    card_reward = f"\n🎴 Получена карта: **{card_info['name']}** {card_info['emoji']}"
            
            # Отмечаем комбинацию как выполненную
            complete_combo(user_id, combo_str)
            
            # Отправляем сообщение
            embed = create_embed(
                title="🥷 СЕКРЕТНАЯ КОМБИНАЦИЯ!",
                description=f"{combo_data['message']}{card_reward}\n\n✨ Редкость: **{combo_data['rarity'].upper()}**",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
            break

# ==================== ДЕКОРАТОРЫ ====================
def in_command_channel():
    def decorator(func):
        @wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            if ctx.channel.name != COMMAND_CHANNEL:
                embed = create_embed(
                    title="❌ Неверный канал!",
                    description=f"Команды бота работают только в канале **#{COMMAND_CHANNEL}**!",
                    color=discord.Color.red()
                )
                try:
                    await ctx.author.send(embed=embed)
                    await ctx.message.delete()
                except:
                    await ctx.send(embed=embed, delete_after=5)
                return
            return await func(ctx, *args, **kwargs)
        return wrapper
    return decorator

def add_command_reaction(command_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            result = await func(ctx, *args, **kwargs)
            if command_name in COMMAND_REACTIONS:
                emoji = random.choice(COMMAND_REACTIONS[command_name])
                try:
                    await ctx.message.add_reaction(emoji)
                except:
                    pass
            return result
        return wrapper
    return decorator

COOLDOWNS = {
    "pray": 3600,
    "sermon": 7200,
    "repent": 3600,
    "ecstasy": 3600,
    "proposal": 60,
    "divorce": 86400,
}

def cooldown(command_name: str):
    """Декоратор для проверки кулдауна команд (работает напрямую с БД)"""
    def decorator(func):
        @wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            user_id = ctx.author.id
            
            # Получаем время последнего использования команды напрямую из БД
            user_data = db.fetch_one(f"SELECT last_{command_name} FROM users WHERE user_id = ?", (user_id,))
            last_time_str = user_data[f"last_{command_name}"] if user_data else None
            
            if last_time_str:
                try:
                    last_time = datetime.fromisoformat(last_time_str)
                    elapsed = (datetime.now() - last_time).total_seconds()
                    remaining = COOLDOWNS.get(command_name, 0) - elapsed
                    
                    if remaining > 0:
                        hours = int(remaining // 3600)
                        minutes = int((remaining % 3600) // 60)
                        secs = int(remaining % 60)
                        
                        if hours > 0:
                            time_str = f"{hours}ч {minutes}м {secs}с"
                        elif minutes > 0:
                            time_str = f"{minutes}м {secs}с"
                        else:
                            time_str = f"{secs}с"
                        
                        embed = create_embed(
                            title="⏳ Кулдаун!",
                            description=f"Подожди **{time_str}** перед следующим использованием `!{command_name}`!",
                            color=discord.Color.red()
                        )
                        await ctx.send(embed=embed, delete_after=10)
                        return
                except Exception as e:
                    print(f"[ERROR] cooldown parse for {command_name}: {e}")
            
            # Выполняем команду
            result = await func(ctx, *args, **kwargs)
            
            # Обновляем время последнего использования
            # Сначала убеждаемся, что пользователь существует
            user_exists = db.fetch_one("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if not user_exists:
                db.execute("""
                    INSERT INTO users (user_id, balance, artifacts, cards, completed_combos, created_at) 
                    VALUES (?, 0, '{}', '[]', '[]', ?)
                """, (user_id, datetime.now().isoformat()))
            
            # Обновляем время
            db.execute(f"UPDATE users SET last_{command_name} = ? WHERE user_id = ?", 
                      (datetime.now().isoformat(), user_id))
            
            return result
        return wrapper
    return decorator

EMOJIS = {
    "bibsy": CURRENCY_EMOJI,
    "pray": "🙏",
    "sermon": "📖",
    "shop": "🛒",
    "win": "🎉",
    "lose": "😢",
    "artifact": "🔮",
    "role": "🎭",
    "leaderboard": "🏆",
    "bieber": "👶",
    "duel": "⚔️",
    "family": "👪",
    "ring": "💍",
    "kiss": "💋",
    "hug": "🤗",
    "hit": "👊",
    "treat": "🍬",
    "love": "❤️",
    "gift": "🎁",
    "transfer": "💸",
    "card": "🎴"
}

SHOP_ITEMS = {
    "twitter_scroll": {
        "name": "Твиттер-свиток",
        "price": 4500,
        "type": "permanent",
        "effect": {"command": "sermon", "bonus": 20}
    },
    "wet_relic": {
        "name": "Промокшая реликвия",
        "price": 9000,
        "type": "permanent",
        "effect": {"command": "pray", "bonus": 20}
    },
    "bieber_amulet": {
        "name": "Амулет Бибера",
        "price": 13500,
        "type": "permanent",
        "effect": {"command": "pray", "bonus": 30}
    },
    "fan_tape": {
        "name": "Фанатская касета",
        "price": 18000,
        "type": "permanent",
        "effect": {"command": "pray", "bonus": 40}
    },
    "personal_role": {
        "name": "Личная роль",
        "price": 50000,
        "type": "role"
    },
    "personal_tag": {
        "name": "Тег",
        "price": 25000,
        "type": "tag"
    },
    "gift": {
        "name": "Подарок",
        "price": GIFT_PRICE,
        "type": "gift"
    }
}

WORK_OPTIONS = [
    {"name": "Раздавал флаеры «Only Beliebers allowed»", "reward": 50},
    {"name": "Протирал алтарь с винилами Бибера", "reward": 55},
    {"name": "Исполнял \"Sorry\" в переходе", "reward": 65},
    {"name": "Рисовал граффити с надписью \"JB 4EVER\"", "reward": 69},
    {"name": "Проставлял лайки на фан-арт", "reward": 53},
    {"name": "Ставил свечи перед клипом \"Baby\"", "reward": 70},
    {"name": "Вёл кружок юных фанатов", "reward": 100},
    {"name": "Заучивал тексты песен наизусть", "reward": 80},
    {"name": "Ставил \"повтор\" на трек 200 раз", "reward": 100},
    {"name": "Читал рэп-переводы на собрании", "reward": 60},
    {"name": "Создавал фан-аккаунт в TikTok", "reward": 70},
    {"name": "Писал хейтерам слово \"анатема\"", "reward": 45},
    {"name": "Репетировал танец из \"Sorry\"", "reward": 40},
    {"name": "Переводил биографию Бибера на латынь", "reward": 75},
    {"name": "Клеил листовки \"Бибер --- путь, истина, лайк\"", "reward": 80}
]

SERMONS = [
    {"text": "«Когда Бибер пел \"Hold on\", он держал за руку весь мир.»", "reward": 69},
    {"text": "«Бибер не ошибается. Он просто делает ремикс на реальность.»", "reward": 95},
    {"text": "«Каждый \"baby\" из его песни --- это шаг к просветлению.»", "reward": 105},
    {"text": "«Он пришёл с севера Канады, чтобы растопить наши сердца.»", "reward": 54},
    {"text": "«Кто не с Бибером --- тот просто не на автотюне судьбы.»", "reward": 60},
    {"text": "«\"Ghost\" --- не про грусть. Это про нас, когда Wi-Fi отвалился на фан-стриме.»", "reward": 120},
    {"text": "«Настоящий belieber не спрашивает \"когда\", он нажимает \"репит\".»", "reward": 50},
    {"text": "«Бибер --- это не музыка. Это операционная система для сердца.»", "reward": 77},
    {"text": "«Тысячи лайков могут сказать \"да\", но достаточно одного дизлайка, чтобы вспомнить \"Never Say Never\".»", "reward": 66},
    {"text": "«И пусть тебя предаст весь мир --- JB останется в рекомендациях.»", "reward": 90}
]

KISS_CONTEXTS = [
    {"text": "нежно целует в щёчку", "gif": "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExZDFjZ3lkMW5kOW9zdHJjeWRocWNld2g3cHMzZ3Q0dm5lbzdrN2VyNCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/AOdpDF2DPkUB2sO1TY/giphy.gif"},
    {"text": "страстно целует в губы", "gif": "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNTFzNDMwdWxndGVyZHI1ZjN3ZmJlbjUwMmRsbnhiZmxldHN1cTA4aSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/gClggN4VEbVvbJdGA2/giphy.gif"},
    {"text": "целует в лобик", "gif": "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExbGx1NnRjeGJuaTc2czJ2MW82Z3R2cG1uMHlmOW56NDhpMDQ0Y3A3dSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/WJuZ2lFG70NKlJxXGg/giphy.gif"},
    {"text": "целует в носик", "gif": "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExaW5rNjI2ZmQ2c3JkcnJzeW8xY3R3aW55amNiM2JmM2lnbnprMW9ueiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/iXSVqcSC13ITk6w4Rs/giphy.gif"},
    {"text": "дарит французский поцелуй", "gif": "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExbzViaTd5ejJ4MnA4a255bmoxbG9mbHVzbGlvdHRsZHl1ZDR1OTNkMCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/wLn8S7EOfaWlcaKEB0/giphy.gif"},
    {"text": "дарит нежный поцелуй в губы", "gif": "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExcDU0c2QxMXdzZDluNTcyZ2J6Y21hMjE1eDNsdWczc2owbXAzbm84dCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/HuD1XNi2UJ5CXOqjcc/giphy.gif"}
]

HUG_CONTEXTS = [
    {"text": "крепко обнимает", "gif": "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExYnAxdGQ3YmRtdW1wenkzeDltdW1qN2E4NmhoOG1yeTF5NXZuZXExcCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/wv8PUwhN4ih42opWub/giphy.gif"},
    {"text": "нежно обнимает за плечи", "gif": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExcmNhd28yYTgzZngwbjBleXcycWozNmQ1bWZlZjczYXRsaWFmeGNndiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/VXQRnSE1zBWz57MDbX/giphy.gif"},
    {"text": "обнимает сзади", "gif": "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExZDQzNjZzc29xZ2hrZmo4bzN1bm1udHVpdjF2cGpmODZsa2VkcHBiNSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/dubNSXJgcIqFo7eJOu/giphy.gif"},
    {"text": "обнимает и гладит по голове", "gif": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExNThhMDFuZHdybnQxaHdjYnJ2YnAydHhzdGJpM2liYWFlbDN0YXdtMCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/JywMlvu3Cq5ZjIEkx3/giphy.gif"}
]

HIT_CONTEXTS = [
    {"text": "шлёпает", "gif": "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExc2lkYnVtNnp5NW10d3dhdGV2dnozNTNpczJrcW81aTFxdHh6YTI0dyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/tZET0HrM7GY2EWvkUO/giphy.gif"},
    {"text": "бьёт мечом", "gif": "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExcnpiNnl2ZGtmOHBrejczbjZoeDB0NnM3ZzJ2M3d1Y3cxdWprZjN4diZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Y8uXSzA3gGAod14Doe/giphy.gif"},
    {"text": "тыкает пальчиком", "gif": "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExMTViNTZxZXZiZGEwb3IxeDdmZnNyMW9tNGJmbzdvYmQyNnZma3prOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/SxqcvyUq5UWq1cYSrm/giphy.gif"},
    {"text": "бьёт ногами", "gif": "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExeXcxb2hhY2Zwb2N1M3F5bDBlend5aWl1YXE5MmtyZDVzZTBqOTJwdSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Omoski16P1UE0F9Ywe/giphy.gif"}
]

TREAT_CONTEXTS = [
    {"text": "угощает конфеткой", "gif": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExeHhva3NhNmM2OGw2NGQ1MnNvMHdlYzZ5eDE0OWZvZGU5am9ueHM0NCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/eo8vbWCa3uztyQkNCf/giphy.gif"},
    {"text": "угощает печеньем", "gif": "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExOWF6d2Uxd2p2a3h6aGQwc2E5NjQ1MGphaWZ1Ymg4c2QyeWc2ZXdiYiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/6f9CJQRgluoNLYXqbb/giphy.gif"},
    {"text": "предлагает чашечку чая", "gif": "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExNHNheTNsZXQ5MDhhcHZzM2diaWpuN2txejQwd3A1bjhzd3cwNTVtZiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/2CvIUdfcpBqdTboT8n/giphy.gif"},
    {"text": "дарит мороженое", "gif": "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExZnlwODh4NW5pd2xkMWFydWVwN2hqZTFzcHpmc2R2bHFrcXZjMHA4cCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/bf3QSFUJeysubP8Ewl/giphy.gif"}
]

LOVE_CONTEXTS = [
    {"text": "нежно занимается любовью", "gif": "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExampkNGt4MGZoc3Rnd2RvNGRmZ2xkNnRjNzBrdGFtMWNwMTQ4aHhjbSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3lAa7jWpZOb0IJx422/giphy.gif"},
    {"text": "страстно занимается любовью", "gif": "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExeXN0dWJzc2kxN3g0eXl2Z3hqM2lxMHJ0YjEyZmdsZDhpeHFjejAyeSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/phHBMQjP1rm0AMSXlP/giphy.gif"},
    {"text": "романтично занимается любовью", "gif": "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExYmNjMXA1NDhsYXVycHFuaXl5MnNhZHd2dHJoaHJlMHR0Mml3M3JhdyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/RgGoCnM5FAvYEnaMd8/giphy.gif"},
    {"text": "нежно обнимает во время любви", "gif": "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExdHBzbm1lOHFjazNvZDIxaGEwdWRzN2N1NngzbzQ0NnkyaW52ZjZvNyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/24c0Ptqt7sorFLJHp6/giphy.gif"}
]

GIFT_TYPES = {
    "цветы": "💐",
    "плюшевый мишка": "🧸", 
    "плюшевый зайчик": "🐰",
    "сердечки": "💖",
    "рандом": "🎁"
}

# ==================== АРТЕФАКТЫ ====================
class ArtifactManager:
    @staticmethod
    def calculate_bonus(user_id: int, command: str, base_reward: int) -> int:
        # ВАЖНО: используем get_user_data, но не кэшируем результат
        data = get_user_data(user_id)
        artifacts = data.get("artifacts", {})
        total_bonus_percent = 0
        
        for artifact_id, artifact_data in artifacts.items():
            if artifact_id not in SHOP_ITEMS:
                continue
            
            artifact_info = SHOP_ITEMS[artifact_id]
            
            if artifact_info["type"] in ["permanent", "legendary"]:
                if artifact_info["effect"]["command"] == command:
                    total_bonus_percent += artifact_info["effect"]["bonus"]
        
        total_bonus_percent = min(total_bonus_percent, 300)
        bonus = int(base_reward * total_bonus_percent / 100)
        return bonus
    
    @staticmethod
    def add_artifact(user_id: int, artifact_id: str) -> bool:
        if artifact_id not in SHOP_ITEMS:
            return False
        
        data = get_user_data(user_id)
        
        if artifact_id in data["artifacts"]:
            if SHOP_ITEMS[artifact_id]["type"] in ["permanent", "legendary"]:
                return False
        
        data["artifacts"][artifact_id] = {}
        update_user_data(user_id, data)
        log_action(user_id, "add_artifact", artifact_id)
        return True

# ==================== МЕНЕДЖЕР ДУЭЛЕЙ ====================
class DuelManager:
    @staticmethod
    def create_duel(channel_id: int, challenger_id: int, target_id: int, amount: int) -> bool:
        try:
            db.execute("""
                INSERT OR REPLACE INTO active_duels 
                (channel_id, challenger_id, target_id, amount, accepted, fighters_ready, created_at)
                VALUES (?, ?, ?, ?, 0, '[]', ?)
            """, (channel_id, challenger_id, target_id, amount, datetime.now().isoformat()))
            return True
        except Exception as e:
            print(f"Ошибка создания дуэли: {e}")
            return False
    
    @staticmethod
    def get_duel(channel_id: int) -> Optional[dict]:
        return db.fetch_one("SELECT * FROM active_duels WHERE channel_id = ?", (channel_id,))
    
    @staticmethod
    def delete_duel(channel_id: int):
        db.execute("DELETE FROM active_duels WHERE channel_id = ?", (channel_id,))
    
    @staticmethod
    def accept_duel(channel_id: int, target_id: int) -> bool:
        duel = DuelManager.get_duel(channel_id)
        if not duel or duel["target_id"] != target_id:
            return False
        db.execute("UPDATE active_duels SET accepted = 1 WHERE channel_id = ?", (channel_id,))
        return True
    
    @staticmethod
    def add_fighter_ready(channel_id: int, fighter_id: int) -> int:
        duel = DuelManager.get_duel(channel_id)
        if not duel:
            return 0
        
        fighters = json.loads(duel["fighters_ready"] or "[]")
        if fighter_id not in fighters:
            fighters.append(fighter_id)
        
        db.execute(
            "UPDATE active_duels SET fighters_ready = ? WHERE channel_id = ?",
            (json.dumps(fighters), channel_id)
        )
        return len(fighters)
    
    @staticmethod
    def cleanup_old_duels():
        db.execute("""
            DELETE FROM active_duels 
            WHERE julianday('now') - julianday(created_at) > 0.0035
        """)
    
    @staticmethod
    def get_daily_duel_count(user_id: int) -> int:
        today = datetime.now().strftime('%Y-%m-%d')
        result = db.fetch_one(
            "SELECT count FROM duels WHERE user_id = ? AND date = ?",
            (user_id, today)
        )
        return result["count"] if result else 0
    
    @staticmethod
    def increment_duel_count(user_id: int, won: bool = False):
        today = datetime.now().strftime('%Y-%m-%d')
        db.execute("""
            INSERT INTO duels (user_id, date, count, wins)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET
                count = count + 1,
                wins = wins + ?
        """, (user_id, today, 1 if won else 0, 1 if won else 0))

# ==================== СЕМЕЙНЫЕ ФУНКЦИИ ====================
def get_family_by_member(user_id: int) -> Optional[dict]:
    families = db.fetch_all("SELECT * FROM families")
    
    for family in families:
        if family["spouse1_id"] == user_id or family["spouse2_id"] == user_id:
            return {
                "family_id": family["family_id"],
                "spouse1_id": family["spouse1_id"],
                "spouse2_id": family["spouse2_id"],
                "children": json.loads(family["children"] or "[]"),
                "level": family["level"],
                "family_name": family["family_name"]
            }
        
        try:
            children = json.loads(family["children"] or "[]")
            for child in children:
                if child["id"] == user_id:
                    return {
                        "family_id": family["family_id"],
                        "spouse1_id": family["spouse1_id"],
                        "spouse2_id": family["spouse2_id"],
                        "children": children,
                        "level": family["level"],
                        "family_name": family["family_name"]
                    }
        except:
            pass
    
    return None

def create_family(spouse1_id: int, spouse2_id: int, family_name: str) -> int:
    return db.execute(
        "INSERT INTO families (spouse1_id, spouse2_id, family_name, children) VALUES (?, ?, ?, ?)",
        (spouse1_id, spouse2_id, family_name, '[]')
    )

def update_family(family_id: int, data: dict):
    db.execute("""
        UPDATE families SET
            spouse1_id = ?,
            spouse2_id = ?,
            children = ?,
            level = ?,
            family_name = ?
        WHERE family_id = ?
    """, (
        data["spouse1_id"], data["spouse2_id"],
        json.dumps(data["children"]),
        data["level"], data["family_name"], family_id
    ))

def get_family(family_id: int) -> Optional[dict]:
    result = db.fetch_one("SELECT * FROM families WHERE family_id = ?", (family_id,))
    if not result:
        return None
    return {
        "family_id": result["family_id"],
        "spouse1_id": result["spouse1_id"],
        "spouse2_id": result["spouse2_id"],
        "children": json.loads(result["children"] or "[]"),
        "level": result["level"],
        "family_name": result["family_name"]
    }

def add_child_to_family(family_id: int, child_id: int, child_name: str, child_type: str) -> bool:
    family = get_family(family_id)
    if not family:
        return False
    
    if len(family["children"]) >= 10:
        return False
    
    for child in family["children"]:
        if child["id"] == child_id:
            return False
    
    family["children"].append({
        "id": child_id,
        "name": child_name,
        "type": child_type,
        "added_at": datetime.now().isoformat()
    })
    
    update_family(family_id, family)
    return True

def remove_child_from_family(family_id: int, child_id: int) -> bool:
    family = get_family(family_id)
    if not family:
        return False
    
    for i, child in enumerate(family["children"]):
        if child["id"] == child_id:
            del family["children"][i]
            update_family(family_id, family)
            return True
    
    return False

def upgrade_family(family_id: int) -> bool:
    family = get_family(family_id)
    if not family or family["level"] >= 5:
        return False
    
    current_level = family["level"]
    cost = FAMILY_UPGRADE_COSTS.get(current_level + 1, 50000)
    spouse1_balance = get_balance(family["spouse1_id"])
    spouse2_balance = get_balance(family["spouse2_id"])
    total_balance = spouse1_balance + spouse2_balance
    
    if total_balance < cost:
        return False
    
    half_cost = cost // 2
    if spouse1_balance >= half_cost and spouse2_balance >= half_cost:
        add_balance(family["spouse1_id"], -half_cost)
        add_balance(family["spouse2_id"], -half_cost)
    elif spouse1_balance >= cost:
        add_balance(family["spouse1_id"], -cost)
    elif spouse2_balance >= cost:
        add_balance(family["spouse2_id"], -cost)
    else:
        add_balance(family["spouse1_id"], -spouse1_balance)
        add_balance(family["spouse2_id"], -(cost - spouse1_balance))
    
    family["level"] += 1
    update_family(family_id, family)
    return True

def create_marriage_proposal(from_id: int, to_id: int, proposal_text: str) -> int:
    return db.execute(
        "INSERT INTO marriage_proposals (from_id, to_id, proposal_text, timestamp) VALUES (?, ?, ?, ?)",
        (from_id, to_id, proposal_text, datetime.now().isoformat())
    )

def get_marriage_proposal(proposal_id: int) -> Optional[dict]:
    result = db.fetch_one("SELECT * FROM marriage_proposals WHERE proposal_id = ?", (proposal_id,))
    if not result:
        return None
    return {
        "proposal_id": result["proposal_id"],
        "from_id": result["from_id"],
        "to_id": result["to_id"],
        "proposal_text": result["proposal_text"],
        "timestamp": result["timestamp"]
    }

def delete_marriage_proposal(proposal_id: int):
    db.execute("DELETE FROM marriage_proposals WHERE proposal_id = ?", (proposal_id,))

def send_gift(from_user_id: int, to_user_id: int, gift_type: str, message: str):
    db.execute(
        "INSERT INTO gifts (from_user_id, to_user_id, gift_type, message, timestamp) VALUES (?, ?, ?, ?, ?)",
        (from_user_id, to_user_id, gift_type, message, datetime.now().isoformat())
    )
    log_action(from_user_id, "send_gift", f"To: {to_user_id}, Type: {gift_type}")

def get_user_gifts(user_id: int) -> List[dict]:
    results = db.fetch_all("SELECT * FROM gifts WHERE to_user_id = ? ORDER BY timestamp DESC", (user_id,))
    return [{
        "gift_id": r["gift_id"],
        "from_user_id": r["from_user_id"],
        "to_user_id": r["to_user_id"],
        "gift_type": r["gift_type"],
        "message": r["message"],
        "timestamp": r["timestamp"]
    } for r in results]

def get_gift_stats() -> List[dict]:
    results = db.fetch_all("SELECT to_user_id, COUNT(*) as gift_count FROM gifts GROUP BY to_user_id ORDER BY gift_count DESC LIMIT 10")
    return [{"user_id": r["to_user_id"], "count": r["gift_count"]} for r in results]

def add_confession(confession_text: str):
    db.execute("INSERT INTO confessions (confession_text, timestamp) VALUES (?, ?)",
               (confession_text, datetime.now().isoformat()))

def get_bieber_catch_stats(user_id: int) -> dict:
    result = db.fetch_one("SELECT catches, fake_catches FROM bieber_catch WHERE user_id = ?", (user_id,))
    if not result:
        return {"catches": 0, "fake_catches": 0}
    return {"catches": result["catches"], "fake_catches": result["fake_catches"]}

def update_bieber_catch_stats(user_id: int, real_catch: bool = True):
    if real_catch:
        db.execute("INSERT OR IGNORE INTO bieber_catch (user_id, catches) VALUES (?, 0)", (user_id,))
        db.execute("UPDATE bieber_catch SET catches = catches + 1 WHERE user_id = ?", (user_id,))
    else:
        db.execute("INSERT OR IGNORE INTO bieber_catch (user_id, fake_catches) VALUES (?, 0)", (user_id,))
        db.execute("UPDATE bieber_catch SET fake_catches = fake_catches + 1 WHERE user_id = ?", (user_id,))
    log_action(user_id, "bieber_catch", f"Real: {real_catch}")

# ==================== СОБЫТИЕ НА СООБЩЕНИЯ ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    content_lower = message.content.lower()
    for keyword, emoji in AUTO_REACTIONS.items():
        if keyword in content_lower:
            try:
                await message.add_reaction(emoji)
            except:
                pass
    
    await bot.process_commands(message)

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================
@bot.command(name='молиться')
@in_command_channel()
@cooldown("pray")
@add_command_reaction("молиться")
async def pray(ctx):
    loading = LoadingAnimation(ctx, "Молитва обрабатывается", "🙏")
    await loading.start()
    
    try:
        user_id = ctx.author.id
        work = random.choice(WORK_OPTIONS)
        base_reward = work["reward"]
        
        # Получаем бонус от артефактов
        user_data = db.fetch_one("SELECT artifacts FROM users WHERE user_id = ?", (user_id,))
        bonus_percent = 0
        
        if user_data and user_data["artifacts"]:
            try:
                artifacts = json.loads(user_data["artifacts"])
                for artifact_id in artifacts:
                    if artifact_id in SHOP_ITEMS:
                        artifact = SHOP_ITEMS[artifact_id]
                        if artifact["type"] in ["permanent", "legendary"]:
                            if artifact["effect"]["command"] == "pray":
                                bonus_percent += artifact["effect"]["bonus"]
            except:
                pass
        
        bonus_percent = min(bonus_percent, 300)
        bonus = int(base_reward * bonus_percent / 100)
        total_reward = base_reward + bonus
        
        # ============ КЛЮЧЕВАЯ ЧАСТЬ (как в тесте) ============
        # Проверяем существует ли пользователь
        user_exists = db.fetch_one("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        
        if not user_exists:
            # Создаём пользователя
            db.execute("""
                INSERT INTO users (user_id, balance, artifacts, cards, completed_combos, created_at) 
                VALUES (?, 0, '{}', '[]', '[]', ?)
            """, (user_id, datetime.now().isoformat()))
        
        # Обновляем баланс (как в успешном тесте)
        db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (total_reward, user_id))
        
        # Получаем новый баланс
        result = db.fetch_one("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        new_balance = result["balance"] if result else 0
        # =====================================================
        
        print(f"[PRAY] {user_id}: +{total_reward} -> {new_balance}")
        
        await try_drop_card(ctx, "молиться")
        await check_combos(ctx)
        
        embed = create_embed(
            title=f"{EMOJIS['pray']} Вы помолились Биберу!",
            description=f"**{work['name']}**\n\n"
                       f"Получено: +{total_reward} {EMOJIS['bibsy']}\n"
                       f"Баланс: {new_balance} {EMOJIS['bibsy']}",
            color=discord.Color.green(),
            image="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaHVhcnFnMmVxYmxzdXVnYTZ6Zjd5dm8xa29oeTdteWZhcnZlbzJ5aiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/t9oU3BYnF7fGDtl5PJ/giphy.gif",
            footer="Твой вклад в культуру Бибера"
        )
        
        if bonus > 0:
            embed.add_field(name="✨ Бонус от артефактов", value=f"+{bonus} {EMOJIS['bibsy']}", inline=False)
        
        await loading.stop(True, "Молитва принята!")
        await ctx.send(embed=embed)
        log_action(ctx.author.id, "pray", f"Work: {work['name']}, Reward: {total_reward}")
        
    except Exception as e:
        print(f"[ERROR] pray: {e}")
        import traceback
        traceback.print_exc()
        await loading.stop(False, f"Ошибка: {str(e)[:50]}")

@bot.command(name='проповедь')
@in_command_channel()
@cooldown("sermon")
@add_command_reaction("проповедь")
async def sermon(ctx):
    loading = LoadingAnimation(ctx, "Проповедь подготавливается", "📖")
    await loading.start()
    
    try:
        user_id = ctx.author.id
        sermon_data = random.choice(SERMONS)
        base_reward = sermon_data["reward"]
        
        # Получаем бонус от артефактов
        user_data = db.fetch_one("SELECT artifacts FROM users WHERE user_id = ?", (user_id,))
        bonus_percent = 0
        
        if user_data and user_data["artifacts"]:
            try:
                artifacts = json.loads(user_data["artifacts"])
                for artifact_id in artifacts:
                    if artifact_id in SHOP_ITEMS:
                        artifact = SHOP_ITEMS[artifact_id]
                        if artifact["type"] in ["permanent", "legendary"]:
                            if artifact["effect"]["command"] == "sermon":
                                bonus_percent += artifact["effect"]["bonus"]
            except:
                pass
        
        bonus_percent = min(bonus_percent, 300)
        bonus = int(base_reward * bonus_percent / 100)
        total_reward = base_reward + bonus
        
        # Обновляем баланс
        user_exists = db.fetch_one("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not user_exists:
            db.execute("""
                INSERT INTO users (user_id, balance, artifacts, cards, completed_combos, created_at) 
                VALUES (?, 0, '{}', '[]', '[]', ?)
            """, (user_id, datetime.now().isoformat()))
        
        db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (total_reward, user_id))
        
        result = db.fetch_one("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        new_balance = result["balance"] if result else 0
        
        print(f"[SERMON] {user_id}: +{total_reward} -> {new_balance}")
        
        await try_drop_card(ctx, "проповедь")
        await check_combos(ctx)
        
        embed = create_embed(
            title=f"{EMOJIS['sermon']} Проповедь о Бибере",
            description=f"*{sermon_data['text']}*\n\n"
                       f"Заработано: +{total_reward} {EMOJIS['bibsy']}\n"
                       f"Баланс: {new_balance} {EMOJIS['bibsy']}",
            color=discord.Color.blue(),
            image="https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExenlsNTgyb2o1cnRjYWJ1ZW1xNDlwdm9qdmtiZGJ5OW83c2oxYTM4dSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/rkJSfl4NQQvd0ZQiiR/giphy.gif",
            footer="Слово Бибера"
        )
        
        if bonus > 0:
            embed.add_field(name="✨ Бонус от артефактов", value=f"+{bonus} {EMOJIS['bibsy']}", inline=False)
        
        await loading.stop(True, "Проповедь завершена!")
        await ctx.send(embed=embed)
        log_action(ctx.author.id, "sermon", f"Reward: {total_reward}")
        
    except Exception as e:
        print(f"[ERROR] sermon: {e}")
        import traceback
        traceback.print_exc()
        await loading.stop(False, f"Ошибка: {str(e)[:50]}")

@bot.command(name='экстаз')
@in_command_channel()
@cooldown("ecstasy")
@add_command_reaction("экстаз")
async def ecstasy(ctx):
    loading = LoadingAnimation(ctx, "Достижение экстаза", "✨")
    await loading.start()
    
    try:
        user_id = ctx.author.id
        
        # Проверяем существование пользователя
        user_exists = db.fetch_one("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not user_exists:
            db.execute("""
                INSERT INTO users (user_id, balance, artifacts, cards, completed_combos, created_at) 
                VALUES (?, 0, '{}', '[]', '[]', ?)
            """, (user_id, datetime.now().isoformat()))
        
        if random.random() <= 0.05:
            reward = 3500
            
            db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, user_id))
            result = db.fetch_one("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            new_balance = result["balance"] if result else 0
            
            print(f"[ECSTASY] {user_id}: +{reward} -> {new_balance}")
            
            outcomes = [
                "Ты запел «Love Yourself» в акапелле. Голос дрожал, но автотюн спустился с небес.",
                "Ты произнёс: \"Baby, baby, baby, ooooh.\" И сам Бибер в тени сделал лайк.",
                "Ты произнёс: «We were born to be somebody...» Люди не выдержали. Ты стоял в центре лужи из слёз и фантиков."
            ]
            
            await try_drop_card(ctx, "экстаз")
            await check_combos(ctx)
            
            embed = create_embed(
                title=f"{EMOJIS['win']} ЭКСТАЗ!",
                description=f"{random.choice(outcomes)}\n\nПолучено: +{reward} {EMOJIS['bibsy']}\nБаланс: {new_balance} {EMOJIS['bibsy']}",
                color=discord.Color.gold(),
                image="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExeWU0M3dtYjI0ZTYxMWtzeXlldWFpYnJncDY3c3M4a3hxdmlnYndhbiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/nCc4eOd8npO1VNc5ca/giphy.gif",
                footer="Божественное откровение"
            )
            
            await loading.stop(True, "Экстаз достигнут!")
            await ctx.send(embed=embed)
            log_action(ctx.author.id, "ecstasy", f"Success, Reward: {reward}")
        else:
            penalty = 200
            
            db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (penalty, user_id))
            result = db.fetch_one("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            new_balance = result["balance"] if result else 0
            
            print(f"[ECSTASY] {user_id}: -{penalty} -> {new_balance}")
            
            embed = create_embed(
                title=f"{EMOJIS['lose']} Неудача!",
                description=f"Вы попытались достичь экстаза, но потерпели неудачу.\n\nПотеряно: -{penalty} {EMOJIS['bibsy']}\nБаланс: {new_balance} {EMOJIS['bibsy']}",
                color=discord.Color.red(),
                image="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExeTJtejhwa2dqNHk0NzQyZ3oweDI2a2lzbGZ5Mnk4YTVhaWs5MmlsMiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/DyfH7ypKAMUX00uywk/giphy.gif"
            )
            
            await loading.stop(False, "Экстаз не удался")
            await ctx.send(embed=embed)
            log_action(ctx.author.id, "ecstasy", f"Fail, Penalty: {penalty}")
            
    except Exception as e:
        print(f"[ERROR] ecstasy: {e}")
        import traceback
        traceback.print_exc()
        await loading.stop(False, f"Ошибка: {str(e)[:50]}")

@bot.command(name='покаяться')
@in_command_channel()
@cooldown("repent")
@add_command_reaction("покаяться")
async def repent(ctx):
    loading = LoadingAnimation(ctx, "Покаяние", "😢")
    await loading.start()
    
    try:
        user_id = ctx.author.id
        
        # Проверяем существование пользователя
        user_exists = db.fetch_one("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not user_exists:
            db.execute("""
                INSERT INTO users (user_id, balance, artifacts, cards, completed_combos, created_at) 
                VALUES (?, 0, '{}', '[]', '[]', ?)
            """, (user_id, datetime.now().isoformat()))
        
        if random.random() <= 0.5:
            bonuses = [
                {"text": "Ты покаялся в том, что слушал другого исполнителя... но вовремя вернулся.", "reward": 100},
                {"text": "Ты признался, что однажды назвал его \"попсой\", но внутри плакал.", "reward": 70},
                {"text": "Ты удалил все каверы на его песни. Мир стал чище.", "reward": 120},
                {"text": "Ты разослал 10 людям \"Sorry\" как миссионер.", "reward": 90},
                {"text": "Ты отстоял Бибера в споре с незнающим. Громко. И с матами.", "reward": 80}
            ]
            bonus = random.choice(bonuses)
            
            db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (bonus["reward"], user_id))
            result = db.fetch_one("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            new_balance = result["balance"] if result else 0
            
            print(f"[REPENT] {user_id}: +{bonus['reward']} -> {new_balance}")
            
            await try_drop_card(ctx, "покаяться")
            await check_combos(ctx)
            
            embed = create_embed(
                title=f"{EMOJIS['win']} Покаяние принято!",
                description=f"{bonus['text']}\n\nПолучено: +{bonus['reward']} {EMOJIS['bibsy']}\nБаланс: {new_balance} {EMOJIS['bibsy']}",
                color=discord.Color.green()
            )
            
            await loading.stop(True, "Ты прощен!")
            await ctx.send(embed=embed)
            log_action(ctx.author.id, "repent", f"Success, Reward: {bonus['reward']}")
        else:
            penalties = [
                {"text": "Ты тайком слушал Селену. И тебе понравилось.", "penalty": 50},
                {"text": "Ты сказал \"одна и та же песня\", хотя это был ремикс.", "penalty": 30},
                {"text": "Ты проигнорировал сторис Бибера. Он заметил.", "penalty": 40},
                {"text": "Ты произнёс: \"Когда-то он был лучше...\"", "penalty": 80},
                {"text": "Ты забыл дату выхода \"Purpose\". Это непростительно.", "penalty": 80}
            ]
            penalty = random.choice(penalties)
            
            db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (penalty["penalty"], user_id))
            result = db.fetch_one("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            new_balance = result["balance"] if result else 0
            
            print(f"[REPENT] {user_id}: -{penalty['penalty']} -> {new_balance}")
            
            embed = create_embed(
                title=f"{EMOJIS['lose']} Покаяние не принято!",
                description=f"{penalty['text']}\n\nПотеряно: -{penalty['penalty']} {EMOJIS['bibsy']}\nБаланс: {new_balance} {EMOJIS['bibsy']}",
                color=discord.Color.red()
            )
            
            await loading.stop(False, "Покаяние отклонено")
            await ctx.send(embed=embed)
            log_action(ctx.author.id, "repent", f"Fail, Penalty: {penalty['penalty']}")
            
    except Exception as e:
        print(f"[ERROR] repent: {e}")
        import traceback
        traceback.print_exc()
        await loading.stop(False, f"Ошибка: {str(e)[:50]}")

# ==================== КОЛЛЕКЦИОННЫЕ КАРТОЧКИ ====================
@bot.command(name='коллекция')
@in_command_channel()
async def show_collection(ctx, member: discord.Member = None):
    """Показать коллекцию карточек пользователя"""
    target = member or ctx.author
    collection = get_user_cards_collection(target.id)
    
    # Проверяем кулдаун для показа
    user_id = target.id
    cooldown_text = ""
    
    if user_id in user_last_card_drop:
        time_since_last = (datetime.now() - user_last_card_drop[user_id]).total_seconds()
        if time_since_last < CARD_DROP_COOLDOWN:
            remaining = CARD_DROP_COOLDOWN - time_since_last
            remaining_hours = int(remaining // 3600)
            remaining_minutes = int((remaining % 3600) // 60)
            cooldown_text = f"\n\n⏳ Следующая карта через: {remaining_hours}ч {remaining_minutes}м"
    
    percent = int(collection['total'] / collection['total_possible'] * 100) if collection['total_possible'] > 0 else 0
    
    embed = create_embed(
        title=f"{EMOJIS['card']} Коллекция карт {target.display_name}",
        description=f"Собрано **{collection['total']}** из **{collection['total_possible']}** карт ({percent}%){cooldown_text}",
        color=discord.Color.gold(),
        footer="Собирай все карты Бибера! Новая карта раз в 12 часов"
    )
    
    # Добавляем поля по редкости
    rarities = ["mythic", "legendary", "epic", "rare", "common"]
    rarity_names = {
        "mythic": "🌟 Мифические",
        "legendary": "👑 Легендарные", 
        "epic": "⚡ Эпические",
        "rare": "💎 Редкие",
        "common": "📦 Обычные"
    }
    rarity_emojis = {
        "mythic": "🌟",
        "legendary": "👑",
        "epic": "⚡",
        "rare": "💎",
        "common": "📦"
    }
    
    for rarity in rarities:
        if collection[rarity]:
            cards_list = []
            for card_id in collection[rarity]:
                card = COLLECTIBLE_CARDS[card_id]
                cards_list.append(f"{card['emoji']} {card['name']}")
            
            embed.add_field(
                name=f"{rarity_emojis[rarity]} {rarity_names[rarity]} ({len(collection[rarity])})",
                value="\n".join(cards_list[:15]) + (f"\n... и еще {len(cards_list) - 15}" if len(cards_list) > 15 else ""),
                inline=False
            )
    
    # Если коллекция полная
    if collection['total'] == collection['total_possible']:
        embed.description += "\n\n🎉 **ПОЛНАЯ КОЛЛЕКЦИЯ!** 🎉\nТы настоящий коллекционер!"
        embed.color = discord.Color.magenta()
    
    await ctx.send(embed=embed)

@bot.command(name='картакд')
@in_command_channel()
async def card_cooldown(ctx):
    """Показать, через сколько выпадет следующая карта"""
    user_id = ctx.author.id
    
    if user_id not in user_last_card_drop:
        embed = create_embed(
            title="🎴 Кулдаун карт",
            description="У вас **нет кулдауна**! Следующая карта может выпасть в любой момент!\n\n"
                       f"📊 Шансы выпадения:\n"
                       f"• !молиться / !проповедь: 8%\n"
                       f"• !экстаз: 5%\n"
                       f"• !покаяться: 3%\n"
                       f"• !дуэль: 4%\n"
                       f"• !подарок: 2%",
            color=discord.Color.green(),
            footer="После выпадения карты будет кулдаун 12 часов"
        )
        await ctx.send(embed=embed)
        return
    
    time_since_last = (datetime.now() - user_last_card_drop[user_id]).total_seconds()
    
    if time_since_last >= CARD_DROP_COOLDOWN:
        embed = create_embed(
            title="🎴 Кулдаун карт",
            description="✅ Кулдаун **прошел**! Следующая карта может выпасть в любой момент!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return
    
    remaining = CARD_DROP_COOLDOWN - time_since_last
    remaining_hours = int(remaining // 3600)
    remaining_minutes = int((remaining % 3600) // 60)
    remaining_seconds = int(remaining % 60)
    
    # Время, когда можно будет получить карту
    next_drop_time = user_last_card_drop[user_id] + timedelta(seconds=CARD_DROP_COOLDOWN)
    
    embed = create_embed(
        title="⏳ Кулдаун карт",
        description=f"Следующая карта выпадет через:\n"
                   f"**{remaining_hours}ч {remaining_minutes}м {remaining_seconds}с**\n\n"
                   f"📅 Можно будет получить: **{next_drop_time.strftime('%H:%M %d.%m.%Y')}**",
        color=discord.Color.gold(),
        footer="После выпадения карты кулдаун обновится"
    )
    
    await ctx.send(embed=embed)

@bot.command(name='шансыкарт')
@in_command_channel()
async def card_chances(ctx):
    """Показать шансы выпадения карт"""
    embed = create_embed(
        title="🎴 Шансы выпадения карт",
        description="**Кулдаун: 12 часов** после получения карты",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="🙏 Молитва / 📖 Проповедь",
        value="**8%** шанс\nКулдаун карт: 12 часов",
        inline=True
    )
    embed.add_field(
        name="✨ Экстаз",
        value="**5%** шанс\nКулдаун карт: 12 часов",
        inline=True
    )
    embed.add_field(
        name="😢 Покаяться",
        value="**3%** шанс\nКулдаун карт: 12 часов",
        inline=True
    )
    embed.add_field(
        name="⚔️ Дуэль",
        value="**4%** шанс (при победе)\nКулдаун карт: 12 часов",
        inline=True
    )
    embed.add_field(
        name="🎁 Подарок",
        value="**2%** шанс\nКулдаун карт: 12 часов",
        inline=True
    )
    
    embed.add_field(
        name="🎴 Редкость карт",
        value="📦 **Обычные** (baby_jb): 30%\n"
              "💎 **Редкие** (purpose_jb, christmas): 35%\n"
              "⚡ **Эпические** (changes_jb, acoustic): 25%\n"
              "👑 **Легендарные** (justice_jb, demon): 9%\n"
              "🌟 **Мифические** (ghost, angel): 3%",
        inline=False
    )
    
    embed.add_field(
        name="💡 Совет",
        value="Используйте `!картакд` чтобы узнать, через сколько выпадет следующая карта!",
        inline=False
    )
    
    await ctx.send(embed=embed)

# ==================== ПЕРСОНАЛИЗИРОВАННЫЕ ПОЗДРАВЛЕНИЯ ====================
@bot.command(name='комплимент')
@in_command_channel()
async def compliment(ctx, member: discord.Member = None):
    target = member or ctx.author
    balance = get_balance(target.id)
    
    if balance >= 10000:
        template = random.choice(PERSONALIZED_COMPLIMENTS["balance_milestone"])
        compliment_text = template.format(balance=balance, emoji=EMOJIS["bibsy"], name=target.display_name)
    else:
        template = random.choice(PERSONALIZED_COMPLIMENTS["random"])
        compliment_text = template.format(name=target.display_name, role=random.choice(["герой", "легенда", "звезда", "фанат года"]))
    
    embed = create_embed(
        title="💝 Персональный комплимент",
        description=compliment_text,
        color=discord.Color.pink(),
        author=target,
        footer="Бибер тебя заметил!"
    )
    
    await ctx.send(embed=embed)

# ==================== ПЕРЕДАЧА ДЕНЕГ ====================
@bot.command(name='передать-деньги')
@in_command_channel()
@add_command_reaction("передать-деньги")
async def transfer_money(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        embed = create_embed("Ошибка", "Сумма должна быть положительной!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if member == ctx.author:
        embed = create_embed("Ошибка", "Нельзя передавать деньги самому себе!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    sender_balance = get_balance(ctx.author.id)
    fee = int(amount * TRANSFER_FEE)
    total_cost = amount + fee
    
    if sender_balance < total_cost:
        embed = create_embed(
            "Недостаточно средств",
            f"Нужно: {total_cost} {EMOJIS['bibsy']} (включая комиссию {fee})\nУ вас: {sender_balance} {EMOJIS['bibsy']}",
            discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    new_sender_balance = add_balance(ctx.author.id, -total_cost)
    new_target_balance = add_balance(member.id, amount)
    
    embed = create_embed(
        "Успешный перевод!",
        f"{ctx.author.mention} передал {member.mention} {amount} {EMOJIS['bibsy']}\n"
        f"Комиссия: {fee} {EMOJIS['bibsy']}\n\n"
        f"Ваш баланс: {new_sender_balance} {EMOJIS['bibsy']}",
        discord.Color.green()
    )
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "transfer", f"To: {member.id}, Amount: {amount}, Fee: {fee}")

# ==================== СЕМЕЙНЫЕ КОМАНДЫ ====================
@bot.command(name='предложить')
@in_command_channel()
@cooldown("proposal")
@add_command_reaction("предложить")
async def propose(ctx, member: discord.Member, *, proposal_text: str):
    if member == ctx.author:
        await ctx.send(embed=create_embed("Ошибка", "Нельзя сделать предложение самому себе!", discord.Color.red()))
        return
    
    if get_family_by_member(ctx.author.id):
        await ctx.send(embed=create_embed("Ошибка", "Вы уже состоите в семье!", discord.Color.red()))
        return
    
    if get_family_by_member(member.id):
        await ctx.send(embed=create_embed("Ошибка", "Этот пользователь уже состоит в семье!", discord.Color.red()))
        return
    
    proposal_id = create_marriage_proposal(ctx.author.id, member.id, proposal_text)
    
    embed = create_embed(
        "Предложение руки и сердца!",
        f"{ctx.author.mention} делает предложение {member.mention}:\n\n*{proposal_text}*\n\n"
        f"{member.mention}, чтобы принять предложение, напишите `!принять-предложение {proposal_id}`\n"
        f"Чтобы отказаться, напишите `!отказаться-от-предложения {proposal_id}`",
        discord.Color.pink(),
        image="https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExcXNvbGU5eXVneTRwaWJ5NjFneGw3Mjg0bTJndW5hdmRrMHVnamVnbiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/bNWsjWhlz0CZ6CthyT/giphy.gif"
    )
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "propose", f"To: {member.id}")

@bot.command(name='принять-предложение')
@in_command_channel()
@add_command_reaction("принять-предложение")
async def accept_proposal(ctx, proposal_id: int):
    proposal = get_marriage_proposal(proposal_id)
    if not proposal or proposal["to_id"] != ctx.author.id:
        await ctx.send(embed=create_embed("Ошибка", "Предложение не найдено!", discord.Color.red()))
        return
    
    if get_family_by_member(proposal["from_id"]) or get_family_by_member(proposal["to_id"]):
        await ctx.send(embed=create_embed("Ошибка", "Один из вас уже состоит в семье!", discord.Color.red()))
        delete_marriage_proposal(proposal_id)
        return
    
    from_user = bot.get_user(proposal["from_id"]) or await bot.fetch_user(proposal["from_id"])
    family_name = f"{from_user.display_name} & {ctx.author.display_name}"
    family_id = create_family(proposal["from_id"], proposal["to_id"], family_name)
    delete_marriage_proposal(proposal_id)
    
    embed = create_embed(
        "Новая семья создана!",
        f"Поздравляем {from_user.mention} и {ctx.author.mention}!\nНазвание: {family_name}",
        discord.Color.green()
    )
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "accept_proposal", f"Family: {family_id}")

@bot.command(name='отказаться-от-предложения')
@in_command_channel()
@add_command_reaction("отказаться-от-предложения")
async def reject_proposal(ctx, proposal_id: int):
    proposal = get_marriage_proposal(proposal_id)
    if not proposal or proposal["to_id"] != ctx.author.id:
        await ctx.send(embed=create_embed("Ошибка", "Предложение не найдено!", discord.Color.red()))
        return
    
    delete_marriage_proposal(proposal_id)
    from_user = bot.get_user(proposal["from_id"]) or await bot.fetch_user(proposal["from_id"])
    
    embed = create_embed(
        "Предложение отклонено",
        f"{ctx.author.mention} отклонил предложение от {from_user.mention}.",
        discord.Color.orange()
    )
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "reject_proposal", f"From: {proposal['from_id']}")

@bot.command(name='моясемья')
@in_command_channel()
async def my_family(ctx):
    family = get_family_by_member(ctx.author.id)
    if not family:
        await ctx.send(embed=create_embed("Ошибка", "Вы не состоите в семье!", discord.Color.red()))
        return
    
    spouse1 = bot.get_user(family["spouse1_id"]) or await bot.fetch_user(family["spouse1_id"])
    spouse2 = bot.get_user(family["spouse2_id"]) or await bot.fetch_user(family["spouse2_id"])
    
    children_text = []
    for child in family["children"]:
        try:
            child_user = bot.get_user(child["id"]) or await bot.fetch_user(child["id"])
            child_type = "👦 Сын" if child["type"] == "son" else "👧 Дочь"
            children_text.append(f"{child_type} {child_user.mention} ({child['name']})")
        except:
            children_text.append(f"👶 {child['name']} (ID: {child['id']})")
    
    current_bonus = FAMILY_HOURLY_BONUSES[family["level"]]
    
    embed = create_embed(
        title=f"👪 {family['family_name']}",
        description=f"Уровень: {family['level']} | Бонус: {current_bonus} {EMOJIS['bibsy']}/час",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="💑 Супруги", value=f"{spouse1.mention} и {spouse2.mention}", inline=False)
    
    if children_text:
        embed.add_field(name=f"👶 Дети ({len(family['children'])}/10)", value="\n".join(children_text), inline=False)
    else:
        embed.add_field(name="👶 Дети", value="Пока нет детей", inline=False)
    
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "view_family")

@bot.command(name='добавитьребенка')
@in_command_channel()
@add_command_reaction("добавитьребенка")
async def add_child(ctx, member: discord.Member, child_name: str, child_type: str = "сын"):
    family = get_family_by_member(ctx.author.id)
    if not family or ctx.author.id not in [family["spouse1_id"], family["spouse2_id"]]:
        embed = create_embed("❌ Ошибка", "Только супруги могут добавлять детей!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if get_family_by_member(member.id):
        embed = create_embed("❌ Ошибка", "Этот пользователь уже состоит в семье!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    child_type_en = "son" if child_type.lower() in ["сын", "парень", "мальчик", "son"] else "daughter"
    
    if len(family["children"]) >= 10:
        embed = create_embed("❌ Ошибка", "В семье уже 10 детей! Нельзя добавить больше.", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    success = add_child_to_family(family["family_id"], member.id, child_name, child_type_en)
    if not success:
        embed = create_embed("❌ Ошибка", "Не удалось добавить ребенка! Возможно, он уже в семье.", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    bonus = 500
    add_balance(ctx.author.id, bonus)
    add_balance(member.id, bonus)
    
    child_type_display = "сыном" if child_type_en == "son" else "дочерью"
    
    embed = create_embed(
        "✅ Ребенок добавлен!",
        f"{member.mention} стал {child_type_display} семьи **{family['family_name']}**!\n\n"
        f"Имя: {child_name}\n"
        f"Всего детей: {len(family['children'])}/10\n\n"
        f"🎉 Бонус: +{bonus} {EMOJIS['bibsy']} обоим родителям!",
        discord.Color.green()
    )
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "add_child", f"Child: {member.id}, Name: {child_name}, Type: {child_type}")

@bot.command(name='исключитьребенка')
@in_command_channel()
@add_command_reaction("исключитьребенка")
async def remove_child(ctx, member: discord.Member):
    family = get_family_by_member(ctx.author.id)
    if not family or ctx.author.id not in [family["spouse1_id"], family["spouse2_id"]]:
        embed = create_embed("❌ Ошибка", "Только супруги могут исключать детей!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    is_child = False
    child_name = ""
    for child in family["children"]:
        if child["id"] == member.id:
            is_child = True
            child_name = child["name"]
            break
    
    if not is_child:
        embed = create_embed("❌ Ошибка", "Этот пользователь не является вашим ребенком!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    success = remove_child_from_family(family["family_id"], member.id)
    if not success:
        embed = create_embed("❌ Ошибка", "Не удалось исключить ребенка!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    embed = create_embed(
        "❌ Ребенок исключен",
        f"{member.mention} ({child_name}) исключен из семьи **{family['family_name']}**!",
        discord.Color.orange()
    )
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "remove_child", f"Child: {member.id}")

@bot.command(name='улучшитьсемью')
@in_command_channel()
@add_command_reaction("улучшитьсемью")
async def upgrade_family_cmd(ctx):
    family = get_family_by_member(ctx.author.id)
    if not family or ctx.author.id not in [family["spouse1_id"], family["spouse2_id"]]:
        embed = create_embed("❌ Ошибка", "Только супруги могут улучшать семью!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if family["level"] >= 5:
        embed = create_embed("❌ Ошибка", "Максимальный уровень семьи (5)!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if not upgrade_family(family["family_id"]):
        embed = create_embed("❌ Ошибка", "Недостаточно средств у семьи!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    family = get_family(family["family_id"])
    embed = create_embed(
        "✅ Семья улучшена!",
        f"Уровень: {family['level']}\nБонус: {FAMILY_HOURLY_BONUSES[family['level']]} {EMOJIS['bibsy']}/час",
        discord.Color.green()
    )
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "upgrade_family", f"Level: {family['level']}")

@bot.command(name='дети')
@in_command_channel()
async def list_children(ctx):
    family = get_family_by_member(ctx.author.id)
    if not family:
        embed = create_embed("❌ Ошибка", "Вы не состоите в семье!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if not family["children"]:
        embed = create_embed("👶 Дети", "В семье пока нет детей", discord.Color.blue())
        await ctx.send(embed=embed)
        return
    
    embed = create_embed(
        title=f"👶 Дети семьи {family['family_name']}",
        description=f"Всего детей: {len(family['children'])}/10",
        color=discord.Color.blue()
    )
    
    for i, child in enumerate(family["children"], 1):
        try:
            child_user = bot.get_user(child["id"]) or await bot.fetch_user(child["id"])
            child_type = "👦 Сын" if child["type"] == "son" else "👧 Дочь"
            embed.add_field(
                name=f"{i}. {child['name']}",
                value=f"{child_type} | {child_user.mention}\nДобавлен: {child['added_at'][:10]}",
                inline=False
            )
        except:
            embed.add_field(
                name=f"{i}. {child['name']}",
                value=f"ID: {child['id']}\nДобавлен: {child['added_at'][:10]}",
                inline=False
            )
    
    await ctx.send(embed=embed)

@bot.command(name='развестись')
@in_command_channel()
@cooldown("divorce")
@add_command_reaction("развестись")
async def divorce(ctx):
    family = get_family_by_member(ctx.author.id)
    if not family or ctx.author.id not in [family["spouse1_id"], family["spouse2_id"]]:
        await ctx.send(embed=create_embed("Ошибка", "Вы не состоите в браке!", discord.Color.red()))
        return
    
    db.execute("DELETE FROM families WHERE family_id = ?", (family["family_id"],))
    
    spouse = bot.get_user(family["spouse1_id"] if ctx.author.id == family["spouse2_id"] else family["spouse1_id"])
    spouse = spouse or await bot.fetch_user(family["spouse1_id"] if ctx.author.id == family["spouse2_id"] else family["spouse1_id"])
    embed = create_embed("💔 Развод", f"Брак с {spouse.mention} расторгнут!", discord.Color.dark_grey())
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "divorce")

@bot.command(name='выйти-из-семьи')
@in_command_channel()
@add_command_reaction("выйти-из-семьи")
async def leave_family(ctx):
    family = get_family_by_member(ctx.author.id)
    if not family:
        embed = create_embed("Ошибка", "Вы не состоите в семье!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    is_child = False
    for i, child in enumerate(family["children"]):
        if child["id"] == ctx.author.id:
            del family["children"][i]
            is_child = True
            break
    
    if not is_child:
        embed = create_embed("Ошибка", "Только дети могут покидать семью!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    update_family(family["family_id"], family)
    embed = create_embed("✅ Успех", "Вы вышли из семьи!", discord.Color.green())
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "leave_family")

# ==================== МАГАЗИН ====================
@bot.command(name='магазин')
@in_command_channel()
async def shop(ctx):
    embed = create_embed("Магазин артефактов", "", discord.Color.purple())
    
    for item_id, item in SHOP_ITEMS.items():
        if item["type"] in ["permanent", "legendary"]:
            cmd = "молиться" if item["effect"]["command"] == "pray" else "проповедь"
            effect = f"+{item['effect']['bonus']}% к !{cmd}"
        elif item["type"] == "role":
            effect = "Личная роль на сервере"
        elif item["type"] == "tag":
            effect = "Личный тег"
        else:
            effect = "Особый эффект"
        
        embed.add_field(name=f"{item['name']} - {item['price']} {EMOJIS['bibsy']}", value=effect, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='купить')
@in_command_channel()
@add_command_reaction("купить")
async def buy(ctx, *, item_name: str):
    item_id = None
    for key, item in SHOP_ITEMS.items():
        if item["name"].lower() == item_name.lower():
            item_id = key
            break
    
    if not item_id:
        await ctx.send(embed=create_embed("Ошибка", "Товар не найден!", discord.Color.red()))
        return
    
    item = SHOP_ITEMS[item_id]
    user_data = get_user_data(ctx.author.id)
    
    if user_data["balance"] < item["price"]:
        await ctx.send(embed=create_embed("Недостаточно средств", "", discord.Color.red()))
        return
    
    if item["type"] == "role" and user_data["personal_role"]:
        await ctx.send(embed=create_embed("Ошибка", "У вас уже есть личная роль!", discord.Color.red()))
        return
    
    if item["type"] == "tag" and user_data["personal_tag"]:
        await ctx.send(embed=create_embed("Ошибка", "У вас уже есть тег!", discord.Color.red()))
        return
    
    add_balance(ctx.author.id, -item["price"])
    user_data["balance"] = get_balance(ctx.author.id)
    
    if item["type"] in ["permanent", "legendary"]:
        ArtifactManager.add_artifact(ctx.author.id, item_id)
        success_msg = f"Вы купили {item['name']}!"
    elif item["type"] == "role":
        role = await ctx.guild.create_role(name=f"{ctx.author.display_name}", color=discord.Color.random())
        await ctx.author.add_roles(role)
        user_data["personal_role"] = role.id
        update_user_data(ctx.author.id, user_data)
        success_msg = f"Вы купили личную роль {role.mention}!"
    elif item["type"] == "tag":
        user_data["personal_tag"] = ctx.author.name
        update_user_data(ctx.author.id, user_data)
        success_msg = f"Вы купили личный тег!"
    else:
        success_msg = f"Вы купили {item['name']}!"
    
    embed = create_embed("✅ Покупка успешна!", success_msg, discord.Color.green())
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "buy_item", item_id)

@bot.command(name='артефакты')
@in_command_channel()
async def artifacts_cmd(ctx):
    data = get_user_data(ctx.author.id)
    artifacts = data["artifacts"]
    
    if not artifacts:
        embed = create_embed("Нет артефактов", "Посетите магазин!", discord.Color.blue())
        await ctx.send(embed=embed)
        return
    
    embed = create_embed("Ваши артефакты", "", discord.Color.blue())
    for art_id in artifacts:
        if art_id in SHOP_ITEMS:
            item = SHOP_ITEMS[art_id]
            effect = f"+{item['effect']['bonus']}% к !{'молиться' if item['effect']['command'] == 'pray' else 'проповедь'}"
            embed.add_field(name=item['name'], value=effect, inline=False)
    
    await ctx.send(embed=embed)

# ==================== ДУЭЛИ ====================
@bot.command(name='дуэль')
@in_command_channel()
@add_command_reaction("дуэль")
async def duel(ctx, member: discord.Member = None, amount: int = None):
    if not member or not amount:
        embed = create_embed("Использование", "`!дуэль @участник 50-150`", discord.Color.blue())
        await ctx.send(embed=embed)
        return
    
    if not (50 <= amount <= 150):
        embed = create_embed("Ошибка", "Ставка: 50-150 бибсов!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if DuelManager.get_daily_duel_count(ctx.author.id) >= 3:
        embed = create_embed("Лимит", "3 дуэли в день!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if get_balance(ctx.author.id) < amount:
        embed = create_embed("Недостаточно средств", "", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if DuelManager.get_duel(ctx.channel.id):
        embed = create_embed("Ошибка", "Дуэль уже идет в этом канале!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    DuelManager.create_duel(ctx.channel.id, ctx.author.id, member.id, amount)
    
    embed = create_embed(
        "Вызов на дуэль!",
        f"{ctx.author.mention} вызывает {member.mention} на дуэль!\nСтавка: {amount} {EMOJIS['bibsy']}\n\n"
        f"{member.mention}, напишите `!принять` или `!отказаться`",
        discord.Color.gold()
    )
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "duel_start", f"Target: {member.id}")

@bot.command(name='принять')
@in_command_channel()
@add_command_reaction("принять")
async def accept_duel(ctx):
    duel_data = DuelManager.get_duel(ctx.channel.id)
    if not duel_data or ctx.author.id != duel_data["target_id"]:
        await ctx.send(embed=create_embed("Ошибка", "Нет активной дуэли для вас!", discord.Color.red()))
        return
    
    if get_balance(ctx.author.id) < duel_data["amount"]:
        await ctx.send(embed=create_embed("Недостаточно средств", "", discord.Color.red()))
        DuelManager.delete_duel(ctx.channel.id)
        return
    
    DuelManager.accept_duel(ctx.channel.id, ctx.author.id)
    
    embed = create_embed(
        "Дуэль принята!",
        f"{ctx.author.mention} принял вызов!\nОба напишите `!бой` чтобы начать!",
        discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='отказаться')
@in_command_channel()
@add_command_reaction("отказаться")
async def decline_duel(ctx):
    duel_data = DuelManager.get_duel(ctx.channel.id)
    if not duel_data or ctx.author.id not in [duel_data["challenger_id"], duel_data["target_id"]]:
        await ctx.send(embed=create_embed("Ошибка", "Вы не участник дуэли!", discord.Color.red()))
        return
    
    DuelManager.delete_duel(ctx.channel.id)
    embed = create_embed("Дуэль отменена", f"{ctx.author.mention} отказался!", discord.Color.orange())
    await ctx.send(embed=embed)

@bot.command(name='бой')
@in_command_channel()
@add_command_reaction("бой")
async def fight(ctx):
    duel_data = DuelManager.get_duel(ctx.channel.id)
    if not duel_data or not duel_data["accepted"]:
        await ctx.send(embed=create_embed("Ошибка", "Дуэль не принята!", discord.Color.red()))
        return
    
    if ctx.author.id not in [duel_data["challenger_id"], duel_data["target_id"]]:
        await ctx.send(embed=create_embed("Ошибка", "Вы не участник!", discord.Color.red()))
        return
    
    ready_count = DuelManager.add_fighter_ready(ctx.channel.id, ctx.author.id)
    
    if ready_count < 2:
        embed = create_embed("Готов к бою!", f"{ctx.author.mention} готов! Ждем второго...", discord.Color.gold())
        await ctx.send(embed=embed)
        return
    
    challenger = bot.get_user(duel_data["challenger_id"]) or await bot.fetch_user(duel_data["challenger_id"])
    target = bot.get_user(duel_data["target_id"]) or await bot.fetch_user(duel_data["target_id"])
    amount = duel_data["amount"]
    
    add_balance(challenger.id, -amount)
    add_balance(target.id, -amount)
    
    winner = random.choice([challenger, target])
    loser = target if winner == challenger else challenger
    reward = amount * 2
    add_balance(winner.id, reward)
    
    await try_drop_card(ctx, "дуэль")
    
    DuelManager.increment_duel_count(winner.id, True)
    DuelManager.increment_duel_count(loser.id, False)
    DuelManager.delete_duel(ctx.channel.id)
    
    embed = create_embed(
        "Дуэль завершена!",
        f"⚔️ {challenger.mention} vs {target.mention} ⚔️\n\n🏆 Победитель: {winner.mention} получает {reward} {EMOJIS['bibsy']}!",
        discord.Color.green()
    )
    await ctx.send(embed=embed)
    log_action(winner.id, "duel_win", f"Amount: {reward}")

# ==================== ЛОВЛЯ БИБЕРА ====================
class BieberEscapeGame:
    def __init__(self):
        self.active = False
        self.fake = False
        self.channel_id = None
        self.message_id = None
        self.winner = None

bieber_game = BieberEscapeGame()

@bot.command(name='поймать')
@in_command_channel()
@add_command_reaction("поймать")
async def catch_bieber(ctx):
    if not bieber_game.active or ctx.channel.id != bieber_game.channel_id or bieber_game.winner:
        return
    
    bieber_game.winner = ctx.author
    bieber_game.active = False
    
    if bieber_game.fake:
        penalty = random.randint(50, 100)
        new_balance = add_balance(ctx.author.id, -penalty)
        update_bieber_catch_stats(ctx.author.id, False)
        embed = create_embed(
            "🎉 Фейк! 🎉", 
            f"{ctx.author.mention} теряет {penalty} {EMOJIS['bibsy']}!\nБаланс: {new_balance} {EMOJIS['bibsy']}", 
            discord.Color.red()
        )
    else:
        reward = 150
        new_balance = add_balance(ctx.author.id, reward)
        update_bieber_catch_stats(ctx.author.id, True)
        embed = create_embed(
            "⭐ Поймал! ⭐", 
            f"{ctx.author.mention} +{reward} {EMOJIS['bibsy']}!\nБаланс: {new_balance} {EMOJIS['bibsy']}", 
            discord.Color.green()
        )
    
    try:
        msg = await ctx.channel.fetch_message(bieber_game.message_id)
        await msg.edit(embed=embed)
    except:
        await ctx.send(embed=embed)

# ==================== СОЦИАЛЬНЫЕ КОМАНДЫ ====================
@bot.command(name='поцелуй')
@in_command_channel()
@add_command_reaction("поцелуй")
async def kiss(ctx, member: discord.Member):
    if member == ctx.author:
        await ctx.send(embed=create_embed("Ошибка", "Нельзя поцеловать себя!", discord.Color.red()))
        return
    
    context = random.choice(KISS_CONTEXTS)
    embed = create_embed(
        "Поцелуй",
        f"{ctx.author.mention} {context['text']} {member.mention}!",
        discord.Color.pink(),
        image=context['gif']
    )
    await ctx.send(embed=embed)

@bot.command(name='обнять')
@in_command_channel()
@add_command_reaction("обнять")
async def hug(ctx, member: discord.Member):
    if member == ctx.author:
        await ctx.send(embed=create_embed("Ошибка", "Нельзя обнять себя!", discord.Color.red()))
        return
    
    context = random.choice(HUG_CONTEXTS)
    embed = create_embed(
        "Объятия",
        f"{ctx.author.mention} {context['text']} {member.mention}!",
        discord.Color.blue(),
        image=context['gif']
    )
    await ctx.send(embed=embed)

@bot.command(name='ударить')
@in_command_channel()
@add_command_reaction("ударить")
async def hit(ctx, member: discord.Member):
    if member == ctx.author:
        await ctx.send(embed=create_embed("Ошибка", "Нельзя ударить себя!", discord.Color.red()))
        return
    
    context = random.choice(HIT_CONTEXTS)
    embed = create_embed(
        "Удар",
        f"{ctx.author.mention} {context['text']} {member.mention}!",
        discord.Color.orange(),
        image=context['gif']
    )
    await ctx.send(embed=embed)

@bot.command(name='угостить')
@in_command_channel()
@add_command_reaction("угостить")
async def treat(ctx, member: discord.Member):
    if member == ctx.author:
        await ctx.send(embed=create_embed("Ошибка", "Нельзя угостить себя!", discord.Color.red()))
        return
    
    context = random.choice(TREAT_CONTEXTS)
    embed = create_embed(
        "Угощение",
        f"{ctx.author.mention} {context['text']} {member.mention}!",
        discord.Color.green(),
        image=context['gif']
    )
    await ctx.send(embed=embed)

@bot.command(name='занятьсялюбовью')
@in_command_channel()
@add_command_reaction("занятьсялюбовью")
async def make_love(ctx, member: discord.Member):
    if member == ctx.author:
        await ctx.send(embed=create_embed("Ошибка", "Нельзя с самим собой!", discord.Color.red()))
        return
    
    context = random.choice(LOVE_CONTEXTS)
    embed = create_embed(
        "Любовь",
        f"{ctx.author.mention} {context['text']} с {member.mention}!",
        discord.Color.red(),
        image=context['gif']
    )
    await ctx.send(embed=embed)

# ==================== ПОДАРКИ ====================
class GiftView(discord.ui.View):
    def __init__(self, ctx, recipient):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.recipient = recipient
        self.gift_type = None
        self.message_text = None

    @discord.ui.select(
        placeholder="Выберите тип подарка...",
        options=[
            discord.SelectOption(label="Цветы", value="цветы", emoji="💐"),
            discord.SelectOption(label="Плюшевый мишка", value="плюшевый мишка", emoji="🧸"),
            discord.SelectOption(label="Плюшевый зайчик", value="плюшевый зайчик", emoji="🐰"),
            discord.SelectOption(label="Сердечки", value="сердечки", emoji="💖"),
            discord.SelectOption(label="Случайный подарок", value="рандом", emoji="🎁")
        ]
    )
    async def select_gift(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Это меню не для вас!", ephemeral=True)
            return
        
        self.gift_type = select.values[0]
        await interaction.response.send_message(
            f"Вы выбрали: {GIFT_TYPES[self.gift_type]} {self.gift_type}\n\nТеперь введите сообщение для получателя (до 500 символов):",
            ephemeral=True
        )
        
        def check(m):
            return m.author == self.ctx.author and m.channel == self.ctx.channel
        
        try:
            msg = await self.ctx.bot.wait_for('message', timeout=120.0, check=check)
            if len(msg.content) > 500:
                await self.ctx.send("Сообщение слишком длинное! Максимум 500 символов.")
                return
            
            self.message_text = msg.content
            
            balance = get_balance(self.ctx.author.id)
            if balance < GIFT_PRICE:
                await self.ctx.send(f"❌ Недостаточно средств! Нужно {GIFT_PRICE} {EMOJIS['bibsy']}, у вас {balance} {EMOJIS['bibsy']}")
                return
            
            add_balance(self.ctx.author.id, -GIFT_PRICE)
            
            final_gift_type = self.gift_type
            if self.gift_type == "рандом":
                final_gift_type = random.choice([gt for gt in GIFT_TYPES.keys() if gt != "рандом"])
            
            send_gift(self.ctx.author.id, self.recipient.id, final_gift_type, self.message_text)
            
            await try_drop_card(self.ctx, "подарок")
            
            embed = create_embed(
                "Вам подарок!",
                f"{self.ctx.author.mention} подарил вам {GIFT_TYPES[final_gift_type]} **{final_gift_type}**!",
                discord.Color.gold(),
                footer="Используйте !моиподарки чтобы посмотреть все ваши подарки"
            )
            embed.add_field(name="💌 Сообщение:", value=self.message_text, inline=False)
            
            try:
                await self.recipient.send(embed=embed)
                await self.ctx.send(f"✅ Подарок успешно отправлен {self.recipient.mention}!")
            except:
                await self.ctx.send(f"✅ Подарок отправлен {self.recipient.mention}, но не удалось отправить уведомление в ЛС.")
            
            self.stop()
            
        except asyncio.TimeoutError:
            await self.ctx.send("Время вышло! Попробуйте снова.")

@bot.command(name='подарок')
@in_command_channel()
@add_command_reaction("подарок")
async def send_gift_command(ctx, member: discord.Member):
    if member == ctx.author:
        await ctx.send(embed=create_embed("Ошибка", "Нельзя подарить себе!", discord.Color.red()))
        return
    
    if get_balance(ctx.author.id) < GIFT_PRICE:
        await ctx.send(embed=create_embed("Недостаточно средств", f"Нужно {GIFT_PRICE} {EMOJIS['bibsy']}", discord.Color.red()))
        return
    
    view = GiftView(ctx, member)
    await ctx.send(f"Вы собираетесь подарить подарок {member.mention} за {GIFT_PRICE} {EMOJIS['bibsy']}", view=view)

@bot.command(name='моиподарки')
@in_command_channel()
async def my_gifts(ctx):
    gifts = get_user_gifts(ctx.author.id)
    if not gifts:
        await ctx.send(embed=create_embed("Подарки", "У вас нет подарков", discord.Color.blue()))
        return
    
    embed = create_embed(f"Ваши подарки ({len(gifts)})", "", discord.Color.gold())
    for gift in gifts[:10]:
        try:
            from_user = bot.get_user(gift['from_user_id']) or await bot.fetch_user(gift['from_user_id'])
            from_name = from_user.display_name
        except:
            from_name = "Неизвестный"
        
        embed.add_field(name=f"{GIFT_TYPES.get(gift['gift_type'], '🎁')} {gift['gift_type']} от {from_name}", value=gift['message'][:100], inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='топподарков')
@in_command_channel()
async def gift_top(ctx):
    stats = get_gift_stats()
    if not stats:
        await ctx.send(embed=create_embed("Топ подарков", "Нет данных", discord.Color.blue()))
        return
    
    embed = create_embed("Топ получателей подарков", "", discord.Color.gold())
    for i, stat in enumerate(stats[:10], 1):
        try:
            user = bot.get_user(stat['user_id']) or await bot.fetch_user(stat['user_id'])
            name = user.display_name
        except:
            name = f"ID:{stat['user_id']}"
        embed.add_field(name=f"{i}. {name}", value=f"{stat['count']} подарков", inline=False)
    
    await ctx.send(embed=embed)

# ==================== ПРИЗНАНИЯ ====================
@bot.command(name='признание')
@add_command_reaction("признание")
async def confession(ctx, *, confession_text: str):
    add_confession(confession_text)
    
    channel = discord.utils.get(ctx.guild.channels, name=COMMAND_CHANNEL) or ctx.channel
    embed = create_embed("💌 Анонимное признание", confession_text, discord.Color.pink(), timestamp=True)
    await channel.send(embed=embed)
    
    try:
        await ctx.author.send("✅ Признание опубликовано!")
    except:
        pass
    
    await ctx.message.delete()

# ==================== ИНФОРМАЦИОННЫЕ КОМАНДЫ ====================
@bot.command(name='баланс')
@in_command_channel()
async def balance(ctx, member: discord.Member = None):
    target = member or ctx.author
    
    result = db.fetch_one("SELECT balance FROM users WHERE user_id = ?", (target.id,))
    
    if not result:
        db.execute("""
            INSERT INTO users (user_id, balance, artifacts, cards, completed_combos, created_at) 
            VALUES (?, 0, '{}', '[]', '[]', ?)
        """, (target.id, datetime.now().isoformat()))
        bal = 0
    else:
        bal = result["balance"]
    
    embed = create_embed(
        f"Баланс {target.display_name}",
        f"{bal} {EMOJIS['bibsy']}",
        discord.Color.gold(),
        image="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExODJ4MnFwdnd0eTZxcWRxYTQ0d29wM3V0NGVvMG9jcWw0dTZ5b3M3MyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/QourcDyAyKQI0IR66R/giphy.gif"
    )
    await ctx.send(embed=embed)


@bot.command(name='топ')
@in_command_channel()
async def top(ctx):
    users = db.fetch_all("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10")
    embed = create_embed("Топ фанатов", "", discord.Color.gold())
    
    for i, user in enumerate(users, 1):
        try:
            u = bot.get_user(user["user_id"]) or await bot.fetch_user(user["user_id"])
            name = u.display_name
        except:
            name = f"ID:{user['user_id']}"
        embed.add_field(name=f"{i}. {name}", value=f"{user['balance']} {EMOJIS['bibsy']}", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='фанаты')
@in_command_channel()
async def fans_top(ctx):
    users = db.fetch_all("SELECT user_id, catches FROM bieber_catch ORDER BY catches DESC LIMIT 10")
    embed = create_embed("Топ ловцов Бибера", "", discord.Color.gold())
    
    for i, user in enumerate(users, 1):
        try:
            u = bot.get_user(user["user_id"]) or await bot.fetch_user(user["user_id"])
            name = u.display_name
        except:
            name = f"ID:{user['user_id']}"
        embed.add_field(name=f"{i}. {name}", value=f"{user['catches']} поимок", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='статистика')
@in_command_channel()
async def stats(ctx, member: discord.Member = None):
    target = member or ctx.author
    bal = get_balance(target.id)
    catch = get_bieber_catch_stats(target.id)
    duels = DuelManager.get_daily_duel_count(target.id)
    family = get_family_by_member(target.id)
    collection = get_user_cards_collection(target.id)
    combos = len(get_user_data(target.id)["completed_combos"])
    
    embed = create_embed(f"Статистика {target.display_name}", "", discord.Color.blue())
    embed.add_field(name="💰 Баланс", value=f"{bal} {EMOJIS['bibsy']}", inline=True)
    embed.add_field(name="👶 Ловля Бибера", value=f"{catch['catches']} (фейков: {catch['fake_catches']})", inline=True)
    embed.add_field(name="⚔️ Дуэли сегодня", value=f"{duels}/3", inline=True)
    embed.add_field(name="🎴 Карт в коллекции", value=f"{collection['total']}/{collection['total_possible']}", inline=True)
    embed.add_field(name="🔓 Найдено комбинаций", value=f"{combos}/{len(SECRET_COMBOS)}", inline=True)
    if family:
        embed.add_field(name="👪 Семья", value=f"{family['family_name']} (ур. {family['level']})", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='помощь')
@in_command_channel()
async def help_command(ctx):
    embed = create_embed("Помощь BiberBOT", "Список команд:", discord.Color.blue())
    
    embed.add_field(name="💰 Заработок", value="`!молиться` `!проповедь` `!экстаз` `!покаяться`", inline=False)
    embed.add_field(name="🎴 Коллекционирование", value="`!коллекция` `!картакд` `!шансыкарт`", inline=False)
    embed.add_field(name="🎉 Развлечения", value="`!поцелуй` `!обнять` `!ударить` `!угостить` `!занятьсялюбовью` `!комплимент`", inline=False)
    embed.add_field(name="🎁 Подарки", value="`!подарок` `!моиподарки` `!топподарков`", inline=False)
    embed.add_field(name="👪 Семья", value="`!предложить` `!принять-предложение` `!моясемья` `!добавитьребенка` `!улучшитьсемью` `!развестись` `!дети` `!исключитьребенка`", inline=False)
    embed.add_field(name="🛒 Магазин", value="`!магазин` `!купить` `!артефакты`", inline=False)
    embed.add_field(name="🎮 Игры", value="`!поймать` `!дуэль`", inline=False)
    embed.add_field(name="💸 Прочее", value="`!передать-деньги` `!признание`", inline=False)
    embed.add_field(name="ℹ Информация", value="`!баланс` `!топ` `!фанаты` `!статистика` `!реальныйбаланс`", inline=False)
    
    await ctx.send(embed=embed)

# ==================== АДМИН КОМАНДЫ ====================
@bot.command(name='выдать')
@commands.has_role(ADMIN_ROLE)
@in_command_channel()
async def give_money(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send(embed=create_embed("Ошибка", "Сумма > 0", discord.Color.red()))
        return
    
    new_balance = add_balance(member.id, amount)
    await ctx.send(embed=create_embed("✅ Выдано", f"{member.mention} +{amount} {EMOJIS['bibsy']}\nНовый баланс: {new_balance} {EMOJIS['bibsy']}", discord.Color.green()))

@bot.command(name='забрать')
@commands.has_role(ADMIN_ROLE)
@in_command_channel()
async def take_money(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send(embed=create_embed("Ошибка", "Сумма > 0", discord.Color.red()))
        return
    
    current = get_balance(member.id)
    take_amount = min(amount, current)
    new_balance = add_balance(member.id, -take_amount)
    await ctx.send(embed=create_embed("✅ Забрано", f"{member.mention} -{take_amount} {EMOJIS['bibsy']}\nНовый баланс: {new_balance} {EMOJIS['bibsy']}", discord.Color.green()))

@bot.command(name='установить')
@commands.has_role(ADMIN_ROLE)
@in_command_channel()
async def set_balance_cmd(ctx, member: discord.Member, amount: int):
    if amount < 0:
        await ctx.send(embed=create_embed("Ошибка", "Баланс не может быть отрицательным", discord.Color.red()))
        return
    
    user = db.fetch_one("SELECT user_id FROM users WHERE user_id = ?", (member.id,))
    if not user:
        db.execute("""
            INSERT INTO users (user_id, balance, artifacts, cards, completed_combos, created_at) 
            VALUES (?, ?, '{}', '[]', '[]', ?)
        """, (member.id, amount, datetime.now().isoformat()))
    else:
        db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (amount, member.id))
    
    await ctx.send(embed=create_embed("✅ Установлено", f"{member.mention} баланс = {amount} {EMOJIS['bibsy']}", discord.Color.green()))

@bot.command(name='сброситькулдаун')
@commands.has_role(ADMIN_ROLE)
@in_command_channel()
async def reset_cooldown(ctx, member: discord.Member):
    data = get_user_data(member.id)
    for cmd in ["pray", "sermon", "repent", "ecstasy", "proposal", "divorce"]:
        data[f"last_{cmd}"] = None
    update_user_data(member.id, data)
    await ctx.send(embed=create_embed("✅ Сброшено", f"Кулдауны {member.mention} сброшены", discord.Color.green()))

@bot.command(name='датькарту')
@commands.has_role(ADMIN_ROLE)
@in_command_channel()
async def give_card(ctx, member: discord.Member, *, card_name: str):
    """Выдать карту пользователю (админ-команда)"""
    # Ищем карту по названию
    found = None
    for cid, card in COLLECTIBLE_CARDS.items():
        if card_name.lower() in card['name'].lower():
            found = cid
            break
    
    if not found:
        # Показываем список доступных карт
        cards_list = "\n".join([f"• {card['name']}" for card in COLLECTIBLE_CARDS.values()])
        embed = create_embed(
            "❌ Карта не найдена",
            f"Доступные карты:\n{cards_list}",
            discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    if add_card_to_user(member.id, found):
        card = COLLECTIBLE_CARDS[found]
        embed = create_embed(
            "✅ Карта выдана",
            f"{member.mention} получил карту **{card['name']}** {card['emoji']}!",
            discord.Color.green()
        )
        await ctx.send(embed=embed)
    else:
        embed = create_embed(
            "❌ Ошибка",
            f"У {member.mention} уже есть эта карта!",
            discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name='логи')
@commands.has_role(ADMIN_ROLE)
@in_command_channel()
async def show_logs(ctx, limit: int = 10):
    limit = min(limit, 50)
    logs = db.fetch_all("SELECT timestamp, user_id, command, details FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    
    if not logs:
        await ctx.send(embed=create_embed("Логи", "Нет записей", discord.Color.blue()))
        return
    
    embed = create_embed(f"Последние {len(logs)} действий", "", discord.Color.blue())
    for log in logs:
        try:
            user = bot.get_user(log["user_id"]) or await bot.fetch_user(log["user_id"])
            name = user.display_name
        except:
            name = f"ID:{log['user_id']}"
        embed.add_field(name=f"{log['timestamp']} - {name} - {log['command']}", value=log['details'][:100] or "-", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='сброситькартыкд')
@commands.has_role(ADMIN_ROLE)
@in_command_channel()
async def reset_card_cooldown(ctx, member: discord.Member = None):
    if member:
        if member.id in user_last_card_drop:
            del user_last_card_drop[member.id]
        await ctx.send(embed=create_embed("✅ Сброшено", f"Кулдаун карт для {member.mention} сброшен!", discord.Color.green()))
    else:
        user_last_card_drop.clear()
        await ctx.send(embed=create_embed("✅ Сброшено", "Кулдаун карт для всех пользователей сброшен!", discord.Color.green()))

# ==================== ФОНОВЫЕ ЗАДАЧИ ====================
@tasks.loop(seconds=BIEBER_ESCAPE_INTERVAL)
async def bieber_escape_task():
    await bot.wait_until_ready()
    
    channel = discord.utils.get(bot.get_all_channels(), name=COMMAND_CHANNEL)
    if not channel:
        return
    
    bieber_game.active = True
    bieber_game.channel_id = channel.id
    bieber_game.fake = random.random() < 0.3
    bieber_game.winner = None
    
    embed = create_embed(
        "БИБЕР СБЕЖАЛ!",
        "Быстрее хватай его: `!поймать`",
        discord.Color.gold(),
        footer="У тебя 30 секунд!"
    )
    msg = await channel.send(embed=embed)
    bieber_game.message_id = msg.id
    
    await asyncio.sleep(30)
    
    if bieber_game.winner is None and bieber_game.active:
        bieber_game.active = False
        embed = create_embed("Бибер ушел...", "Никто не поймал!", discord.Color.dark_grey())
        try:
            msg = await channel.fetch_message(bieber_game.message_id)
            await msg.edit(embed=embed)
        except:
            pass

@tasks.loop(hours=1)
async def family_hourly_bonus():
    await bot.wait_until_ready()
    
    try:
        families = db.fetch_all("SELECT * FROM families")
        
        for family in families:
            bonus = FAMILY_HOURLY_BONUSES.get(family["level"], 0)
            if bonus > 0:
                members = [family["spouse1_id"], family["spouse2_id"]]
                try:
                    children = json.loads(family["children"] or "[]")
                    for child in children:
                        members.append(child["id"])
                except:
                    pass
                
                for member_id in members:
                    if member_id:
                        add_balance(member_id, bonus)
                        log_action(member_id, "family_bonus", f"Amount: {bonus}, Family: {family['family_id']}")
    except Exception as e:
        print(f"[ERROR] family_hourly_bonus: {e}")

@tasks.loop(minutes=5)
async def cleanup_old_duels():
    await bot.wait_until_ready()
    DuelManager.cleanup_old_duels()

# ==================== ЗАПУСК ====================
@bot.event
async def setup_hook():
    init_db()
    if not bieber_escape_task.is_running():
        bieber_escape_task.start()
    if not family_hourly_bonus.is_running():
        family_hourly_bonus.start()
    if not cleanup_old_duels.is_running():
        cleanup_old_duels.start()

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user.name} готов к работе!')
    print(f'📊 Команд загружено: {len(bot.commands)}')
    print(f'🎴 Коллекционных карт: {len(COLLECTIBLE_CARDS)}')
    print(f'🔓 Секретных комбинаций: {len(SECRET_COMBOS)}')
    
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name=f"за {CURRENCY_NAME.lower()} | {len(bot.commands)} команд"
    )
    await bot.change_presence(activity=activity)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRole):
        embed = create_embed("❌ Нет прав", "У вас нет прав для этой команды!", discord.Color.red())
        await ctx.send(embed=embed, delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed("❌ Не хватает аргументов", f"Использование: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`", discord.Color.red())
        await ctx.send(embed=embed, delete_after=10)
    else:
        print(f"Ошибка: {error}")
        embed = create_embed("❌ Ошибка", f"Произошла ошибка: {str(error)[:100]}", discord.Color.red())
        await ctx.send(embed=embed, delete_after=10)

# ==================== ВЕБ-СЕРВЕР ДЛЯ KOYEB ====================
try:
    from flask import Flask
    from threading import Thread
    
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return "✅ BiberBOT is running 24/7!"
    
    @app.route('/health')
    def health():
        return "OK", 200
    
    def run_web():
        app.run(host='0.0.0.0', port=8080)
    
    Thread(target=run_web, daemon=True).start()
    print("🌐 Веб-сервер запущен на порту 8080")
except ImportError:
    print("⚠️ Flask не установлен, веб-сервер не запущен")

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    bot.run(TOKEN)