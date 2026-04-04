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

# ==================== ФУНКЦИИ ДЛЯ ЛОГИРОВАНИЯ ====================

def log_action(user_id: int, command: str, details: str = ""):
    """Логирование действий"""
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
    """Добавить/убавить баланс"""
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
    """Получить баланс"""
    try:
        response = supabase.table('users').select('balance').eq('user_id', user_id).execute()
        if response.data:
            return response.data[0]['balance']
        return 0
    except Exception as e:
        print(f"[ERROR] get_balance: {e}")
        return 0

def set_balance(user_id: int, amount: int) -> int:
    """Установить точный баланс"""
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
    """Получить все данные пользователя"""
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
                "last_divorce": None
            }
        
        data = response.data[0]
        
        artifacts = json.loads(data.get('artifacts', '{}'))
        cards = json.loads(data.get('cards', '[]'))
        completed_combos = json.loads(data.get('completed_combos', '[]'))
        
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
            "last_divorce": data.get('last_divorce')
        }
    except Exception as e:
        print(f"[ERROR] get_user_data: {e}")
        return {"balance": 0, "artifacts": {}, "cards": [], "completed_combos": []}

def update_user_data(user_id: int, data: dict):
    """Обновить данные пользователя"""
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
            'last_divorce': data.get('last_divorce')
        }).eq('user_id', user_id).execute()
    except Exception as e:
        print(f"[ERROR] update_user_data: {e}")

# ==================== ФУНКЦИИ ДЛЯ КАРТОЧЕК ====================

def add_card_to_user(user_id: int, card_id: str) -> bool:
    """Добавить карточку пользователю"""
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
    """Получить коллекцию карт пользователя"""
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

# ==================== ФУНКЦИИ ДЛЯ КОМБИНАЦИЙ ====================

def check_secret_combo(user_id: int, command_sequence: list, SECRET_COMBOS: dict) -> Optional[Tuple[str, dict]]:
    """Проверить секретную комбинацию"""
    combo_str = "→".join(command_sequence)
    
    if combo_str in SECRET_COMBOS:
        response = supabase.table('users').select('completed_combos').eq('user_id', user_id).execute()
        completed = []
        
        if response.data and response.data[0].get('completed_combos'):
            completed = json.loads(response.data[0]['completed_combos'])
        
        if combo_str in completed:
            return None
        
        return (combo_str, SECRET_COMBOS[combo_str])
    
    return None

def complete_combo(user_id: int, combo_str: str):
    """Отметить комбинацию как выполненную"""
    try:
        response = supabase.table('users').select('completed_combos').eq('user_id', user_id).execute()
        completed = []
        
        if response.data and response.data[0].get('completed_combos'):
            completed = json.loads(response.data[0]['completed_combos'])
        
        if combo_str not in completed:
            completed.append(combo_str)
            supabase.table('users').update({'completed_combos': json.dumps(completed)}).eq('user_id', user_id).execute()
    except Exception as e:
        print(f"[ERROR] complete_combo: {e}")


# ==================== ФУНКЦИИ ДЛЯ СЕМЬИ ====================

def get_family_by_member(user_id: int) -> Optional[dict]:
    """Получить семью по участнику"""
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
    """Создать новую семью"""
    try:
        result = supabase.table('families').insert({
            'spouse1_id': spouse1_id,
            'spouse2_id': spouse2_id,
            'family_name': family_name,
            'children': '[]'
        }).execute()
        return result.data[0]['family_id']
    except Exception as e:
        print(f"[ERROR] create_family: {e}")
        return 0

def update_family(family_id: int, data: dict):
    """Обновить данные семьи"""
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
    """Получить семью по ID"""
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
    """Добавить ребенка в семью (максимум 5 детей)"""
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
    """Удалить ребенка из семьи"""
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

def upgrade_family(family_id: int, FAMILY_UPGRADE_COSTS: dict) -> bool:
    """Улучшить уровень семьи"""
    try:
        family = get_family(family_id)
        if not family or family['level'] >= 5:
            return False
        
        cost = FAMILY_UPGRADE_COSTS.get(family['level'] + 1, 50000)
        spouse1_balance = get_balance(family['spouse1_id'])
        spouse2_balance = get_balance(family['spouse2_id'])
        total_balance = spouse1_balance + spouse2_balance
        
        if total_balance < cost:
            return False
        
        half_cost = cost // 2
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
        return True
    except Exception as e:
        print(f"[ERROR] upgrade_family: {e}")
        return False

# ==================== ФУНКЦИИ ДЛЯ ПРЕДЛОЖЕНИЙ ====================

def create_marriage_proposal(from_id: int, to_id: int, proposal_text: str) -> int:
    """Создать предложение о браке"""
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
    """Получить предложение о браке"""
    try:
        response = supabase.table('marriage_proposals').select('*').eq('proposal_id', proposal_id).execute()
        if not response.data:
            return None
        return response.data[0]
    except Exception as e:
        print(f"[ERROR] get_marriage_proposal: {e}")
        return None

def delete_marriage_proposal(proposal_id: int):
    """Удалить предложение о браке"""
    try:
        supabase.table('marriage_proposals').delete().eq('proposal_id', proposal_id).execute()
    except Exception as e:
        print(f"[ERROR] delete_marriage_proposal: {e}")

# ==================== ФУНКЦИИ ДЛЯ ПОДАРКОВ ====================

def send_gift(from_user_id: int, to_user_id: int, gift_type: str, message: str):
    """Отправить подарок"""
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
    """Получить подарки пользователя"""
    try:
        response = supabase.table('gifts').select('*').eq('to_user_id', user_id).order('timestamp', desc=True).execute()
        return response.data
    except Exception as e:
        print(f"[ERROR] get_user_gifts: {e}")
        return []

def get_gift_stats() -> List[dict]:
    """Получить статистику подарков"""
    try:
        response = supabase.table('gifts').select('to_user_id, count:to_user_id').execute()
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
    """Добавить признание"""
    try:
        supabase.table('confessions').insert({
            'confession_text': confession_text,
            'timestamp': datetime.now().isoformat()
        }).execute()
    except Exception as e:
        print(f"[ERROR] add_confession: {e}")

# ==================== ФУНКЦИИ ДЛЯ ЛОВЛИ БИБЕРА ====================

def get_bieber_catch_stats(user_id: int) -> dict:
    """Получить статистику ловли Бибера"""
    try:
        response = supabase.table('bieber_catch').select('catches, fake_catches').eq('user_id', user_id).execute()
        if response.data:
            return {"catches": response.data[0]['catches'], "fake_catches": response.data[0]['fake_catches']}
        return {"catches": 0, "fake_catches": 0}
    except Exception as e:
        print(f"[ERROR] get_bieber_catch_stats: {e}")
        return {"catches": 0, "fake_catches": 0}

def update_bieber_catch_stats(user_id: int, real_catch: bool = True):
    """Обновить статистику ловли Бибера"""
    try:
        if real_catch:
            supabase.rpc('increment_catch', {'user_id': user_id}).execute()
        else:
            supabase.rpc('increment_fake_catch', {'user_id': user_id}).execute()
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
            else:
                supabase.table('duels').insert({
                    'user_id': user_id,
                    'date': today,
                    'count': 1,
                    'wins': 1 if won else 0
                }).execute()
        except Exception as e:
            print(f"[ERROR] increment_duel_count: {e}")