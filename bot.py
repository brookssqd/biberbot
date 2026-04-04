import discord
from discord.ext import commands, tasks
import random
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional
import os
from functools import wraps

# Импортируем данные и функции
from bot_data import *
from supabase_db import *

# ==================== НАСТРОЙКИ ====================
TOKEN = os.environ.get('TOKEN')

if not TOKEN:
    print("❌ ОШИБКА: TOKEN не задан в переменных окружения!")
    exit(1)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ==================== СЕКРЕТНЫЕ КОМБИНАЦИИ ====================

user_command_history = {}

def check_secret_combo(user_id: int, command_sequence: list, SECRET_COMBOS: dict):
    combo_str = "→".join(command_sequence)
    
    if combo_str in SECRET_COMBOS:
        from supabase_db import supabase
        import json
        
        response = supabase.table('users').select('completed_combos').eq('user_id', user_id).execute()
        completed = []
        
        if response.data and response.data[0].get('completed_combos'):
            completed = json.loads(response.data[0]['completed_combos'])
        
        if combo_str in completed:
            return None
        
        return (combo_str, SECRET_COMBOS[combo_str])
    
    return None

def complete_combo(user_id: int, combo_str: str):
    from supabase_db import supabase
    import json
    
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

async def check_combos(ctx):
    from bot_data import SECRET_COMBOS
    from supabase_db import add_balance, add_card_to_user
    from bot_data import COLLECTIBLE_CARDS
    
    user_id = ctx.author.id
    
    if user_id not in user_command_history:
        user_command_history[user_id] = []
    
    user_command_history[user_id].append(ctx.command.name)
    
    if len(user_command_history[user_id]) > 10:
        user_command_history[user_id] = user_command_history[user_id][-10:]
    
    for length in range(2, min(8, len(user_command_history[user_id]) + 1)):
        sequence = user_command_history[user_id][-length:]
        result = check_secret_combo(user_id, sequence, SECRET_COMBOS)
        
        if result:
            combo_str, combo_data = result
            
            add_balance(user_id, combo_data["reward"])
            
            card_reward = ""
            if "card" in combo_data:
                if add_card_to_user(user_id, combo_data["card"]):
                    card_info = COLLECTIBLE_CARDS[combo_data["card"]]
                    card_reward = f"\n🎴 Получена карта: **{card_info['name']}** {card_info['emoji']}"
            
            complete_combo(user_id, combo_str)
            
            embed = create_embed(
                title="🥷 СЕКРЕТНАЯ КОМБИНАЦИЯ!",
                description=f"{combo_data['message']}{card_reward}\n\n✨ Редкость: **{combo_data['rarity'].upper()}**",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
            break
        
# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

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
    def decorator(func):
        @wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            user_id = ctx.author.id
            
            response = supabase.table('users').select(f'last_{command_name}').eq('user_id', user_id).execute()
            last_time_str = None
            if response.data:
                last_time_str = response.data[0].get(f'last_{command_name}')
            
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
                    print(f"[ERROR] cooldown: {e}")
            
            result = await func(ctx, *args, **kwargs)
            
            supabase.table('users').update({f'last_{command_name}': datetime.now().isoformat()}).eq('user_id', user_id).execute()
            
            return result
        return wrapper
    return decorator
# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

@bot.command(name='молиться')
@in_command_channel()
@add_command_reaction("молиться")
@cooldown("pray")
async def pray(ctx):
    loading = LoadingAnimation(ctx, "Молитва обрабатывается", "🙏")
    await loading.start()
    
    try:
        user_id = ctx.author.id
        work = random.choice(WORK_OPTIONS)
        base_reward = work["reward"]
        
        user_data = get_user_data(user_id)
        bonus_percent = 0
        for artifact_id in user_data.get("artifacts", {}):
            if artifact_id in SHOP_ITEMS:
                artifact = SHOP_ITEMS[artifact_id]
                if artifact["type"] in ["permanent", "legendary"]:
                    if artifact["effect"]["command"] == "pray":
                        bonus_percent += artifact["effect"]["bonus"]
        bonus_percent = min(bonus_percent, 300)
        bonus = int(base_reward * bonus_percent / 100)
        total_reward = base_reward + bonus
        
        response = supabase.table('users').select('balance').eq('user_id', user_id).execute()
        
        if response.data:
            current = response.data[0]['balance']
            new_balance = current + total_reward
            supabase.table('users').update({'balance': new_balance}).eq('user_id', user_id).execute()
        else:
            new_balance = total_reward
            supabase.table('users').insert({
                'user_id': user_id,
                'balance': new_balance,
                'artifacts': '{}',
                'cards': '[]',
                'completed_combos': '[]'
            }).execute()
        
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
        log_action(user_id, "pray", f"Work: {work['name']}, Reward: {total_reward}")
        
    except Exception as e:
        print(f"[ERROR] pray: {e}")
        await loading.stop(False, f"Ошибка: {str(e)[:50]}")

@bot.command(name='проповедь')
@in_command_channel()
@add_command_reaction("проповедь")
@cooldown("sermon")
async def sermon(ctx):
    loading = LoadingAnimation(ctx, "Проповедь подготавливается", "📖")
    await loading.start()
    
    try:
        user_id = ctx.author.id
        sermon_data = random.choice(SERMONS)
        base_reward = sermon_data["reward"]
        
        user_data = get_user_data(user_id)
        bonus_percent = 0
        for artifact_id in user_data.get("artifacts", {}):
            if artifact_id in SHOP_ITEMS:
                artifact = SHOP_ITEMS[artifact_id]
                if artifact["type"] in ["permanent", "legendary"]:
                    if artifact["effect"]["command"] == "sermon":
                        bonus_percent += artifact["effect"]["bonus"]
        bonus_percent = min(bonus_percent, 300)
        bonus = int(base_reward * bonus_percent / 100)
        total_reward = base_reward + bonus
        
        response = supabase.table('users').select('balance').eq('user_id', user_id).execute()
        
        if response.data:
            current = response.data[0]['balance']
            new_balance = current + total_reward
            supabase.table('users').update({'balance': new_balance}).eq('user_id', user_id).execute()
        else:
            new_balance = total_reward
            supabase.table('users').insert({
                'user_id': user_id,
                'balance': new_balance,
                'artifacts': '{}',
                'cards': '[]',
                'completed_combos': '[]'
            }).execute()
        
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
        log_action(user_id, "sermon", f"Reward: {total_reward}")
        
    except Exception as e:
        print(f"[ERROR] sermon: {e}")
        await loading.stop(False, f"Ошибка: {str(e)[:50]}")

@bot.command(name='экстаз')
@in_command_channel()
@add_command_reaction("экстаз")
@cooldown("ecstasy")
async def ecstasy(ctx):
    loading = LoadingAnimation(ctx, "Достижение экстаза", "✨")
    await loading.start()
    
    try:
        user_id = ctx.author.id
        
        response = supabase.table('users').select('balance').eq('user_id', user_id).execute()
        if not response.data:
            supabase.table('users').insert({
                'user_id': user_id,
                'balance': 0,
                'artifacts': '{}',
                'cards': '[]',
                'completed_combos': '[]'
            }).execute()
        
        if random.random() <= 0.05:
            reward = 3500
            
            current_response = supabase.table('users').select('balance').eq('user_id', user_id).execute()
            current = current_response.data[0]['balance'] if current_response.data else 0
            new_balance = current + reward
            supabase.table('users').update({'balance': new_balance}).eq('user_id', user_id).execute()
            
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
            log_action(user_id, "ecstasy", f"Success, Reward: {reward}")
        else:
            penalty = 200
            
            current_response = supabase.table('users').select('balance').eq('user_id', user_id).execute()
            current = current_response.data[0]['balance'] if current_response.data else 0
            new_balance = current - penalty
            supabase.table('users').update({'balance': new_balance}).eq('user_id', user_id).execute()
            
            embed = create_embed(
                title=f"{EMOJIS['lose']} Неудача!",
                description=f"Вы попытались достичь экстаза, но потерпели неудачу.\n\nПотеряно: -{penalty} {EMOJIS['bibsy']}\nБаланс: {new_balance} {EMOJIS['bibsy']}",
                color=discord.Color.red(),
                image="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExeTJtejhwa2dqNHk0NzQyZ3oweDI2a2lzbGZ5Mnk4YTVhaWs5MmlsMiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/DyfH7ypKAMUX00uywk/giphy.gif"
            )
            
            await loading.stop(False, "Экстаз не удался")
            await ctx.send(embed=embed)
            log_action(user_id, "ecstasy", f"Fail, Penalty: {penalty}")
            
    except Exception as e:
        print(f"[ERROR] ecstasy: {e}")
        await loading.stop(False, f"Ошибка: {str(e)[:50]}")

@bot.command(name='покаяться')
@in_command_channel()
@add_command_reaction("покаяться")
@cooldown("repent")
async def repent(ctx):
    loading = LoadingAnimation(ctx, "Покаяние", "😢")
    await loading.start()
    
    try:
        user_id = ctx.author.id
        
        response = supabase.table('users').select('balance').eq('user_id', user_id).execute()
        if not response.data:
            supabase.table('users').insert({
                'user_id': user_id,
                'balance': 0,
                'artifacts': '{}',
                'cards': '[]',
                'completed_combos': '[]'
            }).execute()
        
        if random.random() <= 0.5:
            bonuses = [
                {"text": "Ты покаялся в том, что слушал другого исполнителя... но вовремя вернулся.", "reward": 100},
                {"text": "Ты признался, что однажды назвал его \"попсой\", но внутри плакал.", "reward": 70},
                {"text": "Ты удалил все каверы на его песни. Мир стал чище.", "reward": 120},
                {"text": "Ты разослал 10 людям \"Sorry\" как миссионер.", "reward": 90},
                {"text": "Ты отстоял Бибера в споре с незнающим. Громко. И с матами.", "reward": 80}
            ]
            bonus = random.choice(bonuses)
            
            current_response = supabase.table('users').select('balance').eq('user_id', user_id).execute()
            current = current_response.data[0]['balance'] if current_response.data else 0
            new_balance = current + bonus["reward"]
            supabase.table('users').update({'balance': new_balance}).eq('user_id', user_id).execute()
            
            await try_drop_card(ctx, "покаяться")
            await check_combos(ctx)
            
            embed = create_embed(
                title=f"{EMOJIS['win']} Покаяние принято!",
                description=f"{bonus['text']}\n\nПолучено: +{bonus['reward']} {EMOJIS['bibsy']}\nБаланс: {new_balance} {EMOJIS['bibsy']}",
                color=discord.Color.green()
            )
            
            await loading.stop(True, "Ты прощен!")
            await ctx.send(embed=embed)
            log_action(user_id, "repent", f"Success, Reward: {bonus['reward']}")
        else:
            penalties = [
                {"text": "Ты тайком слушал Селену. И тебе понравилось.", "penalty": 50},
                {"text": "Ты сказал \"одна и та же песня\", хотя это был ремикс.", "penalty": 30},
                {"text": "Ты проигнорировал сторис Бибера. Он заметил.", "penalty": 40},
                {"text": "Ты произнёс: \"Когда-то он был лучше...\"", "penalty": 80},
                {"text": "Ты забыл дату выхода \"Purpose\". Это непростительно.", "penalty": 80}
            ]
            penalty = random.choice(penalties)
            
            current_response = supabase.table('users').select('balance').eq('user_id', user_id).execute()
            current = current_response.data[0]['balance'] if current_response.data else 0
            new_balance = current - penalty["penalty"]
            supabase.table('users').update({'balance': new_balance}).eq('user_id', user_id).execute()
            
            embed = create_embed(
                title=f"{EMOJIS['lose']} Покаяние не принято!",
                description=f"{penalty['text']}\n\nПотеряно: -{penalty['penalty']} {EMOJIS['bibsy']}\nБаланс: {new_balance} {EMOJIS['bibsy']}",
                color=discord.Color.red()
            )
            
            await loading.stop(False, "Покаяние отклонено")
            await ctx.send(embed=embed)
            log_action(user_id, "repent", f"Fail, Penalty: {penalty['penalty']}")
            
    except Exception as e:
        print(f"[ERROR] repent: {e}")
        await loading.stop(False, f"Ошибка: {str(e)[:50]}")

# ==================== КАРТОЧКИ И КОМБИНАЦИИ ====================

async def try_drop_card(ctx, command: str):
    user_id = ctx.author.id
    current_time = datetime.now()
    
    if user_id in user_last_card_drop:
        time_since_last = (current_time - user_last_card_drop[user_id]).total_seconds()
        if time_since_last < CARD_DROP_COOLDOWN:
            return False
    
    chances = {
        "молиться": 8,
        "проповедь": 8,
        "экстаз": 5,
        "покаяться": 3,
        "дуэль": 4,
        "подарок": 2
    }
    
    chance = chances.get(command, 1)
    
    if random.randint(1, 100) <= chance:
        cards_list = list(COLLECTIBLE_CARDS.keys())
        weights = {
            "baby_jb": 30,
            "purpose_jb": 20,
            "bieber_christmas": 15,
            "changes_jb": 15,
            "bieber_acoustic": 10,
            "justice_jb": 5,
            "bieber_demon": 4,
            "bieber_ghost": 2,
            "bieber_angel": 1
        }
        card_id = random.choices(cards_list, weights=[weights.get(c, 10) for c in cards_list])[0]
        card_info = COLLECTIBLE_CARDS[card_id]
        
        if add_card_to_user(user_id, card_id):
            user_last_card_drop[user_id] = current_time
            
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

@bot.command(name='коллекция')
@in_command_channel()
async def show_collection(ctx, member: discord.Member = None):
    target = member or ctx.author
    collection = get_user_cards_collection(target.id)
    
    percent = int(collection['total'] / collection['total_possible'] * 100) if collection['total_possible'] > 0 else 0
    
    embed = create_embed(
        title=f"{EMOJIS['card']} Коллекция карт {target.display_name}",
        description=f"Собрано **{collection['total']}** из **{collection['total_possible']}** карт ({percent}%)",
        color=discord.Color.gold(),
        footer="Собирай все карты Бибера! Новая карта раз в 12 часов"
    )
    
    rarities = ["mythic", "legendary", "epic", "rare", "common"]
    rarity_names = {"mythic": "🌟 Мифические", "legendary": "👑 Легендарные", 
                   "epic": "⚡ Эпические", "rare": "💎 Редкие", "common": "📦 Обычные"}
    
    for rarity in rarities:
        if collection[rarity]:
            cards_list = []
            for card_id in collection[rarity]:
                card = COLLECTIBLE_CARDS[card_id]
                cards_list.append(f"{card['emoji']} {card['name']}")
            embed.add_field(
                name=rarity_names[rarity],
                value="\n".join(cards_list),
                inline=False
            )
    
    if collection['total'] == collection['total_possible']:
        embed.description += "\n\n🎉 **ПОЛНАЯ КОЛЛЕКЦИЯ!** 🎉\nТы настоящий коллекционер!"
        embed.color = discord.Color.magenta()
    
    await ctx.send(embed=embed)

@bot.command(name='картакд')
@in_command_channel()
async def card_cooldown(ctx):
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
    
    embed = create_embed(
        title="⏳ Кулдаун карт",
        description=f"Следующая карта выпадет через:\n"
                   f"**{remaining_hours}ч {remaining_minutes}м**",
        color=discord.Color.gold(),
        footer="После выпадения карты кулдаун обновится"
    )
    
    await ctx.send(embed=embed)

@bot.command(name='шансыкарт')
@in_command_channel()
async def card_chances(ctx):
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
    
    await ctx.send(embed=embed)

@bot.command(name='баланс')
@in_command_channel()
async def balance(ctx, member: discord.Member = None):
    target = member or ctx.author
    bal = get_balance(target.id)
    
    embed = create_embed(
        f"Баланс {target.display_name}",
        f"{bal} {EMOJIS['bibsy']}",
        discord.Color.gold(),
        image="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExODJ4MnFwdnd0eTZxcWRxYTQ0d29wM3V0NGVvMG9jcWw0dTZ5b3M3MyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/QourcDyAyKQI0IR66R/giphy.gif"
    )
    await ctx.send(embed=embed)

# ==================== СОЦИАЛЬНЫЕ КОМАНДЫ ====================

@bot.command(name='поцелуй')
@in_command_channel()
@add_command_reaction("поцелуй")
async def kiss(ctx, member: discord.Member):
    if member == ctx.author:
        embed = create_embed("❌ Ошибка", "Нельзя поцеловать себя!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    context = random.choice(KISS_CONTEXTS)
    embed = create_embed(
        "💋 Поцелуй",
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
        embed = create_embed("❌ Ошибка", "Нельзя обнять себя!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    context = random.choice(HUG_CONTEXTS)
    embed = create_embed(
        "🤗 Объятия",
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
        embed = create_embed("❌ Ошибка", "Нельзя ударить себя!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    context = random.choice(HIT_CONTEXTS)
    embed = create_embed(
        "👊 Удар",
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
        embed = create_embed("❌ Ошибка", "Нельзя угостить себя!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    context = random.choice(TREAT_CONTEXTS)
    embed = create_embed(
        "🍬 Угощение",
        f"{ctx.author.mention} {context['text']} {member.mention}!",
        discord.Color.green(),
        image=context['gif']
    )
    await ctx.send(embed=embed)

@bot.command(name='любовь')
@in_command_channel()
@add_command_reaction("любовь")
async def make_love(ctx, member: discord.Member):
    if member == ctx.author:
        embed = create_embed("❌ Ошибка", "Нельзя с самим собой!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    context = random.choice(LOVE_CONTEXTS)
    embed = create_embed(
        "💖 Любовь",
        f"{ctx.author.mention} {context['text']} с {member.mention}!",
        discord.Color.red(),
        image=context['gif']
    )
    await ctx.send(embed=embed)

@bot.command(name='комплимент')
@in_command_channel()
async def compliment(ctx, member: discord.Member = None):
    target = member or ctx.author
    balance_val = get_balance(target.id)
    
    if balance_val >= 10000:
        template = random.choice(PERSONALIZED_COMPLIMENTS["balance_milestone"])
        compliment_text = template.format(balance=balance_val, emoji=EMOJIS["bibsy"], name=target.display_name)
    else:
        template = random.choice(PERSONALIZED_COMPLIMENTS["random"])
        compliment_text = template.format(name=target.display_name, role=random.choice(["герой", "легенда", "звезда", "фанат года"]))
    
    embed = create_embed(
        "💝 Персональный комплимент",
        compliment_text,
        discord.Color.pink(),
        author=target,
        footer="Бибер тебя заметил!"
    )
    await ctx.send(embed=embed)

# ==================== ПЕРЕВОД ДЕНЕГ ====================

@bot.command(name='передать')
@in_command_channel()
@add_command_reaction("передать")
async def transfer_money(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        embed = create_embed("❌ Ошибка", "Сумма должна быть положительной!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if member == ctx.author:
        embed = create_embed("❌ Ошибка", "Нельзя передавать деньги самому себе!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    sender_balance = get_balance(ctx.author.id)
    fee = int(amount * TRANSFER_FEE)
    total_cost = amount + fee
    
    if sender_balance < total_cost:
        embed = create_embed(
            "❌ Недостаточно средств",
            f"Нужно: {total_cost} {EMOJIS['bibsy']} (включая комиссию {fee})\nУ вас: {sender_balance} {EMOJIS['bibsy']}",
            discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    add_balance(ctx.author.id, -total_cost)
    add_balance(member.id, amount)
    
    embed = create_embed(
        "✅ Успешный перевод!",
        f"{ctx.author.mention} передал {member.mention} {amount} {EMOJIS['bibsy']}\n"
        f"Комиссия: {fee} {EMOJIS['bibsy']}",
        discord.Color.green()
    )
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "transfer", f"To: {member.id}, Amount: {amount}, Fee: {fee}")

# ==================== МАГАЗИН И АРТЕФАКТЫ ====================

class ArtifactManager:
    @staticmethod
    def calculate_bonus(user_id: int, command: str, base_reward: int) -> int:
        user_data = get_user_data(user_id)
        artifacts = user_data.get("artifacts", {})
        total_bonus_percent = 0
        
        for artifact_id in artifacts:
            if artifact_id in SHOP_ITEMS:
                artifact = SHOP_ITEMS[artifact_id]
                if artifact["type"] in ["permanent", "legendary"]:
                    if artifact["effect"]["command"] == command:
                        total_bonus_percent += artifact["effect"]["bonus"]
        
        total_bonus_percent = min(total_bonus_percent, 300)
        bonus = int(base_reward * total_bonus_percent / 100)
        return bonus
    
    @staticmethod
    def add_artifact(user_id: int, artifact_id: str) -> bool:
        if artifact_id not in SHOP_ITEMS:
            return False
        
        user_data = get_user_data(user_id)
        
        if artifact_id in user_data.get("artifacts", {}):
            if SHOP_ITEMS[artifact_id]["type"] in ["permanent", "legendary"]:
                return False
        
        user_data["artifacts"][artifact_id] = {}
        update_user_data(user_id, user_data)
        log_action(user_id, "add_artifact", artifact_id)
        return True

@bot.command(name='магазин')
@in_command_channel()
async def shop(ctx):
    embed = create_embed("🛒 Магазин артефактов", "", discord.Color.purple())
    
    for item_id, item in SHOP_ITEMS.items():
        if item["type"] in ["permanent", "legendary"]:
            cmd = "молиться" if item["effect"]["command"] == "pray" else "проповедь"
            effect = f"+{item['effect']['bonus']}% к !{cmd}"
        elif item["type"] == "role":
            effect = "👑 Личная роль на сервере"
        elif item["type"] == "tag":
            effect = "🏷️ Личный тег"
        else:
            effect = "🎁 Особый эффект"
        
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
        embed = create_embed("❌ Ошибка", "Товар не найден!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    item = SHOP_ITEMS[item_id]
    user_data = get_user_data(ctx.author.id)
    
    if user_data["balance"] < item["price"]:
        embed = create_embed("❌ Недостаточно средств", "", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if item["type"] == "role" and user_data.get("personal_role"):
        embed = create_embed("❌ Ошибка", "У вас уже есть личная роль!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if item["type"] == "tag" and user_data.get("personal_tag"):
        embed = create_embed("❌ Ошибка", "У вас уже есть тег!", discord.Color.red())
        await ctx.send(embed=embed)
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
    artifacts = data.get("artifacts", {})
    
    if not artifacts:
        embed = create_embed("🔮 Нет артефактов", "Посетите магазин командой `!магазин`!", discord.Color.blue())
        await ctx.send(embed=embed)
        return
    
    embed = create_embed("🔮 Ваши артефакты", "", discord.Color.blue())
    for art_id in artifacts:
        if art_id in SHOP_ITEMS:
            item = SHOP_ITEMS[art_id]
            effect = f"+{item['effect']['bonus']}% к !{'молиться' if item['effect']['command'] == 'pray' else 'проповедь'}"
            embed.add_field(name=item['name'], value=effect, inline=False)
    
    await ctx.send(embed=embed)

# ==================== СЕМЕЙНЫЕ КОМАНДЫ ====================

@bot.command(name='предложить')
@in_command_channel()
@cooldown("proposal")
@add_command_reaction("предложить")
async def propose(ctx, member: discord.Member, *, proposal_text: str):
    if member == ctx.author:
        await ctx.send(embed=create_embed("❌ Ошибка", "Нельзя сделать предложение самому себе!", discord.Color.red()))
        return
    
    if get_family_by_member(ctx.author.id):
        await ctx.send(embed=create_embed("❌ Ошибка", "Вы уже состоите в семье!", discord.Color.red()))
        return
    
    if get_family_by_member(member.id):
        await ctx.send(embed=create_embed("❌ Ошибка", "Этот пользователь уже состоит в семье!", discord.Color.red()))
        return
    
    proposal_id = create_marriage_proposal(ctx.author.id, member.id, proposal_text)
    
    embed = create_embed(
        "💍 Предложение руки и сердца!",
        f"{ctx.author.mention} делает предложение {member.mention}:\n\n*{proposal_text}*\n\n"
        f"{member.mention}, чтобы принять предложение, напишите `!принять {proposal_id}`\n"
        f"Чтобы отказаться, напишите `!отказаться {proposal_id}`",
        discord.Color.pink()
    )
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "propose", f"To: {member.id}")

@bot.command(name='принять')
@in_command_channel()
@add_command_reaction("принять")
async def accept_proposal(ctx, proposal_id: int):
    proposal = get_marriage_proposal(proposal_id)
    if not proposal or proposal["to_id"] != ctx.author.id:
        await ctx.send(embed=create_embed("❌ Ошибка", "Предложение не найдено!", discord.Color.red()))
        return
    
    if get_family_by_member(proposal["from_id"]) or get_family_by_member(proposal["to_id"]):
        await ctx.send(embed=create_embed("❌ Ошибка", "Один из вас уже состоит в семье!", discord.Color.red()))
        delete_marriage_proposal(proposal_id)
        return
    
    from_user = bot.get_user(proposal["from_id"]) or await bot.fetch_user(proposal["from_id"])
    family_name = f"{from_user.display_name} & {ctx.author.display_name}"
    family_id = create_family(proposal["from_id"], proposal["to_id"], family_name)
    delete_marriage_proposal(proposal_id)
    
    embed = create_embed(
        "✅ Новая семья создана!",
        f"Поздравляем {from_user.mention} и {ctx.author.mention}!\nНазвание: {family_name}",
        discord.Color.green()
    )
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "accept_proposal", f"Family: {family_id}")

@bot.command(name='отказаться')
@in_command_channel()
@add_command_reaction("отказаться")
async def reject_proposal(ctx, proposal_id: int):
    proposal = get_marriage_proposal(proposal_id)
    if not proposal or proposal["to_id"] != ctx.author.id:
        await ctx.send(embed=create_embed("❌ Ошибка", "Предложение не найдено!", discord.Color.red()))
        return
    
    delete_marriage_proposal(proposal_id)
    from_user = bot.get_user(proposal["from_id"]) or await bot.fetch_user(proposal["from_id"])
    
    embed = create_embed(
        "❌ Предложение отклонено",
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
        await ctx.send(embed=create_embed("❌ Ошибка", "Вы не состоите в семье!", discord.Color.red()))
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
        embed.add_field(name=f"👶 Дети ({len(family['children'])}/5)", value="\n".join(children_text), inline=False)
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
    
    if len(family["children"]) >= 5:
        embed = create_embed("❌ Ошибка", "В семье уже 5 детей! Нельзя добавить больше.", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    embed_ask = create_embed(
        "👶 Предложение стать ребёнком!",
        f"{ctx.author.mention} хочет взять вас в семью!\n\n"
        f"Родители: {ctx.author.mention}\n"
        f"Семья: **{family['family_name']}**\n\n"
        f"Вы станете {child_type} по имени **{child_name}**\n\n"
        f"Чтобы согласиться, нажмите ✅\n"
        f"Чтобы отказаться, нажмите ❌",
        discord.Color.blue()
    )
    
    msg = await ctx.send(f"{member.mention}", embed=embed_ask)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    
    def check(reaction, user):
        return user == member and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        
        if str(reaction.emoji) == "✅":
            success = add_child_to_family(family["family_id"], member.id, child_name, child_type_en)
            if not success:
                embed = create_embed("❌ Ошибка", "Не удалось добавить ребенка!", discord.Color.red())
                await ctx.send(embed=embed)
                return
            
            child_type_display = "сыном" if child_type_en == "son" else "дочерью"
            embed = create_embed(
                "✅ Ребенок добавлен!",
                f"{member.mention} стал {child_type_display} семьи **{family['family_name']}**!\n\n"
                f"Имя: {child_name}\n"
                f"Всего детей: {len(family['children'])}/5",
                discord.Color.green()
            )
            await ctx.send(embed=embed)
            log_action(ctx.author.id, "add_child", f"Child: {member.id}, Name: {child_name}, Type: {child_type}")
        else:
            embed = create_embed(
                "❌ Отказано",
                f"{member.mention} отказался стать ребёнком.",
                discord.Color.red()
            )
            await ctx.send(embed=embed)
            
    except asyncio.TimeoutError:
        embed = create_embed(
            "⏳ Время вышло",
            f"{member.mention} не ответил вовремя.",
            discord.Color.orange()
        )
        await ctx.send(embed=embed)

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
    
    if not upgrade_family(family["family_id"], FAMILY_UPGRADE_COSTS):
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
        description=f"Всего детей: {len(family['children'])}/5",
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
        await ctx.send(embed=create_embed("❌ Ошибка", "Вы не состоите в браке!", discord.Color.red()))
        return
    
    supabase.table('families').delete().eq('family_id', family["family_id"]).execute()
    
    spouse = bot.get_user(family["spouse1_id"] if ctx.author.id == family["spouse2_id"] else family["spouse1_id"])
    spouse = spouse or await bot.fetch_user(family["spouse1_id"] if ctx.author.id == family["spouse2_id"] else family["spouse1_id"])
    embed = create_embed("💔 Развод", f"Брак с {spouse.mention} расторгнут!", discord.Color.dark_grey())
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "divorce")

@bot.command(name='выйти')
@in_command_channel()
@add_command_reaction("выйти")
async def leave_family(ctx):
    family = get_family_by_member(ctx.author.id)
    if not family:
        embed = create_embed("❌ Ошибка", "Вы не состоите в семье!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    is_child = False
    for i, child in enumerate(family["children"]):
        if child["id"] == ctx.author.id:
            del family["children"][i]
            is_child = True
            break
    
    if not is_child:
        embed = create_embed("❌ Ошибка", "Только дети могут покидать семью!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    update_family(family["family_id"], family)
    embed = create_embed("✅ Успех", "Вы вышли из семьи!", discord.Color.green())
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "leave_family")

# ==================== ДУЭЛИ ====================

@bot.command(name='дуэль')
@in_command_channel()
@add_command_reaction("дуэль")
async def duel(ctx, member: discord.Member = None, amount: int = None):
    if not member or not amount:
        embed = create_embed("⚔️ Использование", "`!дуэль @участник 50-150`", discord.Color.blue())
        await ctx.send(embed=embed)
        return
    
    if not (50 <= amount <= 150):
        embed = create_embed("❌ Ошибка", "Ставка: 50-150 бибсов!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if DuelManager.get_daily_duel_count(ctx.author.id) >= 3:
        embed = create_embed("❌ Лимит", "3 дуэли в день!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if get_balance(ctx.author.id) < amount:
        embed = create_embed("❌ Недостаточно средств", "", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if DuelManager.get_duel(ctx.channel.id):
        embed = create_embed("❌ Ошибка", "Дуэль уже идет в этом канале!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    DuelManager.create_duel(ctx.channel.id, ctx.author.id, member.id, amount)
    
    embed = create_embed(
        "⚔️ Вызов на дуэль!",
        f"{ctx.author.mention} вызывает {member.mention} на дуэль!\nСтавка: {amount} {EMOJIS['bibsy']}\n\n"
        f"{member.mention}, напишите `!принять` или `!отказаться`",
        discord.Color.gold()
    )
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "duel_start", f"Target: {member.id}")

@bot.command(name='бой')
@in_command_channel()
@add_command_reaction("бой")
async def fight(ctx):
    duel_data = DuelManager.get_duel(ctx.channel.id)
    if not duel_data or not duel_data["accepted"]:
        await ctx.send(embed=create_embed("❌ Ошибка", "Дуэль не принята!", discord.Color.red()))
        return
    
    if ctx.author.id not in [duel_data["challenger_id"], duel_data["target_id"]]:
        await ctx.send(embed=create_embed("❌ Ошибка", "Вы не участник!", discord.Color.red()))
        return
    
    ready_count = DuelManager.add_fighter_ready(ctx.channel.id, ctx.author.id)
    
    if ready_count < 2:
        embed = create_embed("⚔️ Готов к бою!", f"{ctx.author.mention} готов! Ждем второго...", discord.Color.gold())
        await ctx.send(embed=embed)
        return
    
    challenger = bot.get_user(duel_data["challenger_id"]) or await bot.fetch_user(duel_data["challenger_id"])
    target = bot.get_user(duel_data["target_id"]) or await bot.fetch_user(duel_data["target_id"])
    amount = duel_data["amount"]
    
    add_balance(challenger.id, -amount)
    add_balance(target.id, -amount)
    
    winner = random.choice([challenger, target])
    reward = amount * 2
    add_balance(winner.id, reward)
    
    await try_drop_card(ctx, "дуэль")
    
    DuelManager.increment_duel_count(winner.id, True)
    DuelManager.increment_duel_count(target.id if winner == challenger else challenger.id, False)
    DuelManager.delete_duel(ctx.channel.id)
    
    embed = create_embed(
        "⚔️ Дуэль завершена!",
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
        "🏃 БИБЕР СБЕЖАЛ!",
        "Быстрее хватай его: `!поймать`",
        discord.Color.gold(),
        footer="У тебя 30 секунд!"
    )
    msg = await channel.send(embed=embed)
    bieber_game.message_id = msg.id
    
    await asyncio.sleep(30)
    
    if bieber_game.winner is None and bieber_game.active:
        bieber_game.active = False
        embed = create_embed("😢 Бибер ушел...", "Никто не поймал!", discord.Color.dark_grey())
        try:
            msg = await channel.fetch_message(bieber_game.message_id)
            await msg.edit(embed=embed)
        except:
            pass

@bot.command(name='поймать')
@in_command_channel()
@add_command_reaction("поймать")
async def catch_bieber(ctx):
    if not bieber_game.active:
        embed = create_embed(
            "😢 Бибер сбежал...",
            "Бибера сейчас нет в этом канале! Он появляется случайно, следи за сообщениями бота!",
            discord.Color.blue()
        )
        await ctx.send(embed=embed, delete_after=10)
        return
    
    if ctx.channel.id != bieber_game.channel_id:
        embed = create_embed(
            "😢 Не тот канал!",
            "Бибер не здесь! Ищи его в другом месте!",
            discord.Color.blue()
        )
        await ctx.send(embed=embed, delete_after=5)
        return
    
    if bieber_game.winner:
        embed = create_embed(
            "😢 Уже поймали!",
            f"Бибера уже поймал {bieber_game.winner.mention}! В следующий раз быстрее!",
            discord.Color.blue()
        )
        await ctx.send(embed=embed, delete_after=10)
        return
    
    bieber_game.winner = ctx.author
    bieber_game.active = False
    
    if bieber_game.fake:
        penalty = random.randint(50, 100)
        new_balance = add_balance(ctx.author.id, -penalty)
        update_bieber_catch_stats(ctx.author.id, False)
        embed = create_embed(
            "🎉 Фейк! 🎉", 
            f"{ctx.author.mention} попытался поймать, но это был фейк!\n"
            f"Потеряно: -{penalty} {EMOJIS['bibsy']}\n"
            f"Баланс: {new_balance} {EMOJIS['bibsy']}", 
            discord.Color.red()
        )
    else:
        reward = 150
        new_balance = add_balance(ctx.author.id, reward)
        update_bieber_catch_stats(ctx.author.id, True)
        embed = create_embed(
            "⭐ Поймал! ⭐", 
            f"{ctx.author.mention} поймал Бибера!\n"
            f"Получено: +{reward} {EMOJIS['bibsy']}\n"
            f"Баланс: {new_balance} {EMOJIS['bibsy']}", 
            discord.Color.green()
        )
    
    try:
        msg = await ctx.channel.fetch_message(bieber_game.message_id)
        await msg.edit(embed=embed)
    except:
        await ctx.send(embed=embed)

# ==================== ИНФОРМАЦИОННЫЕ КОМАНДЫ ====================

@bot.command(name='топ')
@in_command_channel()
async def top(ctx):
    response = supabase.table('users').select('user_id, balance').order('balance', desc=True).limit(10).execute()
    users = response.data
    
    embed = create_embed("🏆 Топ фанатов", "", discord.Color.gold())
    
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
    response = supabase.table('bieber_catch').select('user_id, catches').order('catches', desc=True).limit(10).execute()
    users = response.data
    
    embed = create_embed("🎣 Топ ловцов Бибера", "", discord.Color.gold())
    
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
    combos = len(get_user_data(target.id).get("completed_combos", []))
    
    embed = create_embed(f"📊 Статистика {target.display_name}", "", discord.Color.blue())
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
    embed = create_embed("📚 Помощь BiberBOT", "Список команд:", discord.Color.blue())
    
    embed.add_field(name="💰 Заработок", value="`!молиться` `!проповедь` `!экстаз` `!покаяться`", inline=False)
    embed.add_field(name="🎴 Коллекционирование", value="`!коллекция` `!картакд` `!шансыкарт`", inline=False)
    embed.add_field(name="🎉 Развлечения", value="`!поцелуй` `!обнять` `!ударить` `!угостить` `!любовь` `!комплимент`", inline=False)
    embed.add_field(name="🎁 Подарки", value="`!подарок` `!моиподарки` `!топподарков`", inline=False)
    embed.add_field(name="👪 Семья", value="`!предложить` `!принять` `!отказаться` `!моясемья` `!добавитьребенка` `!улучшитьсемью` `!развестись` `!дети` `!исключитьребенка` `!выйти`", inline=False)
    embed.add_field(name="🛒 Магазин", value="`!магазин` `!купить` `!артефакты`", inline=False)
    embed.add_field(name="🎮 Игры", value="`!поймать` `!дуэль` `!бой`", inline=False)
    embed.add_field(name="💸 Прочее", value="`!передать` `!признание`", inline=False)
    embed.add_field(name="ℹ Информация", value="`!баланс` `!топ` `!фанаты` `!статистика`", inline=False)
    
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
            await interaction.response.send_message("❌ Это меню не для вас!", ephemeral=True)
            return
        
        self.gift_type = select.values[0]
        await interaction.response.send_message(
            f"✅ Вы выбрали: {GIFT_TYPES[self.gift_type]} {self.gift_type}\n\n✏️ Теперь введите сообщение для получателя (до 500 символов):",
            ephemeral=True
        )
        
        def check(m):
            return m.author == self.ctx.author and m.channel == self.ctx.channel
        
        try:
            msg = await self.ctx.bot.wait_for('message', timeout=120.0, check=check)
            if len(msg.content) > 500:
                await self.ctx.send("❌ Сообщение слишком длинное! Максимум 500 символов.")
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
                "🎁 Вам подарок!",
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
            await self.ctx.send("⏳ Время вышло! Попробуйте снова.")

@bot.command(name='подарок')
@in_command_channel()
@add_command_reaction("подарок")
async def send_gift_command(ctx, member: discord.Member):
    if member == ctx.author:
        await ctx.send(embed=create_embed("❌ Ошибка", "Нельзя подарить себе!", discord.Color.red()))
        return
    
    if get_balance(ctx.author.id) < GIFT_PRICE:
        await ctx.send(embed=create_embed("❌ Недостаточно средств", f"Нужно {GIFT_PRICE} {EMOJIS['bibsy']}", discord.Color.red()))
        return
    
    view = GiftView(ctx, member)
    await ctx.send(f"🎁 Вы собираетесь подарить подарок {member.mention} за {GIFT_PRICE} {EMOJIS['bibsy']}", view=view)

@bot.command(name='моиподарки')
@in_command_channel()
async def my_gifts(ctx):
    gifts = get_user_gifts(ctx.author.id)
    if not gifts:
        await ctx.send(embed=create_embed("🎁 Подарки", "У вас нет подарков", discord.Color.blue()))
        return
    
    embed = create_embed(f"🎁 Ваши подарки ({len(gifts)})", "", discord.Color.gold())
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
        await ctx.send(embed=create_embed("🏆 Топ подарков", "Нет данных", discord.Color.blue()))
        return
    
    embed = create_embed("🏆 Топ получателей подарков", "", discord.Color.gold())
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
        await ctx.author.send("✅ Ваше признание опубликовано!")
    except:
        pass
    
    await ctx.message.delete()

# ==================== АДМИН-КОМАНДЫ ====================

@bot.command(name='выдать')
@commands.has_role(ADMIN_ROLE)
@in_command_channel()
async def give_money(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send(embed=create_embed("❌ Ошибка", "Сумма > 0", discord.Color.red()))
        return
    
    new_balance = add_balance(member.id, amount)
    await ctx.send(embed=create_embed("✅ Выдано", f"{member.mention} +{amount} {EMOJIS['bibsy']}\nНовый баланс: {new_balance} {EMOJIS['bibsy']}", discord.Color.green()))

@bot.command(name='забрать')
@commands.has_role(ADMIN_ROLE)
@in_command_channel()
async def take_money(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send(embed=create_embed("❌ Ошибка", "Сумма > 0", discord.Color.red()))
        return
    
    current = get_balance(member.id)
    take_amount = min(amount, current)
    new_balance = add_balance(member.id, -take_amount)
    await ctx.send(embed=create_embed("✅ Забрано", f"{member.mention} -{take_amount} {EMOJIS['bibsy']}\nНовый баланс: {new_balance} {EMOJIS['bibsy']}", discord.Color.green()))

@bot.command(name='сброситькулдаун')
@commands.has_role(ADMIN_ROLE)
@in_command_channel()
async def reset_cooldown(ctx, member: discord.Member = None):
    target = member or ctx.author
    
    supabase.table('users').update({
        'last_pray': None,
        'last_sermon': None,
        'last_repent': None,
        'last_ecstasy': None,
        'last_proposal': None,
        'last_divorce': None
    }).eq('user_id', target.id).execute()
    
    embed = create_embed("✅ Кулдаун сброшен", f"Кулдауны для {target.mention} сброшены!", discord.Color.green())
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "reset_cooldown", f"Target: {target.id}")

@bot.command(name='датькарту')
@commands.has_role(ADMIN_ROLE)
@in_command_channel()
async def give_card(ctx, member: discord.Member, *, card_name: str):
    found = None
    for cid, card in COLLECTIBLE_CARDS.items():
        if card_name.lower() in card['name'].lower():
            found = cid
            break
    
    if not found:
        cards_list = "\n".join([f"• {card['name']}" for card in COLLECTIBLE_CARDS.values()])
        embed = create_embed("❌ Карта не найдена", f"Доступные карты:\n{cards_list}", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if add_card_to_user(member.id, found):
        card = COLLECTIBLE_CARDS[found]
        embed = create_embed("✅ Карта выдана", f"{member.mention} получил карту **{card['name']}** {card['emoji']}!", discord.Color.green())
        await ctx.send(embed=embed)
    else:
        embed = create_embed("❌ Ошибка", f"У {member.mention} уже есть эта карта!", discord.Color.red())
        await ctx.send(embed=embed)

# ==================== ВЕБ-СЕРВЕР ====================

try:
    from flask import Flask
    from threading import Thread
    
    web_app = Flask(__name__)
    
    @web_app.route('/')
    def home():
        return "✅ BiberBOT is running 24/7!"
    
    @web_app.route('/health')
    def health():
        return "OK", 200
    
    def run_web():
        web_app.run(host='0.0.0.0', port=10000)
    
    Thread(target=run_web, daemon=True).start()
    print("🌐 Веб-сервер запущен на порту 10000")
except ImportError:
    print("⚠️ Flask не установлен, веб-сервер не запущен")

# ==================== ЗАПУСК ====================

@bot.event
async def setup_hook():
    # Запускаем фоновую задачу ловли Бибера
    if not bieber_escape_task.is_running():
        bieber_escape_task.start()
    
    # Очищаем старые дуэли
    DuelManager.cleanup_old_duels()

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user.name} готов к работе!')
    print(f'📊 Команд загружено: {len(bot.commands)}')
    print(f'🎴 Коллекционных карт: {len(COLLECTIBLE_CARDS)}')
    print(f'🔓 Секретных комбинаций: {len(SECRET_COMBOS)}')
    print(f'👨‍👩‍👧‍👦 Семейная система: до 5 детей')
    print(f'🌐 Веб-сервер: https://{os.environ.get("RENDER_EXTERNAL_HOSTNAME", "localhost")}')
    
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name=f"за {CURRENCY_NAME.lower()} | {len(bot.commands)} команд"
    )
    await bot.change_presence(activity=activity)

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

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRole):
        embed = create_embed("❌ Нет прав", "У вас нет прав для этой команды!", discord.Color.red())
        await ctx.send(embed=embed, delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_embed("❌ Не хватает аргументов", f"Использование: `{ctx.prefix}{ctx.command.name}`", discord.Color.red())
        await ctx.send(embed=embed, delete_after=10)
    else:
        print(f"❌ Ошибка: {error}")
        embed = create_embed("❌ Ошибка", f"Произошла ошибка: {str(error)[:100]}", discord.Color.red())
        await ctx.send(embed=embed, delete_after=10)

# ==================== ЗАПУСК ====================

if __name__ == "__main__":
    bot.run(TOKEN)