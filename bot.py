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
            
            # Прямое чтение из БД
            from supabase_db import supabase
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
            
            # Выполняем команду
            result = await func(ctx, *args, **kwargs)
            
            # Обновляем время
            supabase.table('users').update({f'last_{command_name}': datetime.now().isoformat()}).eq('user_id', user_id).execute()
            
            return result
        return wrapper
    return decorator

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

@bot.command(name='тестсупа')
@in_command_channel()
async def test_supa(ctx):
    """Прямой тест Supabase"""
    user_id = ctx.author.id
    
    try:
        from supabase_db import supabase
        
        # Пытаемся добавить 100
        response = supabase.table('users').select('balance').eq('user_id', user_id).execute()
        
        if response.data:
            current = response.data[0]['balance']
            new_balance = current + 100
            supabase.table('users').update({'balance': new_balance}).eq('user_id', user_id).execute()
            await ctx.send(f"✅ Баланс обновлён: {current} -> {new_balance}")
        else:
            supabase.table('users').insert({
                'user_id': user_id,
                'balance': 100,
                'artifacts': '{}',
                'cards': '[]',
                'completed_combos': '[]'
            }).execute()
            await ctx.send(f"✅ Пользователь создан, баланс: 100")
            
    except Exception as e:
        await ctx.send(f"❌ Ошибка: {e}")
        print(f"[ERROR] test_supa: {e}")
        import traceback
        traceback.print_exc()
        
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
        
        from supabase_db import supabase
        
        # Получаем текущий баланс
        response = supabase.table('users').select('balance').eq('user_id', user_id).execute()
        
        if response.data:
            current = response.data[0]['balance']
            new_balance = current + base_reward
            supabase.table('users').update({'balance': new_balance}).eq('user_id', user_id).execute()
        else:
            new_balance = base_reward
            supabase.table('users').insert({
                'user_id': user_id,
                'balance': new_balance,
                'artifacts': '{}',
                'cards': '[]',
                'completed_combos': '[]'
            }).execute()
        
        print(f"[PRAY] {user_id}: +{base_reward} -> {new_balance}")
        
        embed = create_embed(
            title=f"{EMOJIS['pray']} Вы помолились Биберу!",
            description=f"**{work['name']}**\n\n"
                       f"Получено: +{base_reward} {EMOJIS['bibsy']}\n"
                       f"Баланс: {new_balance} {EMOJIS['bibsy']}",
            color=discord.Color.green(),
            image="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaHVhcnFnMmVxYmxzdXVnYTZ6Zjd5dm8xa29oeTdteWZhcnZlbzJ5aiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/t9oU3BYnF7fGDtl5PJ/giphy.gif",
            footer="Твой вклад в культуру Бибера"
        )
        
        await loading.stop(True, "Молитва принята!")
        await ctx.send(embed=embed)
        log_action(user_id, "pray", f"Work: {work['name']}, Reward: {base_reward}")
        
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
        
        new_balance = add_balance(user_id, total_reward)
        
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
        import traceback
        traceback.print_exc()
        await loading.stop(False, f"Ошибка: {str(e)[:50]}")
        raise e

@bot.command(name='экстаз')
@in_command_channel()
@cooldown("ecstasy")
@add_command_reaction("экстаз")
async def ecstasy(ctx):
    loading = LoadingAnimation(ctx, "Достижение экстаза", "✨")
    await loading.start()
    
    try:
        user_id = ctx.author.id
        
        if random.random() <= 0.05:
            reward = 3500
            new_balance = add_balance(user_id, reward)
            
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
            new_balance = add_balance(user_id, -penalty)
            
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
        import traceback
        traceback.print_exc()
        await loading.stop(False, f"Ошибка: {str(e)[:50]}")
        raise e

@bot.command(name='покаяться')
@in_command_channel()
@cooldown("repent")
@add_command_reaction("покаяться")
async def repent(ctx):
    loading = LoadingAnimation(ctx, "Покаяние", "😢")
    await loading.start()
    
    try:
        user_id = ctx.author.id
        
        if random.random() <= 0.5:
            bonuses = [
                {"text": "Ты покаялся в том, что слушал другого исполнителя... но вовремя вернулся.", "reward": 100},
                {"text": "Ты признался, что однажды назвал его \"попсой\", но внутри плакал.", "reward": 70},
                {"text": "Ты удалил все каверы на его песни. Мир стал чище.", "reward": 120},
                {"text": "Ты разослал 10 людям \"Sorry\" как миссионер.", "reward": 90},
                {"text": "Ты отстоял Бибера в споре с незнающим. Громко. И с матами.", "reward": 80}
            ]
            bonus = random.choice(bonuses)
            new_balance = add_balance(user_id, bonus["reward"])
            
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
            new_balance = add_balance(user_id, -penalty["penalty"])
            
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
        import traceback
        traceback.print_exc()
        await loading.stop(False, f"Ошибка: {str(e)[:50]}")
        raise e

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

# ==================== КАРТОЧКИ ====================

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

# ==================== КОМБИНАЦИИ ====================

user_command_history = {}

async def check_combos(ctx):
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

# ==================== АРТЕФАКТЫ ====================

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
    
    if item["type"] == "role" and user_data.get("personal_role"):
        await ctx.send(embed=create_embed("Ошибка", "У вас уже есть личная роль!", discord.Color.red()))
        return
    
    if item["type"] == "tag" and user_data.get("personal_tag"):
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

@bot.command(name='сброситькулдаун')
@commands.has_role(ADMIN_ROLE)
@in_command_channel()
async def reset_cooldown(ctx, member: discord.Member = None):
    """Сбросить кулдауны пользователя (только для Admin)"""
    target = member or ctx.author
    
    # Получаем данные пользователя
    user_data = get_user_data(target.id)
    
    # Сбрасываем все кулдауны
    user_data["last_pray"] = None
    user_data["last_sermon"] = None
    user_data["last_repent"] = None
    user_data["last_ecstasy"] = None
    user_data["last_proposal"] = None
    user_data["last_divorce"] = None
    
    update_user_data(target.id, user_data)
    
    embed = create_embed(
        "✅ Кулдаун сброшен",
        f"Кулдауны для {target.mention} сброшены!",
        discord.Color.green()
    )
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "reset_cooldown", f"Target: {target.id}")
# ==================== ФОНОВЫЕ ЗАДАЧИ ====================

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

# ==================== ВЕБ-СЕРВЕР ====================
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
        app.run(host='0.0.0.0', port=10000)
    
    Thread(target=run_web, daemon=True).start()
    print("🌐 Веб-сервер запущен на порту 10000")
except ImportError:
    print("⚠️ Flask не установлен")

# ==================== ЗАПУСК ====================
@bot.event
async def setup_hook():
    # Фоновые задачи
    if not bieber_escape_task.is_running():
        bieber_escape_task.start()
    
    # Очистка старых дуэлей
    DuelManager.cleanup_old_duels()

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
        embed = create_embed("❌ Не хватает аргументов", f"Использование: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`", discord.Color.red())
        await ctx.send(embed=embed, delete_after=10)
    else:
        print(f"Ошибка: {error}")
        embed = create_embed("❌ Ошибка", f"Произошла ошибка: {str(error)[:100]}", discord.Color.red())
        await ctx.send(embed=embed, delete_after=10)

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    bot.run(TOKEN)