# ==================== НАСТРОЙКИ ====================
ADMIN_ROLE = "Admin"
CURRENCY_NAME = "Бибсы"
CURRENCY_EMOJI = "💰"
COMMAND_CHANNEL = "тттт"
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

# ==================== МАГАЗИН ====================
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

# ==================== РАБОТА ====================
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

# ==================== ПРОПОВЕДИ ====================
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

# ==================== СОЦИАЛЬНЫЕ КОНТЕКСТЫ ====================
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

# ==================== ЭМОДЗИ ====================
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