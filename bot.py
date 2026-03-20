import discord
from discord.ext import commands
import os
import json
from collections import defaultdict
from datetime import timedelta
import requests

# ===== CONFIG =====
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== CANAIS =====
RELATORIOS_CANAIS = {
    "recrutamento": 1470637472781304022,
    "treino": 1470637515441569893,
    "exilio": 1470637554825957591,
    "banimento": 1470637613332431002,
    "rebaixamento": 1470637643888070762,
    "advertencia": 1470637705032499335
}

LOG_CHANNEL_NAME = "logs"

# ===== BANCO =====
def load_db():
    try:
        with open("db.json", "r") as f:
            return json.load(f)
    except:
        return {"fichas": {}}

def save_db():
    try:
        with open("db.json", "w") as f:
            json.dump(db, f, indent=4)
    except Exception as e:
        print("Erro ao salvar DB:", e)

db = load_db()

def get_ficha(user_id):
    uid = str(user_id)
    if uid not in db["fichas"]:
        db["fichas"][uid] = {
            "treinos": 0,
            "recrutamentos": 0,
            "historico": []
        }
    return db["fichas"][uid]

def add_ficha(user_id, registro):
    ficha = get_ficha(user_id)
    ficha["historico"].append(registro)
    save_db()

# ===== FUNÇÕES =====
async def enviar_relatorio(guild, tipo, texto):
    try:
        canal_id = RELATORIOS_CANAIS.get(tipo)
        canal = guild.get_channel(canal_id)

        if not canal:
            print(f"[ERRO] Canal não encontrado: {tipo}")
            return

        await canal.send(texto)

    except Exception as e:
        print("Erro ao enviar relatório:", e)

async def log(guild, texto):
    try:
        canal = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
        if canal:
            await canal.send(texto)
    except:
        pass

# ===== DISCIPLINA =====
infractions = defaultdict(int)
PALAVROES = ["fdp","porra","caralho"]
STAFF = ["[DEV] Developers","[ADM] Administrador","[MOD] Moderador"]

def is_staff(member):
    return any(role.name in STAFF for role in member.roles)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    if not message.content.startswith("!"):
        return

    if not is_staff(message.author):
        if any(p in message.content.lower() for p in PALAVROES):
            infractions[message.author.id] += 1

            if infractions[message.author.id] >= 3:
                try:
                    await message.author.timeout(
                        discord.utils.utcnow() + timedelta(minutes=1)
                    )
                    await log(message.guild, f"{message.author} punido por indisciplina")
                except:
                    pass

# ===== FICHA =====
@bot.command()
async def ficha(ctx, member: discord.Member = None):
    try:
        member = member or ctx.author
        ficha = get_ficha(member.id)

        await ctx.send(
            f"📋 Ficha de {member.name}\n"
            f"Treinos: {ficha['treinos']}\n"
            f"Recrutamentos: {ficha['recrutamentos']}\n"
            f"Histórico: {ficha['historico'][-5:]}"
        )
    except Exception as e:
        await ctx.send("Erro ao puxar ficha.")
        print(e)

# ===== TREINO =====
@bot.command()
async def treino_rel(ctx, status: str, *, resto):
    try:
        nicks, obs = resto.split("|")
    except:
        await ctx.send("Formato: !treino_rel Aprovado nick1,nick2 | obs")
        return

    texto = f"""📖 RELATÓRIO DE TREINAMENTO 📖

👤 Instrutor: {ctx.author.mention}
👥 Treinado(s): {nicks}
📅 Data: {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M')}
📊 Status: {status}
📝 Observações: {obs}
"""

    await enviar_relatorio(ctx.guild, "treino", texto)
    await ctx.send("Relatório enviado.")

    ficha = get_ficha(ctx.author.id)
    ficha["treinos"] += 1
    add_ficha(ctx.author.id, f"Treino: {nicks}")

# ===== RECRUTAMENTO =====
@bot.command()
async def recruta_rel(ctx, *, resto):
    try:
        nicks, obs = resto.split("|")
    except:
        await ctx.send("Formato: !recruta_rel nick1,nick2 | obs")
        return

    texto = f"""🪖 RELATÓRIO DE RECRUTAMENTO 🪖

👤 Responsável: {ctx.author.mention}
👥 Recrutado(s): {nicks}
📅 Data: {discord.utils.utcnow().strftime('%d/%m/%Y')}
📝 Observações: {obs}
"""

    await enviar_relatorio(ctx.guild, "recrutamento", texto)
    await ctx.send("Relatório enviado.")

    ficha = get_ficha(ctx.author.id)
    ficha["recrutamentos"] += 1
    add_ficha(ctx.author.id, f"Recrutou: {nicks}")

# ===== ADVERTÊNCIA =====
@bot.command()
async def adv(ctx, membro: discord.Member, grau: str, *, resto):
    try:
        motivo, provas = resto.split("|")
    except:
        await ctx.send("Formato: !adv @user 1/3 motivo | prova")
        return

    texto = f"""⚠️ RELATÓRIO DE ADVERTÊNCIA ⚠️

👤 Jogador: {membro.mention}
📝 Motivo: {motivo}
🔢 Grau: {grau}
📅 Data: {discord.utils.utcnow().strftime('%d/%m/%Y')}
📂 Provas: {provas}
"""

    await enviar_relatorio(ctx.guild, "advertencia", texto)
    add_ficha(membro.id, f"Advertência {grau} - {motivo}")

# ===== REBAIXAMENTO =====
@bot.command()
async def rebaixar_rel(ctx, membro: discord.Member, cargo_antigo: str, cargo_novo: str, *, resto):
    try:
        motivo, provas = resto.split("|")
    except:
        await ctx.send("Formato: !rebaixar_rel @user Cargo1 Cargo2 motivo | prova")
        return

    texto = f"""📉 RELATÓRIO DE REBAIXAMENTO 📉

👤 Usuário: {membro.mention}
⬆️ Cargo anterior: {cargo_antigo}
⬇️ Novo cargo: {cargo_novo}
📝 Motivo: {motivo}
📅 Data: {discord.utils.utcnow().strftime('%d/%m/%Y')}
📸 Provas: {provas}
"""

    await enviar_relatorio(ctx.guild, "rebaixamento", texto)
    add_ficha(membro.id, f"Rebaixado {cargo_antigo} -> {cargo_novo}")

# ===== BANIMENTO =====
@bot.command()
async def ban_rel(ctx, membro: discord.Member, tempo: str, *, resto):
    try:
        motivo, provas = resto.split("|")
    except:
        await ctx.send("Formato: !ban_rel @user tempo motivo | prova")
        return

    texto = f"""🚫 RELATÓRIO DE BANIMENTO 🚫

👤 Jogador: {membro.mention}
📝 Motivo: {motivo}
⏳ Tempo: {tempo}
📅 Data: {discord.utils.utcnow().strftime('%d/%m/%Y')}
📂 Provas: {provas}
"""

    await enviar_relatorio(ctx.guild, "banimento", texto)
    add_ficha(membro.id, f"Banido {tempo} - {motivo}")

# ===== EXÍLIO =====
@bot.command()
async def exilio(ctx, membro: discord.Member, tipo: str, *, resto):
    try:
        motivo, provas = resto.split("|")
    except:
        await ctx.send("Formato: !exilio @user tipo motivo | prova")
        return

    texto = f"""🏴‍☠️ RELATÓRIO DE EXÍLIO 🏴‍☠️

👤 Exilado: {membro.mention}
📝 Motivo: {motivo}
⛓️ Tipo: {tipo}
📅 Data: {discord.utils.utcnow().strftime('%d/%m/%Y')}
👮 Responsável: {ctx.author.mention}
📂 Provas: {provas}
"""

    await enviar_relatorio(ctx.guild, "exilio", texto)
    add_ficha(membro.id, f"Exilado {tipo} - {motivo}")

# ===== IA =====
memoria = defaultdict(list)

@bot.command()
async def ia(ctx, *, pergunta):
    try:
        memoria[ctx.author.id].append({"role": "user", "content": pergunta})

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": memoria[ctx.author.id]
        }

        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=20
        )

        data = r.json()

        if "choices" not in data:
            await ctx.send("Erro na IA.")
            return

        resposta = data["choices"][0]["message"]["content"]

        memoria[ctx.author.id].append({"role": "assistant", "content": resposta})

        await ctx.send(resposta)

    except Exception as e:
        print(e)
        await ctx.send("Erro ao usar IA.")

# ===== START =====
bot.run(DISCORD_TOKEN)
