import discord
from discord.ext import commands
import requests
import os
import time
from collections import defaultdict
from datetime import timedelta

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

def get_cargo_principal(member):
    roles = set(r.name for r in member.roles)
    for cargo in HIERARQUIA:
        if cargo in roles:
            return cargo
    return None

# ===== NÍVEIS =====
ALTOS = [
    "Fundador","[CD] Con-Dono","[DG] Diretor Geral","[VDA] Vice-diretor-geral",
    "[M] Maneger","[MAL] Marechal","[GEN-E] General de Exército",
    "[GEN-D] General de Divisão","[GEN-B] General de brigada","[GEN] Generais"
]

MEDIOS = [
    "[CEL] Coronel","[T-CEL] Tenente Coronel","[MAJ] Major","[CAP] Capitão",
    "[1-TNT] Primeiro Tenente","[2-TNT] Segundo tenente","[AAO] Aspirante-A-oficial",
    "[CDT] Cadete","[OF] Oficiais","[SUB-T] Sub Tenente","[GDS] Graduados",
    "[1-SGT] Primeiro sargento","[2-SGT] Segundo Sargento"
]

BAIXOS = [
    "[3-SGT] Terceiro sargento","[PRÇ] Praças","[CB] Cabo",
    "[SLD] Soldado","[RCT] Recruta"
]

STAFF = [
    "Supervisores","[ADM] Administrador","[MOD] Moderador","[HLP] Helper",
    "[T-STF] Trial Staff","[DEV] Developers","[B] Builder"
]

def gerar_info_cargo(cargo):
    if not cargo:
        return ("Civil", "Olá! 🔒", "civil")

    if cargo in ALTOS:
        return (cargo, "À vontade! 🎖️", "alto")

    if cargo in MEDIOS:
        return (cargo, "À vontade! 🔴", "medio")

    if cargo in BAIXOS:
        return (cargo, "Sentido! 🟢", "baixo")

    if cargo in STAFF:
        return (cargo, "Olá, Staff! 🛡️", "staff")

    if cargo == "Verificado":
        return ("Cidadão", "Olá! 🟡", "civil")

    return (cargo, "Olá! 🟡", "civil")

# ===== DISCIPLINA HARDCORE =====
PALAVROES = [
    "fdp","filha da puta","porra","caralho","bosta",
    "vsf","vai se fuder","arrombado","desgraça"
]

DESRESPEITO = [
    "bot lixo","tu é burro","vc é burro","comandante lixo",
    "idiota","retardado"
]

# ===== BOT =====
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
historico = {}

SYSTEM_PROMPT = """Você é um COMANDANTE do Exército Brasileiro (EB) no Roblox.

Fale como um superior militar:
- Linguagem firme, respeitosa e natural
- Use termos como "soldado", "atenção", "em posição"
- Nunca fale como robô
- Máximo 3 linhas

Corrija comportamento se necessário.
Foque em regras, treinamentos e patentes."""

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

    cargo = get_cargo_principal(message.author)
    patente, saudacao, nivel = gerar_info_cargo(cargo)

    msg = message.content.lower()

    # 🚨 HARDCORE PUNIÇÃO
    if cargo not in STAFF:
        if any(p in msg for p in PALAVROES) or any(d in msg for d in DESRESPEITO):
            try:
                await message.author.timeout(
                    discord.utils.utcnow() + timedelta(minutes=1),
                    reason="Indisciplina"
                )
                await message.reply("🔇 Silenciado por 1 minuto. Disciplina, soldado.")
            except:
                await message.reply("🔇 Usuário punido.")
            return

    # 🫡 EXIGIR RESPOSTA MILITAR
    if nivel == "baixo":
        if not any(x in msg for x in ["sim senhor", "sim, senhor", "entendido"]):
            await message.reply("🪖 Responda corretamente: 'Sim, senhor!'")
            return

    # 🚫 ANTI FLOOD (exceto staff)
    if cargo not in STAFF:
        if verificar_flood(message.author.id):
            await message.reply("⛔ Controle-se, soldado.")
            return

    # 🔒 BLOQUEIO CIVIL
    if nivel == "civil":
        await message.reply("🔒 Verifique-se para usar o sistema.")
        return

    canal_id = str(message.channel.id)
    historico.setdefault(canal_id, [])

    historico[canal_id].append({"role": "user", "content": pergunta})
    historico[canal_id] = historico[canal_id][-6:]

    async with message.channel.typing():
        resposta = perguntar_groq(
            [{"role": "system", "content": SYSTEM_PROMPT}] + historico[canal_id]
        )

        historico[canal_id].append({"role": "assistant", "content": resposta})

        await message.reply(f"{saudacao}\n📌 {resposta}")

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
