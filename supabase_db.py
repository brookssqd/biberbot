import os
import json
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from supabase import create_client, Client

# ==================== НАСТРОЙКИ SUPABASE ====================
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ ВНИМАНИЕ: SUPABASE_URL или SUPABASE_KEY не заданы!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==================== ДАННЫЕ ДЛЯ АЧИВОК (избегаем циклического импорта) ====================
ACHIEVEMENTS_DATA = {
    "pray_10": {"name": "🙏 Первые шаги", "desc": "Совершить 10 молитв", "reward": 100},
    "pray_100": {"name": "🙌 Истинный верующий", "desc": "Совершить 100 молитв", "reward": 500, "permanent_bonus": {"command": "pray", "bonus": 2}},
    "pray_1000": {"name": "👼 Святой покровитель", "desc": "Совершить 1000 молитв", "reward": 2000, "permanent_bonus": {"command": "pray", "bonus": 5}},
    "sermon_10": {"name": "📖 Первая проповедь", "desc": "Провести 10 проповедей", "reward": 100},
    "sermon_100": {"name": "✝️ Глашатай веры", "desc": "Провести 100 проповедей", "reward": 500, "permanent_bonus": {"command": "sermon", "bonus": 2}},
    "sermon_1000": {"name": "📜 Пророк", "desc": "Провести 1000 проповедей", "reward": 2000, "permanent_bonus": {"command": "sermon", "bonus": 5}},
    "cards_5": {"name": "🎴 Начинающий коллекционер", "desc": "Собрать 5 карт", "reward": 200},
    "cards_15": {"name": "🎴 Знаток Бибера", "desc": "Собрать 15 карт", "reward": 500, "permanent_bonus": {"command": "card", "bonus": 3}},
    "cards_all": {"name": "🎴 Легендарный коллекционер", "desc": "Собрать ВСЕ карты", "reward": 5000, "permanent_bonus": {"command": "card", "bonus": 10}},
    "balance_1000": {"name": "💰 Первый капитал", "desc": "Накопить 1000 бибсов", "reward": 200},
    "balance_10000": {"name": "💎 Бибер-миллионер", "desc": "Накопить 10000 бибсов", "reward": 1000, "permanent_bonus": {"command": "all", "bonus": 3}},
    "balance_100000": {"name": "👑 Король фанатов", "desc": "Накопить 100000 бибсов", "reward": 5000, "permanent_bonus": {"command": "all", "bonus": 5}},
    "catch_5": {"name": "🎣 Первая добыча", "desc": "Поймать Бибера 5 раз", "reward": 300},
    "catch_25": {"name": "🏃 Охотник за Бибером", "desc": "Поймать Бибера 25 раз", "reward": 1000, "permanent_bonus": {"command": "catch", "bonus": 5}},
    "catch_100": {"name": "⚡ Легендарный охотник", "desc": "Поймать Бибера 100 раз", "reward": 3000, "permanent_bonus": {"command": "catch", "bonus": 10}},
    "duel_5": {"name": "⚔️ Первая победа", "desc": "Выиграть 5 дуэлей", "reward": 500},
    "duel_25": {"name": "🏆 Непобедимый", "desc": "Выиграть 25 дуэлей", "reward": 1500, "permanent_bonus": {"command": "duel", "bonus": 5}},
    "duel_100": {"name": "👊 Легенда дуэлей", "desc": "Выиграть 100 дуэлей", "reward": 5000, "permanent_bonus": {"command": "duel", "bonus": 10}},
    "family_create": {"name": "💍 В браке", "desc": "Создать семью", "reward": 1000},
    "family_level_3": {"name": "🏠 Крепкая семья", "desc": "Улучшить семью до 3 уровня", "reward": 2000, "permanent_bonus": {"command": "family", "bonus": 5}},
    "family_level_6": {"name": "👑 Королевская семья", "desc": "Улучшить семью до 6 уровня", "reward": 5000, "permanent_bonus": {"command": "family", "bonus": 10}},
    "combo_1": {"name": "🤫 Знаток секретов", "desc": "Найти первую секретную комбинацию", "reward": 500},
    "combo_5": {"name": "🧙‍♂️ Мастер комбинаций", "desc": "Найти 5 секретных комбинаций", "reward": 2000, "permanent_bonus": {"command": "combo", "bonus": 10}},
    "combo_all": {"name": "🧙‍♂️ Архимаг", "desc": "Найти ВСЕ секретные комбинации", "reward": 5000, "permanent_bonus": {"command": "combo", "bonus": 20}},
}
SECRET_COMBOS_COUNT = 8  # Всего 8 секретных комбинаций

# ==================== ФУНКЦИИ ДЛЯ ЛОГИРОВАНИЯ ====================

def log_action(user_id: int, command: str, details: str = ""):
    try:
        supabase.table('logs').insert({
            'user_id': user_id,
            'command': command,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }).execute()
    except Exception as e:
        print(f"Ошибка логирования: {e}")

# ==================== ФУНКЦИИ РАБОТЫ С БАЛАНСОМ ====================

def add_balance(user_id: int, amount: int) -> int:
    try:
        response = supabase.table('users').select('balance').eq('user_id', user_id).execute()
        
        if response.data:
            current = response.data[0]['balance']
            new_balance = current + amount
            supabase.table('users').update({'balance': new_balance}).eq('user_id', user_id).execute()
        else:
            new_balance = amount if amount > 0 else 0
            supabase.table('users').insert({
                'user_id': user_id,
                'balance': new_balance,
                'artifacts': '{}',
                'cards': '[]',
                'completed_combos': '[]'
            }).execute()
        
        print(f"[BALANCE] {user_id}: {amount:+d} -> {new_balance}")
        return new_balance
    except Exception as e:
        print(f"[ERROR] add_balance: {e}")
        return 0

def get_balance(user_id: int) -> int:
    try:
        response = supabase.table('users').select('balance').eq('user_id', user_id).execute()
        if response.data:
            return response.data[0]['balance']
        return 0
    except Exception as e:
        print(f"[ERROR] get_balance: {e}")
        return 0

def set_balance(user_id: int, amount: int) -> int:
    try:
        supabase.table('users').upsert({
            'user_id': user_id,
            'balance': amount,
            'artifacts': '{}',
            'cards': '[]',
            'completed_combos': '[]'
        }).execute()
        return amount
    except Exception as e:
        print(f"[ERROR] set_balance: {e}")
        return 0

# ==================== ФУНКЦИИ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ====================

def get_user_data(user_id: int) -> dict:
    try:
        response = supabase.table('users').select('*').eq('user_id', user_id).execute()
        
        if not response.data:
            supabase.table('users').insert({
                'user_id': user_id,
                'balance': 0,
                'artifacts': '{}',
                'cards': '[]',
                'completed_combos': '[]'
            }).execute()
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
                "last_divorce": None,
                "last_family_join": None,
                "consumables": {},
                "next_double": False,
                "protect_ecstasy": False,
                "stats": {},
                "achievements": [],
                "achievement_bonuses": {}
            }
        
        data = response.data[0]
        
        artifacts = json.loads(data.get('artifacts', '{}'))
        cards = json.loads(data.get('cards', '[]'))
        completed_combos = json.loads(data.get('completed_combos', '[]'))
        consumables = json.loads(data.get('consumables', '{}'))
        stats = json.loads(data.get('stats', '{}'))
        achievements = json.loads(data.get('achievements', '[]'))
        achievement_bonuses = json.loads(data.get('achievement_bonuses', '{}'))
        
        return {
            "balance": data.get('balance', 0),
            "last_pray": data.get('last_pray'),
            "last_sermon": data.get('last_sermon'),
            "last_repent": data.get('last_repent'),
            "last_ecstasy": data.get('last_ecstasy'),
            "artifacts": artifacts,
            "cards": cards,
            "completed_combos": completed_combos,
            "personal_role": data.get('personal_role'),
            "personal_tag": data.get('personal_tag'),
            "last_proposal": data.get('last_proposal'),
            "last_divorce": data.get('last_divorce'),
            "last_family_join": data.get('last_family_join'),
            "consumables": consumables,
            "next_double": data.get('next_double', False),
            "protect_ecstasy": data.get('protect_ecstasy', False),
            "stats": stats,
            "achievements": achievements,
            "achievement_bonuses": achievement_bonuses
        }
    except Exception as e:
        print(f"[ERROR] get_user_data: {e}")
        return {"balance": 0, "artifacts": {}, "cards": [], "completed_combos": []}

def update_user_data(user_id: int, data: dict):
    try:
        supabase.table('users').update({
            'balance': data.get('balance', 0),
            'last_pray': data.get('last_pray'),
            'last_sermon': data.get('last_sermon'),
            'last_repent': data.get('last_repent'),
            'last_ecstasy': data.get('last_ecstasy'),
            'artifacts': json.dumps(data.get('artifacts', {})),
            'cards': json.dumps(data.get('cards', [])),
            'completed_combos': json.dumps(data.get('completed_combos', [])),
            'personal_role': data.get('personal_role'),
            'personal_tag': data.get('personal_tag'),
            'last_proposal': data.get('last_proposal'),
            'last_divorce': data.get('last_divorce'),
            'last_family_join': data.get('last_family_join'),
            'consumables': json.dumps(data.get('consumables', {})),
            'next_double': data.get('next_double', False),
            'protect_ecstasy': data.get('protect_ecstasy', False),
            'stats': json.dumps(data.get('stats', {})),
            'achievements': json.dumps(data.get('achievements', [])),
            'achievement_bonuses': json.dumps(data.get('achievement_bonuses', {}))
        }).eq('user_id', user_id).execute()
    except Exception as e:
        print(f"[ERROR] update_user_data: {e}")

# ==================== ФУНКЦИИ ДЛЯ КАРТОЧЕК ====================

def add_card_to_user(user_id: int, card_id: str) -> bool:
    try:
        response = supabase.table('users').select('cards').eq('user_id', user_id).execute()
        cards = []
        
        if response.data and response.data[0].get('cards'):
            cards = json.loads(response.data[0]['cards'])
        
        if card_id in cards:
            return False
        
        cards.append(card_id)
        supabase.table('users').update({'cards': json.dumps(cards)}).eq('user_id', user_id).execute()
        log_action(user_id, "add_card", card_id)
        return True
    except Exception as e:
        print(f"[ERROR] add_card_to_user: {e}")
        return False

def get_user_cards_collection(user_id: int) -> dict:
    from bot_data import COLLECTIBLE_CARDS
    
    try:
        response = supabase.table('users').select('cards').eq('user_id', user_id).execute()
        cards = []
        
        if response.data and response.data[0].get('cards'):
            cards = json.loads(response.data[0]['cards'])
        
        collection = {
            "common": [],
            "rare": [],
            "epic": [],
            "legendary": [],
            "mythic": [],
            "total": len(cards),
            "total_possible": len(COLLECTIBLE_CARDS)
        }
        
        for card_id in cards:
            if card_id in COLLECTIBLE_CARDS:
                rarity = COLLECTIBLE_CARDS[card_id]["rarity"]
                collection[rarity].append(card_id)
        
        return collection
    except Exception as e:
        print(f"[ERROR] get_user_cards_collection: {e}")
        return {"common": [], "rare": [], "epic": [], "legendary": [], "mythic": [], "total": 0, "total_possible": 0}

# ==================== СИСТЕМА АРТЕФАКТОВ ====================

def add_temporary_artifact(user_id: int, artifact_id: str, duration_days: int) -> bool:
    try:
        from bot_data import SHOP_ITEMS
        
        if artifact_id not in SHOP_ITEMS:
            return False
        
        user_data = get_user_data(user_id)
        artifacts = user_data.get("artifacts", {})
        
        expires_at = (datetime.now() + timedelta(days=duration_days)).isoformat()
        
        artifacts[artifact_id] = {
            "expires_at": expires_at,
            "type": "temporary",
            "duration_days": duration_days
        }
        
        user_data["artifacts"] = artifacts
        update_user_data(user_id, user_data)
        
        log_action(user_id, "add_temporary_artifact", f"{artifact_id} expires at {expires_at}")
        return True
        
    except Exception as e:
        print(f"[ERROR] add_temporary_artifact: {e}")
        return False

def add_permanent_artifact(user_id: int, artifact_id: str) -> bool:
    try:
        from bot_data import SHOP_ITEMS
        
        if artifact_id not in SHOP_ITEMS:
            return False
        
        user_data = get_user_data(user_id)
        artifacts = user_data.get("artifacts", {})
        
        artifacts[artifact_id] = {
            "type": "permanent"
        }
        
        user_data["artifacts"] = artifacts
        update_user_data(user_id, user_data)
        
        log_action(user_id, "add_permanent_artifact", artifact_id)
        return True
        
    except Exception as e:
        print(f"[ERROR] add_permanent_artifact: {e}")
        return False

def check_expired_artifacts(user_id: int) -> dict:
    try:
        user_data = get_user_data(user_id)
        artifacts = user_data.get("artifacts", {})
        
        expired = []
        active = {}
        
        for art_id, art_data in artifacts.items():
            if art_data.get("type") == "temporary" and "expires_at" in art_data:
                expires_at = datetime.fromisoformat(art_data["expires_at"])
                if expires_at < datetime.now():
                    expired.append(art_id)
                    continue
            active[art_id] = art_data
        
        if expired:
            user_data["artifacts"] = active
            update_user_data(user_id, user_data)
            print(f"[ARTIFACT] У пользователя {user_id} истекли артефакты: {expired}")
        
        return {"active": active, "expired": expired}
        
    except Exception as e:
        print(f"[ERROR] check_expired_artifacts: {e}")
        return {"active": {}, "expired": []}

def get_active_bonus_percent(user_id: int, command: str) -> int:
    try:
        from bot_data import SHOP_ITEMS
        
        check_expired_artifacts(user_id)
        
        user_data = get_user_data(user_id)
        artifacts = user_data.get("artifacts", {})
        
        total_bonus = 0
        
        for art_id, art_data in artifacts.items():
            if art_id not in SHOP_ITEMS:
                continue
            
            item = SHOP_ITEMS[art_id]
            effect = item.get("effect", {})
            
            if effect.get("command") == command or effect.get("command") == "all":
                total_bonus += effect.get("bonus", 0)
        
        # Добавляем бонус от достижений
        achievement_bonus = get_achievement_bonus(user_id, command)
        total_bonus += achievement_bonus
        
        return min(total_bonus, 300)
        
    except Exception as e:
        print(f"[ERROR] get_active_bonus_percent: {e}")
        return 0

# ==================== СИСТЕМА АЧИВОК ====================

def get_achievement_bonus(user_id: int, command: str) -> int:
    """Получить бонус от достижений"""
    user_data = get_user_data(user_id)
    bonuses = user_data.get("achievement_bonuses", {})
    
    total = 0
    for ach_id, bonus in bonuses.items():
        if bonus.get("command") == command or bonus.get("command") == "all":
            total += bonus.get("bonus", 0)
    
    return min(total, 100)

def check_achievements(user_id: int) -> list:
    """Проверить и выдать новые достижения"""
    from bot_data import COLLECTIBLE_CARDS
    
    user_data = get_user_data(user_id)
    achievements = user_data.get("achievements", [])
    stats = user_data.get("stats", {})
    
    new_achievements = []
    
    # Собираем статистику
    pray_count = stats.get("pray_count", 0)
    sermon_count = stats.get("sermon_count", 0)
    cards_count = len(user_data.get("cards", []))
    balance = user_data.get("balance", 0)
    catch_count = get_bieber_catch_stats(user_id)["catches"]
    duel_wins = stats.get("duel_wins", 0)
    family = get_family_by_member(user_id)
    combos_count = len(user_data.get("completed_combos", []))
    
    print(f"[ACHIEVEMENTS] Проверка для {user_id}: молитв={pray_count}, карт={cards_count}, баланс={balance}")
    
    # Проверяем каждое достижение
    if "pray_10" not in achievements and pray_count >= 10:
        new_achievements.append("pray_10")
    if "pray_100" not in achievements and pray_count >= 100:
        new_achievements.append("pray_100")
    if "pray_1000" not in achievements and pray_count >= 1000:
        new_achievements.append("pray_1000")
    
    if "sermon_10" not in achievements and sermon_count >= 10:
        new_achievements.append("sermon_10")
    if "sermon_100" not in achievements and sermon_count >= 100:
        new_achievements.append("sermon_100")
    if "sermon_1000" not in achievements and sermon_count >= 1000:
        new_achievements.append("sermon_1000")
    
    if "cards_5" not in achievements and cards_count >= 5:
        new_achievements.append("cards_5")
    if "cards_15" not in achievements and cards_count >= 15:
        new_achievements.append("cards_15")
    if "cards_all" not in achievements and cards_count >= len(COLLECTIBLE_CARDS):
        new_achievements.append("cards_all")
    
    if "balance_1000" not in achievements and balance >= 1000:
        new_achievements.append("balance_1000")
    if "balance_10000" not in achievements and balance >= 10000:
        new_achievements.append("balance_10000")
    if "balance_100000" not in achievements and balance >= 100000:
        new_achievements.append("balance_100000")
    
    if "catch_5" not in achievements and catch_count >= 5:
        new_achievements.append("catch_5")
    if "catch_25" not in achievements and catch_count >= 25:
        new_achievements.append("catch_25")
    if "catch_100" not in achievements and catch_count >= 100:
        new_achievements.append("catch_100")
    
    if "duel_5" not in achievements and duel_wins >= 5:
        new_achievements.append("duel_5")
    if "duel_25" not in achievements and duel_wins >= 25:
        new_achievements.append("duel_25")
    if "duel_100" not in achievements and duel_wins >= 100:
        new_achievements.append("duel_100")
    
    if "family_create" not in achievements and family:
        new_achievements.append("family_create")
    if "family_level_3" not in achievements and family and family.get("level", 0) >= 3:
        new_achievements.append("family_level_3")
    if "family_level_6" not in achievements and family and family.get("level", 0) >= 6:
        new_achievements.append("family_level_6")
    
    if "combo_1" not in achievements and combos_count >= 1:
        new_achievements.append("combo_1")
    if "combo_5" not in achievements and combos_count >= 5:
        new_achievements.append("combo_5")
    if "combo_all" not in achievements and combos_count >= SECRET_COMBOS_COUNT:
        new_achievements.append("combo_all")
    
    print(f"[ACHIEVEMENTS] Новые достижения для {user_id}: {new_achievements}")
    
    # Выдаём награды
    if new_achievements:
        for ach_id in new_achievements:
            ach_data = ACHIEVEMENTS_DATA[ach_id]
            
            # Мгновенная награда
            if "reward" in ach_data:
                add_balance(user_id, ach_data["reward"])
                print(f"[ACHIEVEMENTS] Выдана награда {ach_data['reward']} бибсов за {ach_id}")
            
            # Постоянный бонус
            if "permanent_bonus" in ach_data:
                bonus = ach_data["permanent_bonus"]
                # Получаем свежие данные
                user_data = get_user_data(user_id)
                if "achievement_bonuses" not in user_data:
                    user_data["achievement_bonuses"] = {}
                user_data["achievement_bonuses"][ach_id] = bonus
                update_user_data(user_id, user_data)
                print(f"[ACHIEVEMENTS] Выдан постоянный бонус +{bonus['bonus']}% к {bonus['command']}")
        
        # Сохраняем достижения
        user_data = get_user_data(user_id)
        user_data["achievements"] = achievements + new_achievements
        update_user_data(user_id, user_data)
    
    return new_achievements

# ==================== ФУНКЦИИ ДЛЯ РАСХОДУЕМЫХ ПРЕДМЕТОВ ====================

def add_consumable(user_id: int, item_id: str, quantity: int = 1) -> bool:
    try:
        user_data = get_user_data(user_id)
        consumables = user_data.get("consumables", {})
        
        if item_id in consumables:
            consumables[item_id] += quantity
        else:
            consumables[item_id] = quantity
        
        user_data["consumables"] = consumables
        update_user_data(user_id, user_data)
        
        log_action(user_id, "add_consumable", f"{item_id} x{quantity}")
        return True
        
    except Exception as e:
        print(f"[ERROR] add_consumable: {e}")
        return False

def use_consumable(user_id: int, item_id: str) -> bool:
    try:
        user_data = get_user_data(user_id)
        consumables = user_data.get("consumables", {})
        
        if consumables.get(item_id, 0) <= 0:
            return False
        
        consumables[item_id] -= 1
        
        if consumables[item_id] <= 0:
            del consumables[item_id]
        
        user_data["consumables"] = consumables
        update_user_data(user_id, user_data)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] use_consumable: {e}")
        return False

def get_consumable_count(user_id: int, item_id: str) -> int:
    try:
        user_data = get_user_data(user_id)
        consumables = user_data.get("consumables", {})
        return consumables.get(item_id, 0)
    except Exception as e:
        print(f"[ERROR] get_consumable_count: {e}")
        return 0

def get_daily_consumable_purchases(user_id: int, item_id: str) -> int:
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        
        response = supabase.table('consumable_purchases') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('item_id', item_id) \
            .eq('purchase_date', today) \
            .execute()
        
        return len(response.data)
    except Exception as e:
        print(f"[ERROR] get_daily_consumable_purchases: {e}")
        return 0

def add_consumable_purchase(user_id: int, item_id: str):
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        
        supabase.table('consumable_purchases').insert({
            'user_id': user_id,
            'item_id': item_id,
            'purchase_date': today
        }).execute()
    except Exception as e:
        print(f"[ERROR] add_consumable_purchase: {e}")

# ==================== СЕМЕЙНЫЕ ФУНКЦИИ ====================

def get_family_by_member(user_id: int) -> Optional[dict]:
    try:
        families = supabase.table('families').select('*').execute()
        
        for family in families.data:
            if family['spouse1_id'] == user_id or family['spouse2_id'] == user_id:
                children = json.loads(family.get('children', '[]'))
                return {
                    "family_id": family['family_id'],
                    "spouse1_id": family['spouse1_id'],
                    "spouse2_id": family['spouse2_id'],
                    "children": children,
                    "level": family['level'],
                    "family_name": family['family_name']
                }
            
            children = json.loads(family.get('children', '[]'))
            for child in children:
                if child.get('id') == user_id:
                    return {
                        "family_id": family['family_id'],
                        "spouse1_id": family['spouse1_id'],
                        "spouse2_id": family['spouse2_id'],
                        "children": children,
                        "level": family['level'],
                        "family_name": family['family_name']
                    }
        
        return None
    except Exception as e:
        print(f"[ERROR] get_family_by_member: {e}")
        return None

def create_family(spouse1_id: int, spouse2_id: int, family_name: str) -> int:
    try:
        result = supabase.table('families').insert({
            'spouse1_id': spouse1_id,
            'spouse2_id': spouse2_id,
            'family_name': family_name,
            'children': '[]',
            'level': 1,
            'created_at': datetime.now().isoformat()
        }).execute()
        return result.data[0]['family_id']
    except Exception as e:
        print(f"[ERROR] create_family: {e}")
        return 0

def update_family(family_id: int, data: dict):
    try:
        supabase.table('families').update({
            'spouse1_id': data['spouse1_id'],
            'spouse2_id': data['spouse2_id'],
            'children': json.dumps(data['children']),
            'level': data['level'],
            'family_name': data['family_name']
        }).eq('family_id', family_id).execute()
    except Exception as e:
        print(f"[ERROR] update_family: {e}")

def get_family(family_id: int) -> Optional[dict]:
    try:
        response = supabase.table('families').select('*').eq('family_id', family_id).execute()
        if not response.data:
            return None
        
        family = response.data[0]
        return {
            "family_id": family['family_id'],
            "spouse1_id": family['spouse1_id'],
            "spouse2_id": family['spouse2_id'],
            "children": json.loads(family.get('children', '[]')),
            "level": family['level'],
            "family_name": family['family_name']
        }
    except Exception as e:
        print(f"[ERROR] get_family: {e}")
        return None

def add_child_to_family(family_id: int, child_id: int, child_name: str, child_type: str) -> bool:
    try:
        family = get_family(family_id)
        if not family:
            return False
        
        if len(family['children']) >= 5:
            return False
        
        for child in family['children']:
            if child.get('id') == child_id:
                return False
        
        family['children'].append({
            "id": child_id,
            "name": child_name,
            "type": child_type,
            "added_at": datetime.now().isoformat()
        })
        
        update_family(family_id, family)
        return True
    except Exception as e:
        print(f"[ERROR] add_child_to_family: {e}")
        return False

def remove_child_from_family(family_id: int, child_id: int) -> bool:
    try:
        family = get_family(family_id)
        if not family:
            return False
        
        for i, child in enumerate(family['children']):
            if child.get('id') == child_id:
                del family['children'][i]
                update_family(family_id, family)
                return True
        
        return False
    except Exception as e:
        print(f"[ERROR] remove_child_from_family: {e}")
        return False

def get_family_upgrade_cooldown(family_id: int) -> Optional[datetime]:
    try:
        response = supabase.table('families').select('last_upgrade_at').eq('family_id', family_id).execute()
        if response.data and response.data[0].get('last_upgrade_at'):
            return datetime.fromisoformat(response.data[0]['last_upgrade_at'])
        return None
    except Exception as e:
        print(f"[ERROR] get_family_upgrade_cooldown: {e}")
        return None

def set_family_upgrade_time(family_id: int):
    try:
        supabase.table('families').update({
            'last_upgrade_at': datetime.now().isoformat()
        }).eq('family_id', family_id).execute()
    except Exception as e:
        print(f"[ERROR] set_family_upgrade_time: {e}")

def get_family_age_days(family_id: int) -> int:
    try:
        response = supabase.table('families').select('created_at').eq('family_id', family_id).execute()
        if response.data:
            created_at = datetime.fromisoformat(response.data[0]['created_at'])
            return (datetime.now() - created_at).days
        return 0
    except Exception as e:
        print(f"[ERROR] get_family_age_days: {e}")
        return 0

def can_upgrade_family(family_id: int, FAMILY_UPGRADE_REQUIREMENTS: dict, FAMILY_MAX_LEVEL: int, FAMILY_UPGRADE_COOLDOWN: int) -> tuple:
    try:
        family = get_family(family_id)
        if not family:
            return (False, "Семья не найдена!")
        
        if family['level'] >= FAMILY_MAX_LEVEL:
            return (False, f"Семья уже достигла максимального {FAMILY_MAX_LEVEL} уровня!")
        
        next_level = family['level'] + 1
        
        last_upgrade = get_family_upgrade_cooldown(family_id)
        if last_upgrade:
            time_since = (datetime.now() - last_upgrade).total_seconds()
            if time_since < FAMILY_UPGRADE_COOLDOWN:
                remaining_hours = int((FAMILY_UPGRADE_COOLDOWN - time_since) // 3600)
                remaining_minutes = int(((FAMILY_UPGRADE_COOLDOWN - time_since) % 3600) // 60)
                return (False, f"Семью можно улучшать только раз в 24 часа! Осталось: {remaining_hours}ч {remaining_minutes}м")
        
        req = FAMILY_UPGRADE_REQUIREMENTS.get(next_level, {})
        
        min_children = req.get("min_children", 0)
        if len(family['children']) < min_children:
            return (False, f"Для улучшения до {next_level} уровня нужно {min_children} детей! Сейчас: {len(family['children'])}")
        
        min_age_days = req.get("min_family_age_days", 0)
        family_age = get_family_age_days(family_id)
        if family_age < min_age_days:
            return (False, f"Семье нужно существовать {min_age_days} дней для улучшения до {next_level} уровня! Сейчас: {family_age} дней")
        
        return (True, f"Можно улучшить до {next_level} уровня")
        
    except Exception as e:
        print(f"[ERROR] can_upgrade_family: {e}")
        return (False, "Ошибка проверки")

def upgrade_family_with_checks(family_id: int, FAMILY_UPGRADE_COSTS: dict, FAMILY_UPGRADE_REQUIREMENTS: dict, FAMILY_MAX_LEVEL: int, FAMILY_UPGRADE_COOLDOWN: int) -> tuple:
    try:
        can, message = can_upgrade_family(family_id, FAMILY_UPGRADE_REQUIREMENTS, FAMILY_MAX_LEVEL, FAMILY_UPGRADE_COOLDOWN)
        if not can:
            return (False, message)
        
        family = get_family(family_id)
        cost = FAMILY_UPGRADE_COSTS.get(family['level'], 5000)
        
        half_cost = cost // 2
        spouse1_balance = get_balance(family['spouse1_id'])
        spouse2_balance = get_balance(family['spouse2_id'])
        
        if spouse1_balance >= half_cost and spouse2_balance >= half_cost:
            add_balance(family['spouse1_id'], -half_cost)
            add_balance(family['spouse2_id'], -half_cost)
        elif spouse1_balance >= cost:
            add_balance(family['spouse1_id'], -cost)
        elif spouse2_balance >= cost:
            add_balance(family['spouse2_id'], -cost)
        else:
            add_balance(family['spouse1_id'], -spouse1_balance)
            add_balance(family['spouse2_id'], -(cost - spouse1_balance))
        
        family['level'] += 1
        update_family(family_id, family)
        set_family_upgrade_time(family_id)
        
        return (True, f"Семья улучшена до {family['level']} уровня!")
        
    except Exception as e:
        print(f"[ERROR] upgrade_family_with_checks: {e}")
        return (False, "Ошибка при улучшении")

def can_join_family(user_id: int, FAMILY_JOIN_COOLDOWN: int) -> tuple:
    try:
        user_data = get_user_data(user_id)
        last_join = user_data.get('last_family_join')
        
        if last_join:
            last_join_time = datetime.fromisoformat(last_join)
            time_since = (datetime.now() - last_join_time).total_seconds()
            if time_since < FAMILY_JOIN_COOLDOWN:
                remaining_hours = int((FAMILY_JOIN_COOLDOWN - time_since) // 3600)
                return (False, f"Вы сможете вступить в новую семью через {remaining_hours} часов")
        
        return (True, "Можно вступать")
        
    except Exception as e:
        print(f"[ERROR] can_join_family: {e}")
        return (True, "Можно вступать")

def set_user_join_time(user_id: int):
    try:
        user_data = get_user_data(user_id)
        user_data['last_family_join'] = datetime.now().isoformat()
        update_user_data(user_id, user_data)
    except Exception as e:
        print(f"[ERROR] set_user_join_time: {e}")

def can_divorce(user_id: int, FAMILY_DIVORCE_COOLDOWN: int) -> tuple:
    try:
        user_data = get_user_data(user_id)
        last_divorce = user_data.get('last_divorce')
        
        if last_divorce:
            last_divorce_time = datetime.fromisoformat(last_divorce)
            time_since = (datetime.now() - last_divorce_time).total_seconds()
            if time_since < FAMILY_DIVORCE_COOLDOWN:
                remaining_days = int((FAMILY_DIVORCE_COOLDOWN - time_since) // 86400)
                return (False, f"Вы сможете развестись через {remaining_days} дней")
        
        return (True, "Можно разводиться")
        
    except Exception as e:
        print(f"[ERROR] can_divorce: {e}")
        return (True, "Можно разводиться")

def set_divorce_time(user_id: int):
    try:
        user_data = get_user_data(user_id)
        user_data['last_divorce'] = datetime.now().isoformat()
        update_user_data(user_id, user_data)
    except Exception as e:
        print(f"[ERROR] set_divorce_time: {e}")

# ==================== ФУНКЦИИ ДЛЯ ПРЕДЛОЖЕНИЙ ====================

def create_marriage_proposal(from_id: int, to_id: int, proposal_text: str) -> int:
    try:
        result = supabase.table('marriage_proposals').insert({
            'from_id': from_id,
            'to_id': to_id,
            'proposal_text': proposal_text,
            'timestamp': datetime.now().isoformat()
        }).execute()
        return result.data[0]['proposal_id']
    except Exception as e:
        print(f"[ERROR] create_marriage_proposal: {e}")
        return 0

def get_marriage_proposal(proposal_id: int) -> Optional[dict]:
    try:
        response = supabase.table('marriage_proposals').select('*').eq('proposal_id', proposal_id).execute()
        if not response.data:
            return None
        return response.data[0]
    except Exception as e:
        print(f"[ERROR] get_marriage_proposal: {e}")
        return None

def delete_marriage_proposal(proposal_id: int):
    try:
        supabase.table('marriage_proposals').delete().eq('proposal_id', proposal_id).execute()
    except Exception as e:
        print(f"[ERROR] delete_marriage_proposal: {e}")

# ==================== ФУНКЦИИ ДЛЯ ПОДАРКОВ ====================

def send_gift(from_user_id: int, to_user_id: int, gift_type: str, message: str):
    try:
        supabase.table('gifts').insert({
            'from_user_id': from_user_id,
            'to_user_id': to_user_id,
            'gift_type': gift_type,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }).execute()
        log_action(from_user_id, "send_gift", f"To: {to_user_id}, Type: {gift_type}")
    except Exception as e:
        print(f"[ERROR] send_gift: {e}")

def get_user_gifts(user_id: int) -> List[dict]:
    try:
        response = supabase.table('gifts').select('*').eq('to_user_id', user_id).order('timestamp', desc=True).execute()
        return response.data
    except Exception as e:
        print(f"[ERROR] get_user_gifts: {e}")
        return []

def get_gift_stats() -> List[dict]:
    try:
        response = supabase.table('gifts').select('to_user_id').execute()
        stats = {}
        for gift in response.data:
            stats[gift['to_user_id']] = stats.get(gift['to_user_id'], 0) + 1
        
        sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:10]
        return [{"user_id": uid, "count": count} for uid, count in sorted_stats]
    except Exception as e:
        print(f"[ERROR] get_gift_stats: {e}")
        return []

# ==================== ФУНКЦИИ ДЛЯ ПРИЗНАНИЙ ====================

def add_confession(confession_text: str):
    try:
        supabase.table('confessions').insert({
            'confession_text': confession_text,
            'timestamp': datetime.now().isoformat()
        }).execute()
    except Exception as e:
        print(f"[ERROR] add_confession: {e}")

# ==================== ФУНКЦИИ ДЛЯ ЛОВЛИ БИБЕРА ====================

def get_bieber_catch_stats(user_id: int) -> dict:
    try:
        response = supabase.table('bieber_catch').select('catches, fake_catches').eq('user_id', user_id).execute()
        if response.data:
            return {"catches": response.data[0]['catches'], "fake_catches": response.data[0]['fake_catches']}
        return {"catches": 0, "fake_catches": 0}
    except Exception as e:
        print(f"[ERROR] get_bieber_catch_stats: {e}")
        return {"catches": 0, "fake_catches": 0}

def update_bieber_catch_stats(user_id: int, real_catch: bool = True):
    try:
        if real_catch:
            response = supabase.table('bieber_catch').select('catches').eq('user_id', user_id).execute()
            current = response.data[0]['catches'] if response.data else 0
            supabase.table('bieber_catch').upsert({
                'user_id': user_id,
                'catches': current + 1,
                'fake_catches': 0
            }).execute()
        else:
            response = supabase.table('bieber_catch').select('fake_catches').eq('user_id', user_id).execute()
            current = response.data[0]['fake_catches'] if response.data else 0
            supabase.table('bieber_catch').upsert({
                'user_id': user_id,
                'catches': 0,
                'fake_catches': current + 1
            }).execute()
        log_action(user_id, "bieber_catch", f"Real: {real_catch}")
    except Exception as e:
        print(f"[ERROR] update_bieber_catch_stats: {e}")

# ==================== ФУНКЦИИ ДЛЯ ДУЭЛЕЙ ====================

class DuelManager:
    @staticmethod
    def create_duel(channel_id: int, challenger_id: int, target_id: int, amount: int) -> bool:
        try:
            supabase.table('active_duels').upsert({
                'channel_id': channel_id,
                'challenger_id': challenger_id,
                'target_id': target_id,
                'amount': amount,
                'accepted': False,
                'fighters_ready': '[]',
                'created_at': datetime.now().isoformat()
            }).execute()
            return True
        except Exception as e:
            print(f"Ошибка создания дуэли: {e}")
            return False
    
    @staticmethod
    def get_duel(channel_id: int) -> Optional[dict]:
        try:
            response = supabase.table('active_duels').select('*').eq('channel_id', channel_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"[ERROR] get_duel: {e}")
            return None
    
    @staticmethod
    def delete_duel(channel_id: int):
        try:
            supabase.table('active_duels').delete().eq('channel_id', channel_id).execute()
        except Exception as e:
            print(f"[ERROR] delete_duel: {e}")
    
    @staticmethod
    def accept_duel(channel_id: int, target_id: int) -> bool:
        duel = DuelManager.get_duel(channel_id)
        if not duel or duel['target_id'] != target_id:
            return False
        supabase.table('active_duels').update({'accepted': True}).eq('channel_id', channel_id).execute()
        return True
    
    @staticmethod
    def add_fighter_ready(channel_id: int, fighter_id: int) -> int:
        duel = DuelManager.get_duel(channel_id)
        if not duel:
            return 0
        
        fighters = json.loads(duel.get('fighters_ready', '[]'))
        if fighter_id not in fighters:
            fighters.append(fighter_id)
        
        supabase.table('active_duels').update({'fighters_ready': json.dumps(fighters)}).eq('channel_id', channel_id).execute()
        return len(fighters)
    
    @staticmethod
    def cleanup_old_duels():
        try:
            supabase.table('active_duels').delete().lt('created_at', (datetime.now() - timedelta(minutes=5)).isoformat()).execute()
        except Exception as e:
            print(f"[ERROR] cleanup_old_duels: {e}")
    
    @staticmethod
    def get_daily_duel_count(user_id: int) -> int:
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            response = supabase.table('duels').select('count').eq('user_id', user_id).eq('date', today).execute()
            if response.data:
                return response.data[0]['count']
            return 0
        except Exception as e:
            print(f"[ERROR] get_daily_duel_count: {e}")
            return 0
    
    @staticmethod
    def increment_duel_count(user_id: int, won: bool = False):
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            response = supabase.table('duels').select('count, wins').eq('user_id', user_id).eq('date', today).execute()
            
            if response.data:
                new_count = response.data[0]['count'] + 1
                new_wins = response.data[0]['wins'] + (1 if won else 0)
                supabase.table('duels').update({'count': new_count, 'wins': new_wins}).eq('user_id', user_id).eq('date', today).execute()
                
                # Обновляем статистику пользователя для ачивок
                user_data = get_user_data(user_id)
                stats = user_data.get("stats", {})
                stats["duel_wins"] = stats.get("duel_wins", 0) + (1 if won else 0)
                stats["duel_total"] = stats.get("duel_total", 0) + 1
                user_data["stats"] = stats
                update_user_data(user_id, user_data)
                
                # Проверяем достижения
                check_achievements(user_id)
            else:
                supabase.table('duels').insert({
                    'user_id': user_id,
                    'date': today,
                    'count': 1,
                    'wins': 1 if won else 0
                }).execute()
                
                # Обновляем статистику пользователя для ачивок
                user_data = get_user_data(user_id)
                stats = user_data.get("stats", {})
                stats["duel_wins"] = stats.get("duel_wins", 0) + (1 if won else 0)
                stats["duel_total"] = stats.get("duel_total", 0) + 1
                user_data["stats"] = stats
                update_user_data(user_id, user_data)
                
                # Проверяем достижения
                check_achievements(user_id)
        except Exception as e:
            print(f"[ERROR] increment_duel_count: {e}")