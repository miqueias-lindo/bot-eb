import discord
from discord.ext import commands
import requests
import os
import time
from collections import defaultdict

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not DISCORD_TOKEN or not GROQ_API_KEY:
    raise ValueError("⚠️ Configure DISCORD_TOKEN e GROQ_API_KEY!")

# ===== ANTI FLOOD =====
flood_control = defaultdict(list)
cooldowns = {}

FLOOD_LIMITE = 3
FLOOD_JANELA = 60

def verificar_flood(user_id):
    agora = time.time()

    if user_id in cooldowns and agora < cooldowns[user_id]:
        return True

    mensagens = flood_control[user_id]
    flood_control[user_id] = [t for t in mensagens if agora - t < FLOOD_JANELA]

    if len(flood_control[user_id]) >= FLOOD_LIMITE:
        cooldowns[user_id] = agora + 30
        return True

    flood_control[user_id].append(agora)
    return False

# ===== HIERARQUIA =====
HIERARQUIA = [
    "Fundador","[CD] Con-Dono","[DG] Diretor Geral","[VDA] Vice-diretor-geral","[M] Maneger",
    "[MAL] Marechal","[GEN-E] General de Exército","[GEN-D] General de Divisão",
    "[GEN-B] General de brigada","[GEN] Generais","[CEL] Coronel","[T-CEL] Tenente Coronel",
    "[MAJ] Major","[CAP] Capitão","[1-TNT] Primeiro Tenente","[2-TNT] Segundo tenente",
    "[AAO] Aspirante-A-oficial","[CDT] Cadete","[OF] Oficiais","[SUB-T] Sub Tenente",
    "[GDS] Graduados","[1-SGT] Primeiro sargento","[2-SGT] Segundo Sargento",
    "[3-SGT] Terceiro sargento","[PRÇ] Praças","[CB] Cabo","[SLD] Soldado","[RCT] Recruta",
    "Supervisores","[ADM] Administrador","[MOD] Moderador","[HLP] Helper",
    "[T-STF] Trial Staff","[DEV] Developers","[B] Builder","Verificado"
]

SAUDACOES = {
    "Fundador": ("Fundador","Olá, Fundador! 👑","alto"),
    "[MAL] Marechal": ("Marechal","Sentido, Marechal! 🎖️","alto"),
    "[GEN-E] General de Exército": ("General","À vontade, General! ⭐⭐⭐⭐","alto"),
    "[CEL] Coronel": ("Coronel","À vontade, Coronel! 🔴","medio"),
    "[CAP] Capitão": ("Capitão","À vontade, Capitão! 🔴","medio"),
    "[SUB-T] Sub Tenente": ("Subtenente","À vontade! 🟢","medio"),
    "[3-SGT] Terceiro sargento": ("3º Sargento","Sentido! 🟢","baixo"),
    "[SLD] Soldado": ("Soldado","Sentido! 🟢","baixo"),
    "[RCT] Recruta": ("Recruta","Sentido! 🫡","baixo"),
    "Verificado": ("Cidadão","Olá! 🟡","civil"),
}

def get_cargo_principal(member):
    roles = set(r.name for r in member.roles)
    for cargo in HIERARQUIA:
        if cargo in roles:
            return cargo
    return None

# ===== BOT =====
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
historico = {}

SYSTEM_PROMPT = """Você é o assistente do EB no Roblox.
Responda curto, direto (máx 3 linhas).
Foque em patentes, regras, treinamentos e eventos."""

def perguntar_groq(mensagens):
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": mensagens,
            "max_tokens": 150
        }

        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    except:
        return "⚠️ Erro na IA. Tente novamente."

@bot.event
async def on_ready():
    print(f"🟢 Online como {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    if not message.content.startswith("!"):
        return

    pergunta = message.content[1:].strip()
    if not pergunta:
        return

    # FLOOD
    if verificar_flood(message.author.id):
        await message.reply("⛔ Aguarde antes de enviar outra mensagem.")
        return

    cargo = get_cargo_principal(message.author)

    if not cargo:
        await message.reply("🔒 Verifique-se com o Rover.")
        return

    patente, saudacao, nivel = SAUDACOES.get(
        cargo, ("Civil","Olá!","civil")
    )

    # BLOQUEIO CIVIL
    if nivel == "civil":
        await message.reply("🔒 Apenas militares podem usar o sistema.")
        return

    canal_id = str(message.channel.id)
    historico.setdefault(canal_id, [])

    historico[canal_id].append({
        "role": "user",
        "content": pergunta
    })

    historico[canal_id] = historico[canal_id][-6:]

    async with message.channel.typing():
        resposta = perguntar_groq(
            [{"role": "system", "content": SYSTEM_PROMPT}] + historico[canal_id]
        )

        historico[canal_id].append({
            "role": "assistant",
            "content": resposta
        })

        await message.reply(f"{saudacao}\n{resposta}")

# ===== COMANDOS =====

@bot.command()
async def ping(ctx):
    await ctx.send(f"🟢 {round(bot.latency * 1000)}ms")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def limpar(ctx):
    historico[str(ctx.channel.id)] = []
    await ctx.send("🗑️ Histórico limpo!")

@bot.command()
async def ordem(ctx, *, texto):
    await ctx.send(f"📢 ORDEM: {texto.upper()}")

# ===== START =====
bot.run(DISCORD_TOKEN)
