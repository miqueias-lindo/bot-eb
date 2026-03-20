import discord
from discord.ext import commands
import requests
import os
import time
from collections import defaultdict

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Anti-flood: máximo 3 mensagens por minuto por usuário
flood_control = defaultdict(list)
FLOOD_LIMITE = 3
FLOOD_JANELA = 60  # segundos

def verificar_flood(user_id):
    agora = time.time()
    mensagens = flood_control[user_id]
    # Remove mensagens antigas
    flood_control[user_id] = [t for t in mensagens if agora - t < FLOOD_JANELA]
    if len(flood_control[user_id]) >= FLOOD_LIMITE:
        return True  # está em flood
    flood_control[user_id].append(agora)
    return False

# Hierarquia de cargos (mais alto pro mais baixo)
HIERARQUIA = [
    "Fundador", "[CD] Con-Dono", "[DG] Diretor Geral", "[VDA] Vice-diretor-geral", "[M] Maneger",
    "[MAL] Marechal",
    "[GEN-E] General de Exército", "[GEN-D] General de Divisão", "[GEN-B] General de brigada", "[GEN] Generais",
    "[CEL] Coronel", "[T-CEL] Tenente Coronel", "[MAJ] Major", "[CAP] Capitão",
    "[1-TNT] Primeiro Tenente", "[2-TNT] Segundo tenente", "[AAO] Aspirante-A-oficial", "[CDT] Cadete", "[OF] Oficiais",
    "[SUB-T] Sub Tenente", "[GDS] Graduados",
    "[1-SGT] Primeiro sargento", "[2-SGT] Segundo Sargento", "[3-SGT] Terceiro sargento",
    "[PRÇ] Praças", "[CB] Cabo", "[SLD] Soldado", "[RCT] Recruta",
    "Supervisores", "[ADM] Administrador", "[MOD] Moderador", "[HLP] Helper", "[T-STF] Trial Staff",
    "[DEV] Developers", "[B] Builder",
    "Verificado",
]

# (patente_display, saudacao, nivel)
SAUDACOES = {
    "Fundador":                     ("Fundador",          "Olá, Fundador! 👑",                    "alto"),
    "[CD] Con-Dono":                ("Con-Dono",           "Olá, Con-Dono! 👑",                   "alto"),
    "[DG] Diretor Geral":           ("Diretor Geral",      "À vontade, Diretor Geral! 🏅",         "alto"),
    "[VDA] Vice-diretor-geral":     ("Vice-Diretor",       "À vontade, Vice-Diretor! 🏅",          "alto"),
    "[M] Maneger":                  ("Manager",            "À vontade, Manager! 🏅",               "alto"),
    "[MAL] Marechal":               ("Marechal",           "Sentido, Marechal! 🎖️",               "alto"),
    "[GEN-E] General de Exército":  ("General de Exército","À vontade, General de Exército! ⭐⭐⭐⭐","alto"),
    "[GEN-D] General de Divisão":   ("General de Divisão", "À vontade, General de Divisão! ⭐⭐⭐", "alto"),
    "[GEN-B] General de brigada":   ("General de Brigada", "À vontade, General de Brigada! ⭐⭐",  "alto"),
    "[GEN] Generais":               ("General",            "À vontade, General! ⭐",               "alto"),
    "[CEL] Coronel":                ("Coronel",            "À vontade, Coronel! 🔴",               "alto"),
    "[T-CEL] Tenente Coronel":      ("Tenente-Coronel",    "À vontade, Tenente-Coronel! 🔴",       "medio"),
    "[MAJ] Major":                  ("Major",              "À vontade, Major! 🔴",                 "medio"),
    "[CAP] Capitão":                ("Capitão",            "À vontade, Capitão! 🔴",               "medio"),
    "[1-TNT] Primeiro Tenente":     ("1º Tenente",         "À vontade, 1º Tenente! 🔴",            "medio"),
    "[2-TNT] Segundo tenente":      ("2º Tenente",         "À vontade, 2º Tenente! 🔴",            "medio"),
    "[AAO] Aspirante-A-oficial":    ("Aspirante",          "À vontade, Aspirante! 🔴",             "medio"),
    "[CDT] Cadete":                 ("Cadete",             "À vontade, Cadete! 🔴",                "medio"),
    "[OF] Oficiais":                ("Oficial",            "À vontade, Oficial! 🔴",               "medio"),
    "[SUB-T] Sub Tenente":          ("Subtenente",         "À vontade, Subtenente! 🟢",            "medio"),
    "[GDS] Graduados":              ("Graduado",           "À vontade, Graduado! 🟢",              "medio"),
    "[1-SGT] Primeiro sargento":    ("1º Sargento",        "À vontade, 1º Sargento! 🟢",           "medio"),
    "[2-SGT] Segundo Sargento":     ("2º Sargento",        "À vontade, 2º Sargento! 🟢",           "medio"),
    "[3-SGT] Terceiro sargento":    ("3º Sargento",        "Sentido, 3º Sargento! 🟢",             "baixo"),
    "[PRÇ] Praças":                 ("Praça",              "Sentido, Praça! 🟢",                   "baixo"),
    "[CB] Cabo":                    ("Cabo",               "Sentido, Cabo! 🟢",                    "baixo"),
    "[SLD] Soldado":                ("Soldado",            "Sentido, Soldado! 🟢",                 "baixo"),
    "[RCT] Recruta":                ("Recruta",            "Sentido, Recruta! 🫡",                 "baixo"),
    "Supervisores":                 ("Supervisor",         "Olá, Supervisor! 🛡️",                 "medio"),
    "[ADM] Administrador":          ("Administrador",      "Olá, Administrador! 🛡️",              "medio"),
    "[MOD] Moderador":              ("Moderador",          "Olá, Moderador! 🛡️",                  "medio"),
    "[HLP] Helper":                 ("Helper",             "Olá, Helper! 🛡️",                     "baixo"),
    "[T-STF] Trial Staff":          ("Trial Staff",        "Olá, Trial Staff! 🛡️",                "baixo"),
    "[DEV] Developers":             ("Developer",          "Olá, Dev! 💻",                         "medio"),
    "[B] Builder":                  ("Builder",            "Olá, Builder! 🔨",                     "baixo"),
    "Verificado":                   ("Cidadão",            "Olá, Cidadão! 🟡",                     "civil"),
}

SYSTEM_PROMPT = """Você é o assistente oficial do Exército Brasileiro (EB) no Roblox.
Responda em português, de forma CURTA e direta (máximo 3 linhas). Nunca mencione sites externos.
Foque apenas em: patentes, regras, treinamentos e eventos do EB no Roblox.
Tom: alto=muito formal | medio=respeitoso | baixo=firme e didático | civil=orientar a se verificar via Rover no canal de verificação."""

def get_cargo_principal(member):
    nomes = [r.name for r in member.roles]
    for cargo in HIERARQUIA:
        if cargo in nomes:
            return cargo
    return None

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
historico = {}

def perguntar_groq(mensagens):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "llama-3.3-70b-versatile", "messages": mensagens, "max_tokens": 150}
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
    data = response.json()
    if "choices" not in data:
        raise Exception(f"Erro da API: {data}")
    return data["choices"][0]["message"]["content"]

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="pelo Exército Brasileiro 🪖"))

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    if not message.content.startswith("!"):
        return

    pergunta = message.content[1:].strip()
    if not pergunta:
        return
    if pergunta.split()[0].lower() in ["ping", "limpar", "help", "patente"]:
        return

    # Anti-flood
    if verificar_flood(message.author.id):
        await message.reply("⛔ Devagar, soldado! Aguarde um momento antes de enviar outra mensagem.")
        return

    cargo_nome = get_cargo_principal(message.author)
    if cargo_nome and cargo_nome in SAUDACOES:
        patente, saudacao, nivel = SAUDACOES[cargo_nome]
    else:
        patente, saudacao, nivel = "Civil", "Olá, Civil! 🔒", "civil"

    canal_id = str(message.channel.id)
    if canal_id not in historico:
        historico[canal_id] = []

    historico[canal_id].append({"role": "user", "content": f"[{patente} - nivel:{nivel}] {message.author.display_name}: {pergunta}"})
    if len(historico[canal_id]) > 6:
        historico[canal_id] = historico[canal_id][-6:]

    async with message.channel.typing():
        try:
            mensagens = [{"role": "system", "content": SYSTEM_PROMPT}] + historico[canal_id]
            texto = perguntar_groq(mensagens)
            historico[canal_id].append({"role": "assistant", "content": texto})
            await message.reply(f"{saudacao}\n{texto}")
        except Exception as e:
            await message.reply(f"Erro: {e}")

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"🟢 Online! {round(bot.latency * 1000)}ms | Exército Brasileiro 🪖")

@bot.command(name="patente")
async def patente_cmd(ctx):
    cargo_nome = get_cargo_principal(ctx.author)
    if cargo_nome and cargo_nome in SAUDACOES:
        patente, saudacao, _ = SAUDACOES[cargo_nome]
        await ctx.send(f"{saudacao} Sua patente é **{patente}**.")
    else:
        await ctx.send("🔒 Você não está verificado! Vá ao canal de verificação e use o bot Rover para vincular sua conta Roblox.")

@bot.command(name="limpar")
@commands.has_permissions(manage_messages=True)
async def limpar(ctx):
    canal_id = str(ctx.channel.id)
    if canal_id in historico:
        historico[canal_id] = []
    await ctx.send("🗑️ Histórico limpo!")

bot.run(DISCORD_TOKEN)
