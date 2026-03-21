"""
bot.py — Módulo do bot Discord
Comandos, IA (Groq), anti-flood, cache de histórico.
"""

import asyncio
import base64
import io
import time
from collections import defaultdict
from typing import Dict, List, Optional

import discord
from discord.ext import commands
import requests

import database as db
from config import (
    DISCORD_TOKEN, GUILD_ID, HIERARQUIA, SAUDACOES,
    FLOOD_LIMIT, FLOOD_WINDOW, GROQ_API_KEY, GROQ_MODEL,
    GROQ_MAX_TOKENS, GROQ_HISTORY_LEN, DEBUG,
    CANAL_POR_TIPO, ADMIN_IDS, STAFF_ROLE_ID
)

# ══════════════════════════════════════════════
# SETUP
# ══════════════════════════════════════════════
intents                 = discord.Intents.default()
intents.message_content = True
intents.members         = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Histórico de IA por canal
chat_history: Dict[str, List[Dict]] = {}

# Flood control
flood_control: defaultdict = defaultdict(list)

# Comandos nativos (IA não responde)
KNOWN_CMDS = frozenset({"ping", "patente", "limpar", "help", "aprovar", "reprovar", "perms"})

# System prompt da IA
SYSTEM_PROMPT = (
    "Você é o assistente oficial do Exército Brasileiro (EB) no Roblox. "
    "Responda em português, de forma CURTA e direta (máximo 3 linhas). "
    "Nunca mencione sites externos. Seja formal e respeitoso com os postos. "
    "Foque apenas em: patentes, regras, treinamentos e eventos do EB no Roblox."
)


# ══════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════
def get_main_role(member: discord.Member) -> Optional[str]:
    role_names = {r.name for r in member.roles}
    for rank in HIERARQUIA:
        if rank in role_names:
            return rank
    return None


def check_flood(user_id: int) -> bool:
    now = time.time()
    flood_control[user_id] = [t for t in flood_control[user_id] if now - t < FLOOD_WINDOW]
    if len(flood_control[user_id]) >= FLOOD_LIMIT:
        return True
    flood_control[user_id].append(now)
    return False


def _ask_groq_sync(messages: List[Dict]) -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       GROQ_MODEL,
        "messages":    messages,
        "max_tokens":  GROQ_MAX_TOKENS,
        "temperature": 0.7,
    }
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )
    data = resp.json()
    if "choices" not in data:
        raise ValueError(f"Groq error: {data}")
    return data["choices"][0]["message"]["content"]


async def ask_groq(messages: List[Dict]) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _ask_groq_sync, messages)


# ══════════════════════════════════════════════
# EVENTOS
# ══════════════════════════════════════════════
@bot.event
async def on_ready() -> None:
    print(f"🤖 Bot: {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="pelo Exército Brasileiro 🪖",
        )
    )
    await db.add_log("system", f"Bot iniciado: {bot.user}")


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    if not message.content.startswith("!"):
        return

    pergunta = message.content[1:].strip()
    if not pergunta:
        return

    if pergunta.split()[0].lower() in KNOWN_CMDS:
        return

    # Anti-flood
    if check_flood(message.author.id):
        await message.reply("⛔ Devagar, soldado! Aguarde antes de perguntar novamente.")
        await db.add_log("block", f"Flood bloqueado: {message.author.display_name}",
                         str(message.author.id), message.author.display_name)
        return

    if not GROQ_API_KEY:
        await message.reply("⚠️ IA não configurada. Defina GROQ_API_KEY.")
        return

    # Patente
    cargo_nome = get_main_role(message.author)
    if cargo_nome and cargo_nome in SAUDACOES:
        patente, saudacao, _ = SAUDACOES[cargo_nome]
    else:
        patente, saudacao = "Civil", "Olá, Civil! 🔒"

    canal_key = str(message.channel.id)
    if canal_key not in chat_history:
        chat_history[canal_key] = []

    chat_history[canal_key].append({
        "role":    "user",
        "content": f"[{patente}] {message.author.display_name}: {pergunta}",
    })

    if len(chat_history[canal_key]) > GROQ_HISTORY_LEN:
        chat_history[canal_key] = chat_history[canal_key][-GROQ_HISTORY_LEN:]

    async with message.channel.typing():
        try:
            msgs     = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history[canal_key]
            resposta = await ask_groq(msgs)
            chat_history[canal_key].append({"role": "assistant", "content": resposta})
            await message.reply(f"{saudacao}\n{resposta}")
            await db.add_log("ia", f"IA respondeu para {message.author.display_name}",
                             str(message.author.id), message.author.display_name)
        except Exception as exc:
            await message.reply(f"⚠️ Erro: {exc}")
            if DEBUG:
                print(f"[BOT] Erro IA: {exc}")


# ══════════════════════════════════════════════
# COMANDOS
# ══════════════════════════════════════════════
@bot.command(name="ping")
async def cmd_ping(ctx: commands.Context) -> None:
    ms = round(bot.latency * 1000)
    await ctx.send(f"🟢 Online! **{ms}ms** | EB DO RAFA 🪖")


@bot.command(name="patente")
async def cmd_patente(ctx: commands.Context) -> None:
    cargo_nome = get_main_role(ctx.author)
    if cargo_nome and cargo_nome in SAUDACOES:
        patente, saudacao, _ = SAUDACOES[cargo_nome]
        await ctx.send(f"{saudacao}\nSua patente é **{patente}**.")
    else:
        await ctx.send("🔒 Você não está verificado! Vá ao canal de verificação.")


@bot.command(name="aprovar")
@commands.has_permissions(manage_messages=True)
async def cmd_aprovar(ctx: commands.Context, rel_id: str) -> None:
    """!aprovar <id> — Aprova relatório pendente."""
    rel = await db.get_relatorio(rel_id)
    if not rel:
        await ctx.send(f"⚠️ Relatório `{rel_id}` não encontrado.")
        return
    if rel.get("status") != "pendente":
        await ctx.send(f"⚠️ Relatório `{rel_id}` já foi processado ({rel.get('status')}).")
        return

    nick = ctx.author.display_name
    ok   = await db.aprovar_relatorio(rel_id, nick)
    if not ok:
        await ctx.send("⚠️ Erro ao aprovar.")
        return

    # Envia ao canal final
    from api import send_to_discord
    await send_to_discord(rel["tipo"], rel["campos"])

    await db.add_log("aprov", f"Relatório {rel_id} aprovado via Discord por {nick}",
                     str(ctx.author.id), nick)
    await ctx.send(f"✅ Relatório `{rel_id}` aprovado e enviado!")


@bot.command(name="reprovar")
@commands.has_permissions(manage_messages=True)
async def cmd_reprovar(ctx: commands.Context, rel_id: str, *, motivo: str) -> None:
    """!reprovar <id> <motivo>"""
    rel = await db.get_relatorio(rel_id)
    if not rel:
        await ctx.send(f"⚠️ Relatório `{rel_id}` não encontrado.")
        return
    if rel.get("status") != "pendente":
        await ctx.send(f"⚠️ Já processado ({rel.get('status')}).")
        return

    nick = ctx.author.display_name
    ok   = await db.reprovar_relatorio(rel_id, motivo, nick)
    if not ok:
        await ctx.send("⚠️ Erro ao reprovar.")
        return

    await db.add_log("reprov", f"Relatório {rel_id} reprovado por {nick} — {motivo}",
                     str(ctx.author.id), nick)
    await ctx.send(
        f"❌ `{rel_id}` reprovado.\n"
        f"**Autor:** {rel.get('autor_nick', '—')}\n"
        f"**Motivo:** {motivo}"
    )


@bot.command(name="perms")
@commands.has_permissions(manage_messages=True)
async def cmd_perms(ctx: commands.Context, discord_id: str, acao: str) -> None:
    """!perms <discord_id> <dar|revogar>"""
    acao = acao.lower().strip()
    if acao not in ("dar", "revogar"):
        await ctx.send("⚠️ Use: `!perms <discord_id> dar` ou `!perms <discord_id> revogar`")
        return

    pode = (acao == "dar")
    await db.set_permissao_relatorio(discord_id, pode)
    nick = ctx.author.display_name
    await db.add_log("perm", f"Permissão {acao}da para {discord_id} por {nick}",
                     str(ctx.author.id), nick)
    resp = f"✅ Permissão **concedida** para `{discord_id}`." if pode else f"🚫 **Revogada** de `{discord_id}`."
    await ctx.send(resp)


@bot.command(name="limpar")
@commands.has_permissions(manage_messages=True)
async def cmd_limpar(ctx: commands.Context) -> None:
    """!limpar — limpa histórico de IA do canal."""
    canal_key = str(ctx.channel.id)
    if canal_key in chat_history:
        chat_history[canal_key] = []
    await ctx.send("🗑️ Histórico limpo.")


# ══════════════════════════════════════════════
# ERROR HANDLER
# ══════════════════════════════════════════════
@bot.event
async def on_command_error(ctx: commands.Context, error: Exception) -> None:
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("⛔ Sem permissão para este comando.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ Argumento faltando. Use `!help {ctx.command.name if ctx.command else '?'}`")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        if DEBUG:
            print(f"[BOT] Erro no comando: {error}")
        await db.add_log("erro", f"Erro cmd: {error}")


# ══════════════════════════════════════════════
# RUNNER
# ══════════════════════════════════════════════
async def start_bot() -> None:
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN não definido!")
    await bot.start(DISCORD_TOKEN)
