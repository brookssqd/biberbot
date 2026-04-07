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
        
        # Проверяем эффект удвоителя
        user_data = get_user_data(user_id)
        double = user_data.get("next_double", False)
        if double:
            user_data["next_double"] = False
            update_user_data(user_id, user_data)
            base_reward *= 2
        
        # Бонус от артефактов
        bonus_percent = get_active_bonus_percent(user_id, "pray")
        bonus = int(base_reward * bonus_percent / 100)
        total_reward = base_reward + bonus
        
        # Обновляем баланс
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
        
        # Обновляем статистику и проверяем достижения
        user_data = get_user_data(user_id)
        stats = user_data.get("stats", {})
        stats["pray_count"] = stats.get("pray_count", 0) + 1
        stats["total_earned"] = stats.get("total_earned", 0) + total_reward
        user_data["stats"] = stats
        update_user_data(user_id, user_data)
        
        # Проверяем достижения
        new_achievements = check_achievements(user_id)
        
        await try_drop_card(ctx, "молиться")
        await check_combos(ctx)
        
        double_text = " (x2 от удвоителя!)" if double else ""
        
        embed = create_embed(
            title=f"{EMOJIS['pray']} Вы помолились Биберу!",
            description=f"**{work['name']}**\n\n"
                       f"Получено: +{total_reward} {EMOJIS['bibsy']}{double_text}\n"
                       f"Баланс: {new_balance} {EMOJIS['bibsy']}",
            color=discord.Color.green(),
            image="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaHVhcnFnMmVxYmxzdXVnYTZ6Zjd5dm8xa29oeTdteWZhcnZlbzJ5aiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/t9oU3BYnF7fGDtl5PJ/giphy.gif",
            footer="Твой вклад в культуру Бибера"
        )
        
        if bonus_percent > 0:
            embed.add_field(name="✨ Бонус от артефактов", value=f"+{bonus_percent}% → +{bonus} {EMOJIS['bibsy']}", inline=False)
        
        await loading.stop(True, "Молитва принята!")
        await ctx.send(embed=embed)
        
        # Уведомление о новых достижениях
        if new_achievements:
            from supabase_db import ACHIEVEMENTS_DATA
            ach_names = ", ".join([ACHIEVEMENTS_DATA[a]["name"] for a in new_achievements])
            await ctx.send(f"🏆 **НОВОЕ ДОСТИЖЕНИЕ!** {ach_names}")
        
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
        
        # Проверяем эффект удвоителя
        user_data = get_user_data(user_id)
        double = user_data.get("next_double", False)
        if double:
            user_data["next_double"] = False
            update_user_data(user_id, user_data)
            base_reward *= 2
        
        # Бонус от артефактов
        bonus_percent = get_active_bonus_percent(user_id, "sermon")
        bonus = int(base_reward * bonus_percent / 100)
        total_reward = base_reward + bonus
        
        # Обновляем баланс
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
        
        # Обновляем статистику и проверяем достижения
        user_data = get_user_data(user_id)
        stats = user_data.get("stats", {})
        stats["sermon_count"] = stats.get("sermon_count", 0) + 1
        stats["total_earned"] = stats.get("total_earned", 0) + total_reward
        user_data["stats"] = stats
        update_user_data(user_id, user_data)
        
        # Проверяем достижения
        new_achievements = check_achievements(user_id)
        
        await try_drop_card(ctx, "проповедь")
        await check_combos(ctx)
        
        double_text = " (x2 от удвоителя!)" if double else ""
        
        embed = create_embed(
            title=f"{EMOJIS['sermon']} Проповедь о Бибере",
            description=f"*{sermon_data['text']}*\n\n"
                       f"Заработано: +{total_reward} {EMOJIS['bibsy']}{double_text}\n"
                       f"Баланс: {new_balance} {EMOJIS['bibsy']}",
            color=discord.Color.blue(),
            image="https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExenlsNTgyb2o1cnRjYWJ1ZW1xNDlwdm9qdmtiZGJ5OW83c2oxYTM4dSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/rkJSfl4NQQvd0ZQiiR/giphy.gif",
            footer="Слово Бибера"
        )
        
        if bonus_percent > 0:
            embed.add_field(name="✨ Бонус от артефактов", value=f"+{bonus_percent}% → +{bonus} {EMOJIS['bibsy']}", inline=False)
        
        await loading.stop(True, "Проповедь завершена!")
        await ctx.send(embed=embed)
        
        # Уведомление о новых достижениях
        if new_achievements:
            from supabase_db import ACHIEVEMENTS_DATA
            ach_names = ", ".join([ACHIEVEMENTS_DATA[a]["name"] for a in new_achievements])
            await ctx.send(f"🏆 **НОВОЕ ДОСТИЖЕНИЕ!** {ach_names}")
        
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
        
        # Проверяем защиту от штрафа
        user_data = get_user_data(user_id)
        protected = user_data.get("protect_ecstasy", False)
        double = user_data.get("next_double", False)
        
        if random.random() <= 0.05:
            reward = 3500
            
            if double:
                user_data["next_double"] = False
                reward *= 2
            
            current_response = supabase.table('users').select('balance').eq('user_id', user_id).execute()
            current = current_response.data[0]['balance'] if current_response.data else 0
            new_balance = current + reward
            supabase.table('users').update({'balance': new_balance}).eq('user_id', user_id).execute()
            
            # Обновляем статистику и проверяем достижения
            user_data = get_user_data(user_id)
            stats = user_data.get("stats", {})
            stats["ecstasy_wins"] = stats.get("ecstasy_wins", 0) + 1
            stats["total_earned"] = stats.get("total_earned", 0) + reward
            user_data["stats"] = stats
            update_user_data(user_id, user_data)
            
            # Проверяем достижения
            new_achievements = check_achievements(user_id)
            
            outcomes = [
                "Ты запел «Love Yourself» в акапелле. Голос дрожал, но автотюн спустился с небес.",
                "Ты произнёс: \"Baby, baby, baby, ooooh.\" И сам Бибер в тени сделал лайк.",
                "Ты произнёс: «We were born to be somebody...» Люди не выдержали. Ты стоял в центре лужи из слёз и фантиков."
            ]
            
            await try_drop_card(ctx, "экстаз")
            await check_combos(ctx)
            
            double_text = " (x2 от удвоителя!)" if double else ""
            
            embed = create_embed(
                title=f"{EMOJIS['win']} ЭКСТАЗ!",
                description=f"{random.choice(outcomes)}\n\nПолучено: +{reward} {EMOJIS['bibsy']}{double_text}\nБаланс: {new_balance} {EMOJIS['bibsy']}",
                color=discord.Color.gold(),
                image="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExeWU0M3dtYjI0ZTYxMWtzeXlldWFpYnJncDY3c3M4a3hxdmlnYndhbiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/nCc4eOd8npO1VNc5ca/giphy.gif",
                footer="Божественное откровение"
            )
            
            await loading.stop(True, "Экстаз достигнут!")
            await ctx.send(embed=embed)
            
            if new_achievements:
                from supabase_db import ACHIEVEMENTS_DATA
                ach_names = ", ".join([ACHIEVEMENTS_DATA[a]["name"] for a in new_achievements])
                await ctx.send(f"🏆 **НОВОЕ ДОСТИЖЕНИЕ!** {ach_names}")
            
            log_action(user_id, "ecstasy", f"Success, Reward: {reward}")
        else:
            penalty = 200
            
            if protected:
                user_data["protect_ecstasy"] = False
                update_user_data(user_id, user_data)
                new_balance = get_balance(user_id)
                embed = create_embed(
                    title=f"🛡️ Защита сработала!",
                    description=f"Вы попытались достичь экстаза, но потерпели неудачу.\n"
                               f"Защитный амулет спас вас от штрафа!\n\n"
                               f"Баланс: {new_balance} {EMOJIS['bibsy']}",
                    color=discord.Color.green()
                )
            else:
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
            
            # Проверяем удвоитель
            user_data = get_user_data(user_id)
            double = user_data.get("next_double", False)
            if double:
                user_data["next_double"] = False
                update_user_data(user_id, user_data)
                bonus["reward"] *= 2
            
            current_response = supabase.table('users').select('balance').eq('user_id', user_id).execute()
            current = current_response.data[0]['balance'] if current_response.data else 0
            new_balance = current + bonus["reward"]
            supabase.table('users').update({'balance': new_balance}).eq('user_id', user_id).execute()
            
            # Обновляем статистику и проверяем достижения
            user_data = get_user_data(user_id)
            stats = user_data.get("stats", {})
            stats["repent_success"] = stats.get("repent_success", 0) + 1
            stats["total_earned"] = stats.get("total_earned", 0) + bonus["reward"]
            user_data["stats"] = stats
            update_user_data(user_id, user_data)
            
            # Проверяем достижения
            new_achievements = check_achievements(user_id)
            
            await try_drop_card(ctx, "покаяться")
            await check_combos(ctx)
            
            double_text = " (x2 от удвоителя!)" if double else ""
            
            embed = create_embed(
                title=f"{EMOJIS['win']} Покаяние принято!",
                description=f"{bonus['text']}\n\nПолучено: +{bonus['reward']} {EMOJIS['bibsy']}{double_text}\nБаланс: {new_balance} {EMOJIS['bibsy']}",
                color=discord.Color.green()
            )
            
            await loading.stop(True, "Ты прощен!")
            await ctx.send(embed=embed)
            
            if new_achievements:
                from supabase_db import ACHIEVEMENTS_DATA
                ach_names = ", ".join([ACHIEVEMENTS_DATA[a]["name"] for a in new_achievements])
                await ctx.send(f"🏆 **НОВОЕ ДОСТИЖЕНИЕ!** {ach_names}")
            
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
    
    # Проверяем карточный талисман
    user_data = get_user_data(user_id)
    card_charm_count = get_consumable_count(user_id, "card_charm")
    
    chances = {
        "молиться": 8,
        "проповедь": 8,
        "экстаз": 5,
        "покаяться": 3,
        "дуэль": 4,
        "подарок": 2
    }
    
    chance = chances.get(command, 1)
    if card_charm_count > 0:
        chance += 15
        use_consumable(user_id, "card_charm")
        await ctx.send("🎴 Ваш карточный талисман увеличил шанс выпадения карты! +15%", delete_after=5)
    
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

user_command_history = {}

def check_secret_combo_local(user_id: int, command_sequence: list, SECRET_COMBOS: dict):
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

def complete_combo_local(user_id: int, combo_str: str):
    try:
        response = supabase.table('users').select('completed_combos').eq('user_id', user_id).execute()
        completed = []
        
        if response.data and response.data[0].get('completed_combos'):
            completed = json.loads(response.data[0]['completed_combos'])
        
        if combo_str not in completed:
            completed.append(combo_str)
            supabase.table('users').update({'completed_combos': json.dumps(completed)}).eq('user_id', user_id).execute()
    except Exception as e:
        print(f"[ERROR] complete_combo_local: {e}")

async def check_combos(ctx):
    from bot_data import SECRET_COMBOS
    
    user_id = ctx.author.id
    
    if user_id not in user_command_history:
        user_command_history[user_id] = []
    
    user_command_history[user_id].append(ctx.command.name)
    
    if len(user_command_history[user_id]) > 10:
        user_command_history[user_id] = user_command_history[user_id][-10:]
    
    for length in range(2, min(8, len(user_command_history[user_id]) + 1)):
        sequence = user_command_history[user_id][-length:]
        result = check_secret_combo_local(user_id, sequence, SECRET_COMBOS)
        
        if result:
            combo_str, combo_data = result
            
            add_balance(user_id, combo_data["reward"])
            
            card_reward = ""
            if "card" in combo_data:
                if add_card_to_user(user_id, combo_data["card"]):
                    card_info = COLLECTIBLE_CARDS[combo_data["card"]]
                    card_reward = f"\n🎴 Получена карта: **{card_info['name']}** {card_info['emoji']}"
            
            complete_combo_local(user_id, combo_str)
            
            embed = create_embed(
                title="🥷 СЕКРЕТНАЯ КОМБИНАЦИЯ!",
                description=f"{combo_data['message']}{card_reward}\n\n✨ Редкость: **{combo_data['rarity'].upper()}**",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
            break

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

@bot.command(name='магазин')
@in_command_channel()
async def shop(ctx):
    embed = create_embed("🛒 МАГАЗИН АРТЕФАКТОВ", "", discord.Color.purple())
    
    # Временные артефакты
    temp_items = {k: v for k, v in SHOP_ITEMS.items() if v["type"] == "temporary"}
    if temp_items:
        temp_text = ""
        for item_id, item in temp_items.items():
            temp_text += f"**{item['name']}** - {item['price']} {EMOJIS['bibsy']}\n"
            temp_text += f"└ {item['description']}\n\n"
        embed.add_field(name="⏳ ВРЕМЕННЫЕ (7/15/30 дней)", value=temp_text, inline=False)
    
    # Постоянные артефакты
    perm_items = {k: v for k, v in SHOP_ITEMS.items() if v["type"] == "permanent"}
    if perm_items:
        perm_text = ""
        for item_id, item in perm_items.items():
            perm_text += f"**{item['name']}** - {item['price']} {EMOJIS['bibsy']}\n"
            perm_text += f"└ {item['description']}\n\n"
        embed.add_field(name="💎 ПОСТОЯННЫЕ", value=perm_text, inline=False)
    
    # Расходуемые предметы
    if CONSUMABLE_ITEMS:
        cons_text = ""
        for item_id, item in CONSUMABLE_ITEMS.items():
            cons_text += f"**{item['name']}** - {item['price']} {EMOJIS['bibsy']}\n"
            cons_text += f"└ {item['description']}\n\n"
        embed.add_field(name="⚡ РАСХОДУЕМЫЕ", value=cons_text, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='купить')
@in_command_channel()
@add_command_reaction("купить")
async def buy(ctx, *, item_name: str):
    try:
        user_id = ctx.author.id
        
        # Ищем в SHOP_ITEMS
        item_id = None
        item_data = None
        is_consumable = False
        
        for key, item in SHOP_ITEMS.items():
            if item["name"].lower() == item_name.lower():
                item_id = key
                item_data = item
                break
        
        if not item_id:
            for key, item in CONSUMABLE_ITEMS.items():
                if item["name"].lower() == item_name.lower():
                    item_id = key
                    item_data = item
                    is_consumable = True
                    break
        
        if not item_id:
            embed = create_embed("❌ Ошибка", "Товар не найден! Используйте `!магазин`", discord.Color.red())
            await ctx.send(embed=embed)
            return
        
        user_balance = get_balance(user_id)
        
        if user_balance < item_data["price"]:
            embed = create_embed("❌ Недостаточно средств", f"Нужно: {item_data['price']} {EMOJIS['bibsy']}\nУ вас: {user_balance} {EMOJIS['bibsy']}", discord.Color.red())
            await ctx.send(embed=embed)
            return
        
        if is_consumable:
            max_per_day = item_data.get("max_per_day", 3)
            purchases_today = get_daily_consumable_purchases(user_id, item_id)
            
            if purchases_today >= max_per_day:
                embed = create_embed("❌ Лимит покупок", f"Вы можете купить не более {max_per_day} шт. {item_data['name']} в день!", discord.Color.red())
                await ctx.send(embed=embed)
                return
            
            # Снимаем деньги
            add_balance(user_id, -item_data["price"])
            # Добавляем расходник
            add_consumable(user_id, item_id)
            # Записываем покупку
            add_consumable_purchase(user_id, item_id)
            
            # Проверяем, что добавилось
            check_count = get_consumable_count(user_id, item_id)
            print(f"[BUY] {user_id} купил {item_id}, теперь {check_count} шт.")
            
            embed = create_embed("✅ Покупка успешна!", f"Вы купили **{item_data['name']}**!\n{item_data['description']}\n\n📦 В наличии: {check_count} шт.", discord.Color.green())
            await ctx.send(embed=embed)
            log_action(user_id, "buy_consumable", f"{item_id}, Price: {item_data['price']}")
            
        elif item_data["type"] == "temporary":
            duration_days = item_data.get("duration_days", 7)
            
            # Снимаем деньги
            add_balance(user_id, -item_data["price"])
            # Добавляем временный артефакт
            success = add_temporary_artifact(user_id, item_id, duration_days)
            
            if success:
                embed = create_embed("✅ Покупка успешна!", f"Вы купили **{item_data['name']}**!\n📅 Действует: {duration_days} дней\n✨ {item_data['description']}", discord.Color.green())
                await ctx.send(embed=embed)
                log_action(user_id, "buy_temporary_artifact", f"{item_id}, Price: {item_data['price']}")
            else:
                # Возвращаем деньги
                add_balance(user_id, item_data["price"])
                embed = create_embed("❌ Ошибка", "Не удалось добавить артефакт. Попробуйте позже.", discord.Color.red())
                await ctx.send(embed=embed)
            
        elif item_data["type"] == "permanent":
            # Снимаем деньги
            add_balance(user_id, -item_data["price"])
            # Добавляем постоянный артефакт
            success = add_permanent_artifact(user_id, item_id)
            
            if success:
                embed = create_embed("✅ Покупка успешна!", f"Вы купили **{item_data['name']}**!\n💎 Действует: НАВСЕГДА\n✨ {item_data['description']}", discord.Color.green())
                await ctx.send(embed=embed)
                log_action(user_id, "buy_permanent_artifact", f"{item_id}, Price: {item_data['price']}")
            else:
                # Возвращаем деньги
                add_balance(user_id, item_data["price"])
                embed = create_embed("❌ Ошибка", "Не удалось добавить артефакт. Попробуйте позже.", discord.Color.red())
                await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"[ERROR] buy: {e}")
        import traceback
        traceback.print_exc()
        await ctx.send(embed=create_embed("❌ Ошибка", str(e)[:100], discord.Color.red()))

@bot.command(name='артефакты')
@in_command_channel()
async def artifacts_cmd(ctx):
    """Показать ваши активные артефакты и расходники"""
    user_id = ctx.author.id
    
    # Проверяем просроченные артефакты
    check_expired_artifacts(user_id)
    
    user_data = get_user_data(user_id)
    artifacts = user_data.get("artifacts", {})
    consumables = user_data.get("consumables", {})
    
    embed = create_embed(f"🔮 ИНВЕНТАРЬ {ctx.author.display_name}", "", discord.Color.blue())
    
    # Активные артефакты
    if artifacts:
        art_text = ""
        for art_id, art_data in artifacts.items():
            if art_id in SHOP_ITEMS:
                item = SHOP_ITEMS[art_id]
                if art_data.get("type") == "temporary":
                    expires_at = datetime.fromisoformat(art_data["expires_at"])
                    remaining = expires_at - datetime.now()
                    days_left = remaining.days
                    if days_left > 0:
                        status = f"⏳ Осталось: {days_left} дней"
                    else:
                        hours_left = remaining.seconds // 3600
                        status = f"⏳ Осталось: {hours_left} часов"
                    art_text += f"**{item['name']}**\n└ {item['description']}\n└ {status}\n\n"
                else:
                    art_text += f"**{item['name']}** 💎\n└ {item['description']}\n└ ♾️ Навсегда\n\n"
        if art_text:
            embed.add_field(name="📦 АКТИВНЫЕ АРТЕФАКТЫ", value=art_text, inline=False)
        else:
            embed.add_field(name="📦 АКТИВНЫЕ АРТЕФАКТЫ", value="Нет активных артефактов", inline=False)
    else:
        embed.add_field(name="📦 АКТИВНЫЕ АРТЕФАКТЫ", value="Нет активных артефактов", inline=False)
    
    # Расходуемые предметы
    if consumables:
        cons_text = ""
        for cons_id, count in consumables.items():
            if cons_id in CONSUMABLE_ITEMS:
                item = CONSUMABLE_ITEMS[cons_id]
                cons_text += f"**{item['name']}** x{count}\n└ {item['description']}\n\n"
        embed.add_field(name="⚡ РАСХОДУЕМЫЕ ПРЕДМЕТЫ", value=cons_text, inline=False)
    else:
        embed.add_field(name="⚡ РАСХОДУЕМЫЕ ПРЕДМЕТЫ", value="Нет расходуемых предметов", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='окупаемость')
@in_command_channel()
async def roi(ctx, *, item_name: str):
    """Рассчитать окупаемость артефакта или расходника"""
    try:
        item_id = None
        item_data = None
        is_consumable = False
        
        # Ищем в обычных артефактах
        for key, item in SHOP_ITEMS.items():
            if item["name"].lower() == item_name.lower():
                item_id = key
                item_data = item
                break
        
        # Если не нашли, ищем в расходниках
        if not item_data:
            for key, item in CONSUMABLE_ITEMS.items():
                if item["name"].lower() == item_name.lower():
                    item_id = key
                    item_data = item
                    is_consumable = True
                    break
        
        if not item_data:
            await ctx.send(embed=create_embed("❌ Ошибка", "Товар не найден! Используйте `!магазин`", discord.Color.red()))
            return
        
        # --- БАЗОВЫЕ ПАРАМЕТРЫ ДЛЯ РАСЧЁТА ---
        cmds_per_day = 15
        avg_reward = 65
        
        # --- ВЫЧИСЛЯЕМ БОНУС ---
        bonus_percent = 0
        effect = item_data.get("effect", {})
        
        if effect.get("type") == "instant":
            win_chance = effect.get("win_chance", 0)
            win_amount = effect.get("win_amount", 0)
            expected_value = (win_chance / 100) * win_amount
            
            embed = create_embed(
                "📊 ОЦЕНКА РАСХОДНИКА",
                f"**{item_data['name']}**\n\n"
                f"💰 Цена: {item_data['price']} {EMOJIS['bibsy']}\n"
                f"🎲 Ожидаемый выигрыш: ~{expected_value} {EMOJIS['bibsy']}\n"
                f"{'✅ Выгодно!' if expected_value > item_data['price'] else '⚠️ Это лотерея, не гарантирует прибыль'}",
                discord.Color.gold()
            )
            await ctx.send(embed=embed)
            return
        
        # Для обычных артефактов
        if effect.get("command") == "all":
            bonus_percent = effect.get("bonus", 0)
            daily_extra = int((avg_reward * cmds_per_day) * (bonus_percent / 100))
            cmd_desc = "ко ВСЕМ командам"
        else:
            bonus_percent = effect.get("bonus", 0)
            daily_extra = int((avg_reward * cmds_per_day) * (bonus_percent / 100))
            cmd_desc = f"к команде !{effect.get('command', '?')}"
        
        # --- ОСНОВНОЙ ЭМБЕД ---
        embed = create_embed(
            f"📊 ОКУПАЕМОСТЬ: {item_data['name']}",
            "",
            discord.Color.gold()
        )
        
        embed.add_field(name="💰 Цена", value=f"{item_data['price']} {EMOJIS['bibsy']}", inline=True)
        embed.add_field(name="✨ Бонус", value=f"+{bonus_percent}% {cmd_desc}", inline=True)
        embed.add_field(name="📈 Доп. доход в день", value=f"~{daily_extra} {EMOJIS['bibsy']}", inline=True)
        
        if daily_extra > 0:
            days_to_roi = item_data['price'] / daily_extra
            embed.add_field(name="⏱️ Окупаемость", value=f"~{days_to_roi:.1f} дней", inline=False)
            
            if item_data.get("type") == "temporary":
                duration = item_data.get("duration_days", 7)
                if days_to_roi <= duration:
                    profit = int((duration - days_to_roi) * daily_extra)
                    embed.add_field(
                        name="✅ ВЫГОДНО",
                        value=f"Артефакт окупится за {days_to_roi:.1f} дн.\nЧистая прибыль за {duration} дн.: ~{profit} {EMOJIS['bibsy']}",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="⚠️ НЕ ВЫГОДНО",
                        value=f"Артефакт НЕ окупится за {duration} дней.\nЛучше использовать более дешёвый или копить на постоянный.",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="💎 ПОСТОЯННЫЙ БОНУС",
                    value=f"Окупится за {days_to_roi:.1f} дней, после чего будет приносить чистую прибыль.",
                    inline=False
                )
        else:
            embed.add_field(name="⚠️ Бонус не влияет на доход", value="Этот предмет не увеличивает заработок напрямую.", inline=False)
        
        embed.set_footer(text="Расчёт приблизительный. Реальная окупаемость зависит от вашей активности.")
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"[ERROR] roi: {e}")
        await ctx.send(embed=create_embed("❌ Ошибка", str(e)[:100], discord.Color.red()))

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
    
    can_join, msg = can_join_family(member.id, FAMILY_JOIN_COOLDOWN)
    if not can_join:
        await ctx.send(embed=create_embed("❌ Ошибка", msg, discord.Color.red()))
        return
    
    proposal_id = create_marriage_proposal(ctx.author.id, member.id, proposal_text)
    
    embed = create_embed(
        "💍 ПРЕДЛОЖЕНИЕ РУКИ И СЕРДЦА!",
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
    
    can_join, msg = can_join_family(ctx.author.id, FAMILY_JOIN_COOLDOWN)
    if not can_join:
        await ctx.send(embed=create_embed("❌ Ошибка", msg, discord.Color.red()))
        delete_marriage_proposal(proposal_id)
        return
    
    from_user = bot.get_user(proposal["from_id"]) or await bot.fetch_user(proposal["from_id"])
    family_name = f"{from_user.display_name} & {ctx.author.display_name}"
    family_id = create_family(proposal["from_id"], proposal["to_id"], family_name)
    delete_marriage_proposal(proposal_id)
    
    set_user_join_time(proposal["from_id"])
    set_user_join_time(proposal["to_id"])
    
    embed = create_embed(
        "✅ НОВАЯ СЕМЬЯ СОЗДАНА!",
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
        "❌ ПРЕДЛОЖЕНИЕ ОТКЛОНЕНО",
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
        embed = create_embed("❌ Ошибка", "Вы не состоите в семье!", discord.Color.red())
        await ctx.send(embed=embed)
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
    
    family_age = get_family_age_days(family["family_id"])
    
    embed = create_embed(
        title=f"👪 {family['family_name']}",
        description=f"📅 Возраст семьи: {family_age} дней\n"
                   f"📊 Уровень: {family['level']}/{FAMILY_MAX_LEVEL}\n"
                   f"💰 Бонус: {current_bonus} {EMOJIS['bibsy']}/час",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="💑 Супруги", value=f"{spouse1.mention} и {spouse2.mention}", inline=False)
    
    if children_text:
        embed.add_field(name=f"👶 Дети ({len(family['children'])}/{FAMILY_MAX_CHILDREN})", value="\n".join(children_text), inline=False)
    else:
        embed.add_field(name="👶 Дети", value="Пока нет детей", inline=False)
    
    # Следующий уровень
    if family["level"] < FAMILY_MAX_LEVEL:
        next_level = family["level"] + 1
        req = FAMILY_UPGRADE_REQUIREMENTS.get(next_level, {})
        min_children = req.get("min_children", 0)
        min_age_days = req.get("min_family_age_days", 0)
        cost = FAMILY_UPGRADE_COSTS.get(family["level"], 5000)
        
        embed.add_field(
            name=f"📈 Следующий уровень ({next_level})",
            value=f"👶 Нужно детей: {min_children}\n"
                  f"📅 Возраст семьи: {family_age}/{min_age_days} дней\n"
                  f"💰 Стоимость: {cost} {EMOJIS['bibsy']}",
            inline=False
        )
    
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
    
    if len(family["children"]) >= FAMILY_MAX_CHILDREN:
        embed = create_embed("❌ Ошибка", f"В семье уже {FAMILY_MAX_CHILDREN} детей! Нельзя добавить больше.", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    embed_ask = create_embed(
        "👶 ПРЕДЛОЖЕНИЕ СТАТЬ РЕБЁНКОМ!",
        f"{ctx.author.mention} хочет взять вас в семью!\n\n"
        f"👨‍👩‍👧 Родители: {ctx.author.mention}\n"
        f"👪 Семья: **{family['family_name']}**\n\n"
        f"📝 Вы станете {child_type} по имени **{child_name}**\n\n"
        f"✅ Чтобы согласиться, нажмите ✅\n"
        f"❌ Чтобы отказаться, нажмите ❌",
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
            
            set_user_join_time(member.id)
            
            child_type_display = "сыном" if child_type_en == "son" else "дочерью"
            embed = create_embed(
                "✅ РЕБЕНОК ДОБАВЛЕН!",
                f"{member.mention} стал {child_type_display} семьи **{family['family_name']}**!\n\n"
                f"📝 Имя: {child_name}\n"
                f"👶 Всего детей: {len(family['children'])}/{FAMILY_MAX_CHILDREN}",
                discord.Color.green()
            )
            await ctx.send(embed=embed)
            log_action(ctx.author.id, "add_child", f"Child: {member.id}, Name: {child_name}, Type: {child_type}")
        else:
            embed = create_embed(
                "❌ ОТКАЗАНО",
                f"{member.mention} отказался стать ребёнком.",
                discord.Color.red()
            )
            await ctx.send(embed=embed)
            
    except asyncio.TimeoutError:
        embed = create_embed(
            "⏳ ВРЕМЯ ВЫШЛО",
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
        "❌ РЕБЕНОК ИСКЛЮЧЕН",
        f"{member.mention} ({child_name}) исключен из семьи **{family['family_name']}**!",
        discord.Color.orange()
    )
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "remove_child", f"Child: {member.id}")

@bot.command(name='улучшитьсемью')
@in_command_channel()
@add_command_reaction("улучшитьсемью")
async def upgrade_family_cmd(ctx, confirm: str = None):
    family = get_family_by_member(ctx.author.id)
    
    if not family:
        embed = create_embed("❌ Ошибка", "Вы не состоите в семье!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if ctx.author.id not in [family["spouse1_id"], family["spouse2_id"]]:
        embed = create_embed("❌ Ошибка", "Только супруги могут улучшать семью!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    current_level = family['level']
    next_level = current_level + 1
    
    if next_level > FAMILY_MAX_LEVEL:
        embed = create_embed("❌ Ошибка", f"Семья уже достигла максимального {FAMILY_MAX_LEVEL} уровня!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    # Если это не подтверждение - показываем информацию
    if confirm != "подтвердить":
        req = FAMILY_UPGRADE_REQUIREMENTS.get(next_level, {})
        min_children = req.get("min_children", 0)
        min_age_days = req.get("min_family_age_days", 0)
        cost = FAMILY_UPGRADE_COSTS.get(current_level, 5000)
        
        family_age = get_family_age_days(family['family_id'])
        
        last_upgrade = get_family_upgrade_cooldown(family['family_id'])
        cooldown_text = ""
        if last_upgrade:
            time_since = (datetime.now() - last_upgrade).total_seconds()
            if time_since < FAMILY_UPGRADE_COOLDOWN:
                remaining_hours = int((FAMILY_UPGRADE_COOLDOWN - time_since) // 3600)
                remaining_minutes = int(((FAMILY_UPGRADE_COOLDOWN - time_since) % 3600) // 60)
                cooldown_text = f"\n⏳ Кулдаун улучшения: {remaining_hours}ч {remaining_minutes}м"
        
        embed = create_embed(
            f"🏠 УЛУЧШЕНИЕ СЕМЬИ ({current_level} → {next_level})",
            f"**Семья:** {family['family_name']}\n"
            f"**Текущий бонус:** {FAMILY_HOURLY_BONUSES[current_level]} {EMOJIS['bibsy']}/час\n"
            f"**Следующий бонус:** {FAMILY_HOURLY_BONUSES[next_level]} {EMOJIS['bibsy']}/час\n\n"
            f"**Требования:**\n"
            f"• 👶 Детей: {len(family['children'])}/{min_children}\n"
            f"• 📅 Возраст семьи: {family_age}/{min_age_days} дней\n"
            f"• 💰 Стоимость: {cost} {EMOJIS['bibsy']}\n"
            f"{cooldown_text}\n\n"
            f"Чтобы улучшить, напишите `!улучшитьсемью подтвердить`",
            discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return
    
    # Подтверждение улучшения
    success, message = upgrade_family_with_checks(family["family_id"], FAMILY_UPGRADE_COSTS, FAMILY_UPGRADE_REQUIREMENTS, FAMILY_MAX_LEVEL, FAMILY_UPGRADE_COOLDOWN)
    
    if success:
        family = get_family(family["family_id"])
        embed = create_embed(
            "✅ СЕМЬЯ УЛУЧШЕНА!",
            f"{message}\n\n"
            f"📊 Новый уровень: {family['level']}\n"
            f"💰 Новый бонус: {FAMILY_HOURLY_BONUSES[family['level']]} {EMOJIS['bibsy']}/час",
            discord.Color.green()
        )
        await ctx.send(embed=embed)
        log_action(ctx.author.id, "upgrade_family", f"Level: {family['level']}")
    else:
        embed = create_embed("❌ Ошибка", message, discord.Color.red())
        await ctx.send(embed=embed)

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
        title=f"👶 ДЕТИ СЕМЬИ {family['family_name']}",
        description=f"Всего детей: {len(family['children'])}/{FAMILY_MAX_CHILDREN}",
        color=discord.Color.blue()
    )
    
    for i, child in enumerate(family["children"], 1):
        try:
            child_user = bot.get_user(child["id"]) or await bot.fetch_user(child["id"])
            child_type = "👦 Сын" if child["type"] == "son" else "👧 Дочь"
            embed.add_field(
                name=f"{i}. {child['name']}",
                value=f"{child_type} | {child_user.mention}\n📅 Добавлен: {child['added_at'][:10]}",
                inline=False
            )
        except:
            embed.add_field(
                name=f"{i}. {child['name']}",
                value=f"ID: {child['id']}\n📅 Добавлен: {child['added_at'][:10]}",
                inline=False
            )
    
    await ctx.send(embed=embed)

@bot.command(name='развестись')
@in_command_channel()
@add_command_reaction("развестись")
async def divorce_cmd(ctx, confirm: str = None):
    family = get_family_by_member(ctx.author.id)
    
    if not family or ctx.author.id not in [family["spouse1_id"], family["spouse2_id"]]:
        embed = create_embed("❌ Ошибка", "Вы не состоите в браке!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if confirm != "да":
        can, message = can_divorce(ctx.author.id, FAMILY_DIVORCE_COOLDOWN)
        if not can:
            embed = create_embed("❌ Нельзя развестись", message, discord.Color.red())
            await ctx.send(embed=embed)
            return
        
        embed = create_embed(
            "⚠️ ПОДТВЕРЖДЕНИЕ РАЗВОДА",
            f"Вы действительно хотите развестись?\n\n"
            f"После развода:\n"
            f"• Семья будет распущена\n"
            f"• Дети останутся без семьи\n"
            f"• Вы сможете вступить в новую семью через {FAMILY_JOIN_COOLDOWN // 86400} дней\n\n"
            f"**Напишите `!развестись да` чтобы подтвердить**",
            discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Подтверждение развода
    can, message = can_divorce(ctx.author.id, FAMILY_DIVORCE_COOLDOWN)
    if not can:
        embed = create_embed("❌ Нельзя развестись", message, discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    spouse = bot.get_user(family["spouse1_id"] if ctx.author.id == family["spouse2_id"] else family["spouse1_id"])
    
    supabase.table('families').delete().eq('family_id', family["family_id"]).execute()
    
    set_divorce_time(ctx.author.id)
    set_divorce_time(spouse.id)
    
    embed = create_embed(
        "💔 РАЗВОД",
        f"Брак между {ctx.author.mention} и {spouse.mention} расторгнут!\n\n"
        f"⏳ Вы сможете вступить в новую семью через {FAMILY_JOIN_COOLDOWN // 86400} дней.",
        discord.Color.dark_grey()
    )
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "divorce", f"Spouse: {spouse.id}")

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
    set_user_join_time(ctx.author.id)
    
    embed = create_embed("✅ УСПЕХ", "Вы вышли из семьи!", discord.Color.green())
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
    
    if member == ctx.author:
        embed = create_embed("❌ Ошибка", "Нельзя вызвать самого себя!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if not (50 <= amount <= 150):
        embed = create_embed("❌ Ошибка", "Ставка должна быть от 50 до 150 бибсов!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if DuelManager.get_daily_duel_count(ctx.author.id) >= 3:
        embed = create_embed("❌ Лимит", "Вы уже провели 3 дуэли сегодня!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if get_balance(ctx.author.id) < amount:
        embed = create_embed("❌ Недостаточно средств", f"У вас нет {amount} {EMOJIS['bibsy']} для ставки!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    if DuelManager.get_duel(ctx.channel.id):
        embed = create_embed("❌ Ошибка", "В этом канале уже идёт дуэль!", discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    for channel in bot.get_all_channels():
        duel_data = DuelManager.get_duel(channel.id)
        if duel_data and (duel_data["challenger_id"] == member.id or duel_data["target_id"] == member.id):
            embed = create_embed("❌ Ошибка", f"{member.mention} уже участвует в другой дуэли!", discord.Color.red())
            await ctx.send(embed=embed)
            return
    
    DuelManager.create_duel(ctx.channel.id, ctx.author.id, member.id, amount)
    
    embed = create_embed(
        "⚔️ ВЫЗОВ НА ДУЭЛЬ!",
        f"{ctx.author.mention} вызывает {member.mention} на дуэль!\n\n"
        f"💰 Ставка: {amount} {EMOJIS['bibsy']}\n\n"
        f"📝 {member.mention}, напишите `!принятьдуэль` чтобы принять вызов!\n"
        f"❌ Чтобы отменить, напишите `!отменитьдуэль`",
        discord.Color.gold()
    )
    await ctx.send(embed=embed)
    log_action(ctx.author.id, "duel_start", f"Target: {member.id}, Amount: {amount}")

@bot.command(name='принятьдуэль')
@in_command_channel()
@add_command_reaction("принятьдуэль")
async def accept_duel(ctx):
    try:
        duel_data = DuelManager.get_duel(ctx.channel.id)
        
        if not duel_data:
            embed = create_embed("❌ Ошибка", "Нет активной дуэли в этом канале!", discord.Color.red())
            await ctx.send(embed=embed)
            return
        
        if ctx.author.id != duel_data["target_id"]:
            embed = create_embed("❌ Ошибка", "Эта дуэль не для вас!", discord.Color.red())
            await ctx.send(embed=embed)
            return
        
        if get_balance(ctx.author.id) < duel_data["amount"]:
            embed = create_embed("❌ Недостаточно средств", f"У вас нет {duel_data['amount']} {EMOJIS['bibsy']} для участия в дуэли!", discord.Color.red())
            DuelManager.delete_duel(ctx.channel.id)
            await ctx.send(embed=embed)
            return
        
        DuelManager.accept_duel(ctx.channel.id, ctx.author.id)
        
        embed = create_embed(
            "⚔️ ДУЭЛЬ ПРИНЯТА!",
            f"{ctx.author.mention} принял вызов!\n\n"
            f"⚔️ Оба участника, напишите `!бой` чтобы начать сражение!",
            discord.Color.green()
        )
        await ctx.send(embed=embed)
        log_action(ctx.author.id, "accept_duel", f"Channel: {ctx.channel.id}")
        
    except Exception as e:
        print(f"[ERROR] accept_duel: {e}")
        embed = create_embed("❌ Ошибка", f"Произошла ошибка: {str(e)[:100]}", discord.Color.red())
        await ctx.send(embed=embed)

@bot.command(name='отменитьдуэль')
@in_command_channel()
@add_command_reaction("отменитьдуэль")
async def cancel_duel(ctx):
    try:
        duel_data = DuelManager.get_duel(ctx.channel.id)
        
        if not duel_data:
            embed = create_embed("❌ Ошибка", "Нет активной дуэли в этом канале!", discord.Color.red())
            await ctx.send(embed=embed)
            return
        
        if ctx.author.id not in [duel_data["challenger_id"], duel_data["target_id"]]:
            embed = create_embed("❌ Ошибка", "Вы не участник этой дуэли!", discord.Color.red())
            await ctx.send(embed=embed)
            return
        
        challenger = bot.get_user(duel_data["challenger_id"]) or await bot.fetch_user(duel_data["challenger_id"])
        target = bot.get_user(duel_data["target_id"]) or await bot.fetch_user(duel_data["target_id"])
        
        DuelManager.delete_duel(ctx.channel.id)
        
        embed = create_embed(
            "❌ ДУЭЛЬ ОТМЕНЕНА",
            f"Дуэль между {challenger.mention} и {target.mention} отменена по просьбе {ctx.author.mention}!",
            discord.Color.orange()
        )
        await ctx.send(embed=embed)
        log_action(ctx.author.id, "cancel_duel", f"Channel: {ctx.channel.id}")
        
    except Exception as e:
        print(f"[ERROR] cancel_duel: {e}")
        embed = create_embed("❌ Ошибка", f"Произошла ошибка: {str(e)[:100]}", discord.Color.red())
        await ctx.send(embed=embed)

@bot.command(name='бой')
@in_command_channel()
@add_command_reaction("бой")
async def fight(ctx):
    try:
        duel_data = DuelManager.get_duel(ctx.channel.id)
        
        if not duel_data:
            embed = create_embed("❌ Ошибка", "Нет активной дуэли в этом канале!", discord.Color.red())
            await ctx.send(embed=embed)
            return
        
        if not duel_data["accepted"]:
            embed = create_embed("❌ Ошибка", "Дуэль ещё не принята! Ожидайте согласия соперника.", discord.Color.red())
            await ctx.send(embed=embed)
            return
        
        if ctx.author.id not in [duel_data["challenger_id"], duel_data["target_id"]]:
            embed = create_embed("❌ Ошибка", "Вы не участник этой дуэли!", discord.Color.red())
            await ctx.send(embed=embed)
            return
        
        ready_count = DuelManager.add_fighter_ready(ctx.channel.id, ctx.author.id)
        
        if ready_count < 2:
            embed = create_embed("⚔️ ГОТОВ К БОЮ!", f"{ctx.author.mention} готов! Ожидаем второго участника...", discord.Color.gold())
            await ctx.send(embed=embed)
            return
        
        challenger = bot.get_user(duel_data["challenger_id"]) or await bot.fetch_user(duel_data["challenger_id"])
        target = bot.get_user(duel_data["target_id"]) or await bot.fetch_user(duel_data["target_id"])
        amount = duel_data["amount"]
        
        # Проверяем защиту от проигрыша
        challenger_protect = get_consumable_count(challenger.id, "duel_shield") > 0
        target_protect = get_consumable_count(target.id, "duel_shield") > 0
        
        embed = create_embed(
            "⚔️ БОЙ НАЧАЛСЯ! ⚔️",
            f"{challenger.mention} vs {target.mention}\n\n"
            f"💰 Ставка: {amount} {EMOJIS['bibsy']}\n\n"
            f"**Бой идёт...**",
            discord.Color.gold()
        )
        msg = await ctx.send(embed=embed)
        
        await asyncio.sleep(2)
        
        # Снимаем ставки
        add_balance(challenger.id, -amount)
        add_balance(target.id, -amount)
        
        # Определяем победителя
        winner = random.choice([challenger, target])
        loser = target if winner == challenger else challenger
        reward = amount * 2
        
        # Проверяем защиту проигравшего
        if (loser.id == challenger.id and challenger_protect) or (loser.id == target.id and target_protect):
            use_consumable(loser.id, "duel_shield")
            add_balance(loser.id, amount)
            reward = amount
            embed = create_embed(
                "⚔️ ДУЭЛЬ ЗАВЕРШЕНА! ⚔️",
                f"{challenger.mention} vs {target.mention}\n\n"
                f"🏆 **ПОБЕДИТЕЛЬ: {winner.mention}** 🏆\n\n"
                f"💰 Выигрыш: {reward} {EMOJIS['bibsy']}\n\n"
                f"🛡️ {loser.mention} использовал Оберег дуэлянта и не потерял ставку!",
                discord.Color.green()
            )
        else:
            add_balance(winner.id, reward)
            embed = create_embed(
                "⚔️ ДУЭЛЬ ЗАВЕРШЕНА! ⚔️",
                f"{challenger.mention} vs {target.mention}\n\n"
                f"🏆 **ПОБЕДИТЕЛЬ: {winner.mention}** 🏆\n\n"
                f"💰 Выигрыш: {reward} {EMOJIS['bibsy']}\n\n"
                f"💔 Проигравший: {loser.mention}",
                discord.Color.green()
            )
        
        await try_drop_card(ctx, "дуэль")
        
        DuelManager.increment_duel_count(winner.id, True)
        DuelManager.increment_duel_count(loser.id, False)
        DuelManager.delete_duel(ctx.channel.id)
        
        await msg.edit(embed=embed)
        log_action(winner.id, "duel_win", f"Amount: {reward}, Loser: {loser.id}")
        
    except Exception as e:
        print(f"[ERROR] fight: {e}")
        embed = create_embed("❌ Ошибка", f"Произошла ошибка: {str(e)[:100]}", discord.Color.red())
        await ctx.send(embed=embed)

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
            "🎉 ФЕЙК! 🎉", 
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
            "⭐ ПОЙМАЛ! ⭐", 
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
                "🎁 ВАМ ПОДАРОК!",
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
    
    embed = create_embed(f"🎁 ВАШИ ПОДАРКИ ({len(gifts)})", "", discord.Color.gold())
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
    
    embed = create_embed("🏆 ТОП ПОЛУЧАТЕЛЕЙ ПОДАРКОВ", "", discord.Color.gold())
    for i, stat in enumerate(stats[:10], 1):
        try:
            user = bot.get_user(stat['user_id']) or await bot.fetch_user(stat['user_id'])
            name = user.display_name
        except:
            name = f"ID:{stat['user_id']}"
        embed.add_field(name=f"{i}. {name}", value=f"{stat['count']} подарков", inline=False)
    
    await ctx.send(embed=embed)

# ==================== ИНФОРМАЦИОННЫЕ КОМАНДЫ ====================

@bot.command(name='топ')
@in_command_channel()
async def top(ctx):
    response = supabase.table('users').select('user_id, balance').order('balance', desc=True).limit(10).execute()
    users = response.data
    
    embed = create_embed("🏆 ТОП ФАНАТОВ", "", discord.Color.gold())
    
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
    
    embed = create_embed("🎣 ТОП ЛОВЦОВ БИБЕРА", "", discord.Color.gold())
    
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
    
    embed = create_embed(f"📊 СТАТИСТИКА {target.display_name}", "", discord.Color.blue())
    embed.add_field(name="💰 Баланс", value=f"{bal} {EMOJIS['bibsy']}", inline=True)
    embed.add_field(name="👶 Ловля Бибера", value=f"{catch['catches']} (фейков: {catch['fake_catches']})", inline=True)
    embed.add_field(name="⚔️ Дуэли сегодня", value=f"{duels}/3", inline=True)
    embed.add_field(name="🎴 Карт в коллекции", value=f"{collection['total']}/{collection['total_possible']}", inline=True)
    embed.add_field(name="🔓 Найдено комбинаций", value=f"{combos}/{len(SECRET_COMBOS)}", inline=True)
    if family:
        embed.add_field(name="👪 Семья", value=f"{family['family_name']} (ур. {family['level']})", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='ачивки')
@in_command_channel()
async def show_achievements(ctx, member: discord.Member = None):
    """Показать полученные достижения пользователя"""
    target = member or ctx.author
    
    # Проверяем и обновляем достижения
    new_achs = check_achievements(target.id)
    
    user_data = get_user_data(target.id)
    achievements = user_data.get("achievements", [])
    
    # Считаем прогресс
    total_achs = len(ACHIEVEMENTS_DATA)
    earned_achs = len(achievements)
    percent = int(earned_achs / total_achs * 100) if total_achs > 0 else 0
    
    embed = create_embed(
        f"🏆 ДОСТИЖЕНИЯ {target.display_name}",
        f"**Прогресс:** {earned_achs}/{total_achs} ({percent}%)",
        discord.Color.gold()
    )
    
    # Прогресс-бар
    progress_bars = 10
    filled = int(progress_bars * earned_achs / total_achs) if total_achs > 0 else 0
    empty = progress_bars - filled
    progress_bar = "█" * filled + "░" * empty
    embed.add_field(name="📊 Общий прогресс", value=f"`{progress_bar}`", inline=False)
    
    # Группируем по категориям с прогрессом
    categories = {
        "🙏 МОЛИТВЫ": ["pray_10", "pray_100", "pray_1000"],
        "📖 ПРОПОВЕДИ": ["sermon_10", "sermon_100", "sermon_1000"],
        "🎴 КАРТЫ": ["cards_5", "cards_15", "cards_all"],
        "💰 БАЛАНС": ["balance_1000", "balance_10000", "balance_100000"],
        "🎣 ЛОВЛЯ БИБЕРА": ["catch_5", "catch_25", "catch_100"],
        "⚔️ ДУЭЛИ": ["duel_5", "duel_25", "duel_100"],
        "👪 СЕМЬЯ": ["family_create", "family_level_3", "family_level_6"],
        "🤫 КОМБИНАЦИИ": ["combo_1", "combo_5", "combo_all"]
    }
    
    for cat_name, cat_achievements in categories.items():
        cat_text = ""
        cat_earned = 0
        for ach_id in cat_achievements:
            if ach_id in ACHIEVEMENTS_DATA:
                ach = ACHIEVEMENTS_DATA[ach_id]
                status = "✅" if ach_id in achievements else "❌"
                if ach_id in achievements:
                    cat_earned += 1
                cat_text += f"{status} **{ach['name']}**\n"
        cat_total = len(cat_achievements)
        if cat_text:
            embed.add_field(
                name=f"{cat_name} [{cat_earned}/{cat_total}]",
                value=cat_text,
                inline=True
            )
    
    # Если есть новые достижения
    if new_achs:
        ach_names = ", ".join([ACHIEVEMENTS_DATA[a]["name"] for a in new_achs])
        embed.set_footer(text=f"🎉 Новые достижения: {ach_names}")
    
    await ctx.send(embed=embed)

@bot.command(name='достижения')
@in_command_channel()
async def list_all_achievements(ctx, category: str = None):
    """Показать все достижения с условиями получения
    Использование: !достижения [категория]
    Категории: молитвы, проповеди, карты, баланс, ловля, дуэли, семья, комбинации"""
    
    categories = {
        "молитвы": {
            "emoji": "🙏",
            "name": "МОЛИТВЫ",
            "achs": ["pray_10", "pray_100", "pray_1000"],
            "requirements": {
                "pray_10": "Совершить 10 молитв",
                "pray_100": "Совершить 100 молитв",
                "pray_1000": "Совершить 1000 молитв"
            }
        },
        "проповеди": {
            "emoji": "📖",
            "name": "ПРОПОВЕДИ",
            "achs": ["sermon_10", "sermon_100", "sermon_1000"],
            "requirements": {
                "sermon_10": "Провести 10 проповедей",
                "sermon_100": "Провести 100 проповедей",
                "sermon_1000": "Провести 1000 проповедей"
            }
        },
        "карты": {
            "emoji": "🎴",
            "name": "КАРТЫ",
            "achs": ["cards_5", "cards_15", "cards_all"],
            "requirements": {
                "cards_5": "Собрать 5 разных карт",
                "cards_15": "Собрать 15 разных карт",
                "cards_all": "Собрать ВСЕ карты (9 шт)"
            }
        },
        "баланс": {
            "emoji": "💰",
            "name": "БАЛАНС",
            "achs": ["balance_1000", "balance_10000", "balance_100000"],
            "requirements": {
                "balance_1000": "Накопить 1000 бибсов",
                "balance_10000": "Накопить 10000 бибсов",
                "balance_100000": "Накопить 100000 бибсов"
            }
        },
        "ловля": {
            "emoji": "🎣",
            "name": "ЛОВЛЯ БИБЕРА",
            "achs": ["catch_5", "catch_25", "catch_100"],
            "requirements": {
                "catch_5": "Поймать Бибера 5 раз",
                "catch_25": "Поймать Бибера 25 раз",
                "catch_100": "Поймать Бибера 100 раз"
            }
        },
        "дуэли": {
            "emoji": "⚔️",
            "name": "ДУЭЛИ",
            "achs": ["duel_5", "duel_25", "duel_100"],
            "requirements": {
                "duel_5": "Выиграть 5 дуэлей",
                "duel_25": "Выиграть 25 дуэлей",
                "duel_100": "Выиграть 100 дуэлей"
            }
        },
        "семья": {
            "emoji": "👪",
            "name": "СЕМЬЯ",
            "achs": ["family_create", "family_level_3", "family_level_6"],
            "requirements": {
                "family_create": "Создать семью",
                "family_level_3": "Улучшить семью до 3 уровня",
                "family_level_6": "Улучшить семью до 6 уровня"
            }
        },
        "комбинации": {
            "emoji": "🤫",
            "name": "КОМБИНАЦИИ",
            "achs": ["combo_1", "combo_5", "combo_all"],
            "requirements": {
                "combo_1": "Найти 1 секретную комбинацию",
                "combo_5": "Найти 5 секретных комбинаций",
                "combo_all": "Найти ВСЕ секретные комбинации (8 шт)"
            }
        }
    }
    
    # Если указана категория - показываем только её
    if category and category.lower() in categories:
        cat = categories[category.lower()]
        embed = create_embed(
            f"{cat['emoji']} ДОСТИЖЕНИЯ - {cat['name']}",
            "Награды за достижения в этой категории:",
            discord.Color.gold()
        )
        
        for ach_id in cat["achs"]:
            if ach_id in ACHIEVEMENTS_DATA:
                ach = ACHIEVEMENTS_DATA[ach_id]
                reward_text = f"🎁 {ach['reward']} бибсов"
                if "permanent_bonus" in ach:
                    bonus = ach["permanent_bonus"]
                    reward_text += f"\n└ ✨ Постоянный бонус: +{bonus['bonus']}% к {bonus['command']}"
                
                embed.add_field(
                    name=f"🏆 {ach['name']}",
                    value=f"📋 Условие: {cat['requirements'][ach_id]}\n🎁 Награда: {reward_text}",
                    inline=False
                )
        
        embed.set_footer(text="Используйте !ачивки чтобы увидеть свой прогресс")
        await ctx.send(embed=embed)
        return
    
    # Если категория не указана - показываем все категории
    embed = create_embed(
        "🏆 ВСЕ ДОСТИЖЕНИЯ BIBERBOT",
        "Выберите категорию для просмотра подробностей:\n"
        "`!достижения молитвы`\n`!достижения проповеди`\n`!достижения карты`\n"
        "`!достижения баланс`\n`!достижения ловля`\n`!достижения дуэли`\n"
        "`!достижения семья`\n`!достижения комбинации`",
        discord.Color.blue()
    )
    
    for cat_key, cat_data in categories.items():
        embed.add_field(
            name=f"{cat_data['emoji']} {cat_data['name']}",
            value=f"Достижений: {len(cat_data['achs'])}\n`!достижения {cat_key}`",
            inline=True
        )
    
    embed.set_footer(text="Всего достижений: 27")
    await ctx.send(embed=embed)

@bot.command(name='помощь')
@in_command_channel()
async def help_command(ctx):
    embed = create_embed(
        "📚 ПОМОЩЬ BIBERBOT",
        "Вот список всех доступных команд:",
        discord.Color.blue()
    )
    
    # 💰 ЗАРАБОТОК
    embed.add_field(
        name="💰 ЗАРАБОТОК",
        value="`!молиться` - заработать бибсы\n"
              "`!проповедь` - заработать бибсы\n"
              "`!экстаз` - рискнуть (5% успеха)\n"
              "`!покаяться` - шанс получить бибсы",
        inline=False
    )
    
    # 🎴 КОЛЛЕКЦИОНИРОВАНИЕ
    embed.add_field(
        name="🎴 КОЛЛЕКЦИОНИРОВАНИЕ",
        value="`!коллекция` - показать коллекцию карт\n"
              "`!картакд` - показать кулдаун карт\n"
              "`!шансыкарт` - шансы выпадения карт",
        inline=False
    )
    
    # 🎉 РАЗВЛЕЧЕНИЯ
    embed.add_field(
        name="🎉 РАЗВЛЕЧЕНИЯ",
        value="`!поцелуй @участник` - поцеловать\n"
              "`!обнять @участник` - обнять\n"
              "`!ударить @участник` - ударить\n"
              "`!угостить @участник` - угостить\n"
              "`!любовь @участник` - заняться любовью\n"
              "`!комплимент [@участник]` - получить комплимент",
        inline=False
    )
    
    # 👪 СЕМЬЯ
    embed.add_field(
        name="👪 СЕМЬЯ",
        value="`!предложить @участник текст` - сделать предложение\n"
              "`!принять ID` - принять предложение\n"
              "`!отказаться ID` - отказаться\n"
              "`!моясемья` - информация о семье\n"
              "`!добавитьребенка @участник имя тип` - добавить ребёнка (сын/дочь)\n"
              "`!исключитьребенка @участник` - исключить ребёнка\n"
              "`!улучшитьсемью` - улучшить семью\n"
              "`!дети` - список детей\n"
              "`!развестись` - развод (только с подтверждением)\n"
              "`!выйти` - выйти из семьи (для детей)",
        inline=False
    )
    
    # ⚔️ ДУЭЛИ
    embed.add_field(
        name="⚔️ ДУЭЛИ",
        value="`!дуэль @участник 50-150` - вызвать на дуэль\n"
              "`!принятьдуэль` - принять дуэль\n"
              "`!бой` - начать бой\n"
              "`!отменитьдуэль` - отменить дуэль",
        inline=False
    )
    
    # 🎁 ПОДАРКИ
    embed.add_field(
        name="🎁 ПОДАРКИ",
        value="`!подарок @участник` - отправить подарок\n"
              "`!моиподарки` - посмотреть подарки\n"
              "`!топподарков` - топ получателей подарков",
        inline=False
    )
    
    # 🛒 МАГАЗИН И АРТЕФАКТЫ
    embed.add_field(
        name="🛒 МАГАЗИН И АРТЕФАКТЫ",
        value="`!магазин` - список товаров\n"
              "`!купить название` - купить артефакт/расходник\n"
              "`!артефакты` - ваши активные артефакты\n"
              "`!окупаемость название` - рассчитать окупаемость артефакта",
        inline=False
    )
    
    # 🏆 ДОСТИЖЕНИЯ
    embed.add_field(
        name="🏆 ДОСТИЖЕНИЯ",
        value="`!ачивки [@участник]` - мои полученные достижения\n"
              "`!достижения [категория]` - список всех достижений с условиями",
        inline=False
    )

    # 🎮 ИГРЫ И ПРОЧЕЕ
    embed.add_field(
        name="🎮 ИГРЫ И ПРОЧЕЕ",
        value="`!поймать` - поймать Бибера (появляется случайно)\n"
              "`!передать @участник сумма` - передать бибсы\n"
              "`!признание текст` - анонимное признание",
        inline=False
    )
    
    # ℹ️ ИНФОРМАЦИЯ
    embed.add_field(
        name="ℹ️ ИНФОРМАЦИЯ",
        value="`!баланс [@участник]` - проверить баланс\n"
              "`!топ` - топ по балансу\n"
              "`!фанаты` - топ ловцов Бибера\n"
              "`!статистика [@участник]` - полная статистика\n"
              "`!помощь` - это сообщение",
        inline=False
    )
    
    # 👑 АДМИН-КОМАНДЫ
    if ctx.author.guild_permissions.administrator or discord.utils.get(ctx.author.roles, name=ADMIN_ROLE):
        embed.add_field(
            name="👑 АДМИН-КОМАНДЫ",
            value="`!выдать @участник сумма` - выдать бибсы\n"
                  "`!забрать @участник сумма` - забрать бибсы\n"
                  "`!сброситькулдаун [@участник]` - сбросить кулдаун\n"
                  "`!датькарту @участник название` - выдать карту\n"
                  "`!сброситьбд ДА` - ПОЛНОСТЬЮ СБРОСИТЬ БД\n"
                  "`!админотмена [#канал]` - принудительно отменить дуэль\n"
                  "`!дуэлисписок` - список активных дуэлей",
            inline=False
        )
    
    embed.set_footer(text="Бибер всегда с тобой! 🙏")
    await ctx.send(embed=embed)

# ==================== ПРИЗНАНИЯ ====================

@bot.command(name='признание')
@add_command_reaction("признание")
async def confession(ctx, *, confession_text: str):
    add_confession(confession_text)
    
    channel = discord.utils.get(ctx.guild.channels, name=COMMAND_CHANNEL) or ctx.channel
    embed = create_embed("💌 АНОНИМНОЕ ПРИЗНАНИЕ", confession_text, discord.Color.pink(), timestamp=True)
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

@bot.command(name='сброситьбд')
@commands.has_role(ADMIN_ROLE)
@in_command_channel()
async def reset_database(ctx, confirm: str = None):
    if confirm != "ДА":
        embed = create_embed(
            "⚠️ ПОДТВЕРЖДЕНИЕ",
            f"Эта команда **ПОЛНОСТЬЮ УДАЛИТ ВСЕ ДАННЫЕ**:\n"
            f"• Балансы всех пользователей\n"
            f"• Все карточки\n"
            f"• Все семьи\n"
            f"• Всю статистику\n"
            f"• Все подарки и признания\n\n"
            f"**Чтобы подтвердить, напишите:** `!сброситьбд ДА`\n\n"
            f"*Это действие НЕЛЬЗЯ отменить!*",
            discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    embed = create_embed("⏳ Сброс базы данных", "Начинаю удаление всех данных...", discord.Color.orange())
    await ctx.send(embed=embed)
    
    try:
        supabase.table('users').delete().neq('user_id', 0).execute()
        supabase.table('families').delete().neq('family_id', 0).execute()
        supabase.table('marriage_proposals').delete().neq('proposal_id', 0).execute()
        supabase.table('active_duels').delete().neq('channel_id', 0).execute()
        supabase.table('bieber_catch').delete().neq('user_id', 0).execute()
        supabase.table('duels').delete().neq('user_id', 0).execute()
        supabase.table('logs').delete().neq('log_id', 0).execute()
        supabase.table('gifts').delete().neq('gift_id', 0).execute()
        supabase.table('confessions').delete().neq('confession_id', 0).execute()
        
        global user_last_card_drop, user_command_history
        user_last_card_drop = {}
        user_command_history = {}
        
        embed = create_embed(
            "✅ БАЗА ДАННЫХ ПОЛНОСТЬЮ СБРОШЕНА",
            f"Все таблицы очищены!\n"
            f"• Балансы удалены\n"
            f"• Карточки удалены\n"
            f"• Семьи удалены\n"
            f"• Вся статистика удалена\n\n"
            f"Бот готов к работе с чистого листа!",
            discord.Color.green()
        )
        await ctx.send(embed=embed)
        log_action(ctx.author.id, "reset_database", "Full database reset")
        
    except Exception as e:
        embed = create_embed("❌ Ошибка при сбросе", f"Произошла ошибка: {str(e)}", discord.Color.red())
        await ctx.send(embed=embed)
        print(f"[ERROR] reset_database: {e}")

@bot.command(name='админотмена')
@commands.has_role(ADMIN_ROLE)
@in_command_channel()
async def admin_cancel_duel(ctx, channel_id: int = None):
    try:
        if channel_id:
            duel_data = DuelManager.get_duel(channel_id)
            target_channel = bot.get_channel(channel_id)
        else:
            duel_data = DuelManager.get_duel(ctx.channel.id)
            target_channel = ctx.channel
        
        if not duel_data:
            embed = create_embed("❌ Ошибка", "Нет активной дуэли в этом канале!", discord.Color.red())
            await ctx.send(embed=embed)
            return
        
        challenger = bot.get_user(duel_data["challenger_id"]) or await bot.fetch_user(duel_data["challenger_id"])
        target = bot.get_user(duel_data["target_id"]) or await bot.fetch_user(duel_data["target_id"])
        
        DuelManager.delete_duel(duel_data["channel_id"])
        
        embed = create_embed(
            "👑 ДУЭЛЬ ПРИНУДИТЕЛЬНО ОТМЕНЕНА",
            f"Дуэль между {challenger.mention} и {target.mention} отменена администратором {ctx.author.mention}!",
            discord.Color.red()
        )
        await ctx.send(embed=embed)
        
        if target_channel and target_channel.id != ctx.channel.id:
            await target_channel.send(embed=embed)
        
        log_action(ctx.author.id, "admin_cancel_duel", f"Channel: {duel_data['channel_id']}")
        
    except Exception as e:
        print(f"[ERROR] admin_cancel_duel: {e}")
        embed = create_embed("❌ Ошибка", f"Произошла ошибка: {str(e)[:100]}", discord.Color.red())
        await ctx.send(embed=embed)

@bot.command(name='дуэлисписок')
@commands.has_role(ADMIN_ROLE)
@in_command_channel()
async def list_duels(ctx):
    try:
        response = supabase.table('active_duels').select('*').execute()
        duels = response.data
        
        if not duels:
            embed = create_embed("⚔️ Активные дуэли", "Нет активных дуэлей.", discord.Color.blue())
            await ctx.send(embed=embed)
            return
        
        embed = create_embed("⚔️ АКТИВНЫЕ ДУЭЛИ", f"Всего: {len(duels)}", discord.Color.gold())
        
        for duel in duels:
            challenger = bot.get_user(duel["challenger_id"]) or await bot.fetch_user(duel["challenger_id"])
            target = bot.get_user(duel["target_id"]) or await bot.fetch_user(duel["target_id"])
            channel = bot.get_channel(duel["channel_id"])
            
            status = "✅ Принята" if duel["accepted"] else "⏳ Ожидает принятия"
            
            embed.add_field(
                name=f"📌 Канал: {channel.mention if channel else duel['channel_id']}",
                value=f"⚔️ {challenger.display_name} vs {target.display_name}\n"
                      f"💰 Ставка: {duel['amount']} {EMOJIS['bibsy']}\n"
                      f"📊 Статус: {status}",
                inline=False
            )
        
        embed.set_footer(text="Используйте !админотмена #канал для отмены дуэли")
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"[ERROR] list_duels: {e}")
        embed = create_embed("❌ Ошибка", str(e)[:100], discord.Color.red())
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
    if not bieber_escape_task.is_running():
        bieber_escape_task.start()
    
    DuelManager.cleanup_old_duels()

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user.name} готов к работе!')
    print(f'📊 Команд загружено: {len(bot.commands)}')
    print(f'🎴 Коллекционных карт: {len(COLLECTIBLE_CARDS)}')
    print(f'🔓 Секретных комбинаций: {len(SECRET_COMBOS)}')
    print(f'👨‍👩‍👧‍👦 Семейная система: до {FAMILY_MAX_CHILDREN} детей, макс уровень {FAMILY_MAX_LEVEL}')
    print(f'🛒 Магазин: {len(SHOP_ITEMS)} артефактов, {len(CONSUMABLE_ITEMS)} расходников')
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