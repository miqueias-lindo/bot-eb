import discord
from discord.ext import commands
import requests
import os
import time
import json
import asyncio
import base64
from collections import defaultdict
from aiohttp import web

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GUILD_ID = int(os.environ.get("GUILD_ID", "0"))
PORT = int(os.environ.get("PORT", "8080"))

# IDs dos canais
CANAL_RECRUTAMENTO = 1470637472781304022
CANAL_EVENTOS = 1470635180535582720
CANAL_ANUNCIOS = 1470635151523578078
CANAL_SORTEIOS = 1472329428888584357
CANAL_VENDAS = 1470645650113958000
CANAL_TREINO = 1470637515441569893
CANAL_EXILIO = 1470637554825957591
CANAL_BANIMENTO = 1470637613332431002
CANAL_REBAIXAMENTO = 1470637643888070762
CANAL_ADV = 1470637705032499335

# Anti-flood
flood_control = defaultdict(list)
FLOOD_LIMITE = 3
FLOOD_JANELA = 60

def verificar_flood(user_id):
    agora = time.time()
    flood_control[user_id] = [t for t in flood_control[user_id] if agora - t < FLOOD_JANELA]
    if len(flood_control[user_id]) >= FLOOD_LIMITE:
        return True
    flood_control[user_id].append(agora)
    return False

HIERARQUIA = [
    "Fundador", "[CD] Con-Dono", "[DG] Diretor Geral", "[VDA] Vice-diretor-geral", "[M] Maneger",
    "[MAL] Marechal", "[GEN-E] General de Exército", "[GEN-D] General de Divisão",
    "[GEN-B] General de brigada", "[GEN] Generais", "[CEL] Coronel", "[T-CEL] Tenente Coronel",
    "[MAJ] Major", "[CAP] Capitão", "[1-TNT] Primeiro Tenente", "[2-TNT] Segundo tenente",
    "[AAO] Aspirante-A-oficial", "[CDT] Cadete", "[OF] Oficiais", "[SUB-T] Sub Tenente",
    "[GDS] Graduados", "[1-SGT] Primeiro sargento", "[2-SGT] Segundo Sargento",
    "[3-SGT] Terceiro sargento", "[PRÇ] Praças", "[CB] Cabo", "[SLD] Soldado", "[RCT] Recruta",
    "Supervisores", "[ADM] Administrador", "[MOD] Moderador", "[HLP] Helper", "[T-STF] Trial Staff",
    "[DEV] Developers", "[B] Builder", "Verificado",
]

SAUDACOES = {
    "Fundador": ("Fundador", "Olá, Fundador! 👑", "alto"),
    "[CD] Con-Dono": ("Con-Dono", "Olá, Con-Dono! 👑", "alto"),
    "[DG] Diretor Geral": ("Diretor Geral", "À vontade, Diretor Geral! 🏅", "alto"),
    "[VDA] Vice-diretor-geral": ("Vice-Diretor", "À vontade, Vice-Diretor! 🏅", "alto"),
    "[M] Maneger": ("Manager", "À vontade, Manager! 🏅", "alto"),
    "[MAL] Marechal": ("Marechal", "Sentido, Marechal! 🎖️", "alto"),
    "[GEN-E] General de Exército": ("General de Exército", "À vontade, General de Exército! ⭐⭐⭐⭐", "alto"),
    "[GEN-D] General de Divisão": ("General de Divisão", "À vontade, General de Divisão! ⭐⭐⭐", "alto"),
    "[GEN-B] General de brigada": ("General de Brigada", "À vontade, General de Brigada! ⭐⭐", "alto"),
    "[GEN] Generais": ("General", "À vontade, General! ⭐", "alto"),
    "[CEL] Coronel": ("Coronel", "À vontade, Coronel! 🔴", "alto"),
    "[T-CEL] Tenente Coronel": ("Tenente-Coronel", "À vontade, Tenente-Coronel! 🔴", "medio"),
    "[MAJ] Major": ("Major", "À vontade, Major! 🔴", "medio"),
    "[CAP] Capitão": ("Capitão", "À vontade, Capitão! 🔴", "medio"),
    "[1-TNT] Primeiro Tenente": ("1º Tenente", "À vontade, 1º Tenente! 🔴", "medio"),
    "[2-TNT] Segundo tenente": ("2º Tenente", "À vontade, 2º Tenente! 🔴", "medio"),
    "[AAO] Aspirante-A-oficial": ("Aspirante", "À vontade, Aspirante! 🔴", "medio"),
    "[CDT] Cadete": ("Cadete", "À vontade, Cadete! 🔴", "medio"),
    "[OF] Oficiais": ("Oficial", "À vontade, Oficial! 🔴", "medio"),
    "[SUB-T] Sub Tenente": ("Subtenente", "À vontade, Subtenente! 🟢", "medio"),
    "[GDS] Graduados": ("Graduado", "À vontade, Graduado! 🟢", "medio"),
    "[1-SGT] Primeiro sargento": ("1º Sargento", "À vontade, 1º Sargento! 🟢", "medio"),
    "[2-SGT] Segundo Sargento": ("2º Sargento", "À vontade, 2º Sargento! 🟢", "medio"),
    "[3-SGT] Terceiro sargento": ("3º Sargento", "Sentido, 3º Sargento! 🟢", "baixo"),
    "[PRÇ] Praças": ("Praça", "Sentido, Praça! 🟢", "baixo"),
    "[CB] Cabo": ("Cabo", "Sentido, Cabo! 🟢", "baixo"),
    "[SLD] Soldado": ("Soldado", "Sentido, Soldado! 🟢", "baixo"),
    "[RCT] Recruta": ("Recruta", "Sentido, Recruta! 🫡", "baixo"),
    "Supervisores": ("Supervisor", "Olá, Supervisor! 🛡️", "medio"),
    "[ADM] Administrador": ("Administrador", "Olá, Administrador! 🛡️", "medio"),
    "[MOD] Moderador": ("Moderador", "Olá, Moderador! 🛡️", "medio"),
    "[HLP] Helper": ("Helper", "Olá, Helper! 🛡️", "baixo"),
    "[T-STF] Trial Staff": ("Trial Staff", "Olá, Trial Staff! 🛡️", "baixo"),
    "[DEV] Developers": ("Developer", "Olá, Dev! 💻", "medio"),
    "[B] Builder": ("Builder", "Olá, Builder! 🔨", "baixo"),
    "Verificado": ("Cidadão", "Olá, Cidadão! 🟡", "civil"),
}

SYSTEM_PROMPT = """Você é o assistente oficial do Exército Brasileiro (EB) no Roblox.
Responda em português, de forma CURTA e direta (máximo 3 linhas). Nunca mencione sites externos.
Foque apenas em: patentes, regras, treinamentos e eventos do EB no Roblox."""

def get_cargo_principal(member):
    nomes = [r.name for r in member.roles]
    for cargo in HIERARQUIA:
        if cargo in nomes:
            return cargo
    return None

def perguntar_groq(mensagens):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "llama-3.3-70b-versatile", "messages": mensagens, "max_tokens": 150}
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
    data = response.json()
    if "choices" not in data:
        raise Exception(f"Erro da API: {data}")
    return data["choices"][0]["message"]["content"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
historico = {}

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Content-Type": "application/json"
    }

async def handle_options(request):
    return web.Response(headers=cors_headers())

async def handle_ping(request):
    return web.Response(text=json.dumps({"status": "online"}), headers=cors_headers())

async def handle_cargos(request):
    user_id = request.rel_url.query.get("user_id")
    if not user_id:
        return web.Response(text=json.dumps({"error": "user_id obrigatorio"}), headers=cors_headers(), status=400)
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return web.Response(text=json.dumps({"error": "Servidor nao encontrado"}), headers=cors_headers(), status=404)
    try:
        member = await guild.fetch_member(int(user_id))
        cargos = [{"id": str(r.id), "nome": r.name} for r in member.roles if r.name != "@everyone"]
        cargo_principal = get_cargo_principal(member)
        patente = "Cidadão"
        if cargo_principal and cargo_principal in SAUDACOES:
            patente = SAUDACOES[cargo_principal][0]
        return web.Response(text=json.dumps({
            "user_id": user_id,
            "cargos": cargos,
            "cargo_principal": cargo_principal,
            "patente": patente
        }), headers=cors_headers())
    except discord.NotFound:
        return web.Response(text=json.dumps({"error": "Membro nao encontrado"}), headers=cors_headers(), status=404)
    except Exception as e:
        return web.Response(text=json.dumps({"error": str(e)}), headers=cors_headers(), status=500)

async def handle_relatorio(request):
    try:
        data = await request.json()
        tipo = data.get("tipo")
        campos = data.get("campos", {})
        imagem_base64 = data.get("imagem")

        canal_map = {
            "recrutamento": CANAL_RECRUTAMENTO,
            "treino": CANAL_TREINO,
            "exilio": CANAL_EXILIO,
            "banimento": CANAL_BANIMENTO,
            "rebaixamento": CANAL_REBAIXAMENTO,
            "advertencia": CANAL_ADV,
            "venda": CANAL_VENDAS,
            "promocao": CANAL_ANUNCIOS,
            "aviso": CANAL_ANUNCIOS,
            "evento_eventos": CANAL_EVENTOS,
            "evento_anuncios": CANAL_ANUNCIOS,
            "evento_sorteios": CANAL_SORTEIOS,
        }

        canal_id = canal_map.get(tipo)
        if not canal_id:
            return web.Response(text=json.dumps({"error": "Tipo invalido"}), headers=cors_headers(), status=400)

        canal = bot.get_channel(canal_id)
        if not canal:
            return web.Response(text=json.dumps({"error": "Canal nao encontrado"}), headers=cors_headers(), status=404)

        # Monta a mensagem conforme o tipo
        if tipo == "advertencia":
            msg = f"**⚠️ RELATÓRIO DE ADVERTÊNCIA ⚠️**\n\n👤 Jogador: {campos.get('jogador','—')}\n📝 Motivo: {campos.get('motivo','—')}\n🔢 Grau da Advertência: {campos.get('grau','—')}\n📅 Data: {campos.get('data','—')}"
        elif tipo == "rebaixamento":
            msg = f"**📉 RELATÓRIO DE REBAIXAMENTO 📉**\n\n👤 USUÁRIO: {campos.get('usuario','—')}\n⬆️ CARGO ANTERIOR: {campos.get('cargo_anterior','—')}\n⬇️ NOVO CARGO: {campos.get('novo_cargo','—')}\n📝 MOTIVO: {campos.get('motivo','—')}\n📅 DATA: {campos.get('data','—')}"
        elif tipo == "banimento":
            msg = f"**🚫 RELATÓRIO DE BANIMENTO 🚫**\n\n👤 Jogador: {campos.get('jogador','—')}\n📝 Motivo: {campos.get('motivo','—')}\n⏳ Tempo: {campos.get('tempo','—')}\n📅 Data: {campos.get('data','—')}"
        elif tipo == "exilio":
            msg = f"**🏴‍☠️ RELATÓRIO DE EXÍLIO 🏴‍☠️**\n\n👤 EXILADO: {campos.get('exilado','—')}\n📝 MOTIVO: {campos.get('motivo','—')}\n⛓️ TIPO: {campos.get('tipo_exilio','—')}\n📅 DATA: {campos.get('data','—')}\n👮 RESPONSÁVEL: {campos.get('responsavel','—')}"
        elif tipo == "treino":
            msg = f"**📖 RELATÓRIO DE TREINAMENTO 📖**\n\n👤 INSTRUTOR: {campos.get('instrutor','—')}\n👥 TREINADO(S): {campos.get('treinados','—')}\n📅 DATA E HORA: {campos.get('data','—')}\n📊 STATUS: {campos.get('status','—')}\n📝 OBSERVAÇÕES: {campos.get('observacoes','—')}"
        elif tipo == "recrutamento":
            msg = f"**🪖 RELATÓRIO DE RECRUTAMENTO 🪖**\n\n👤 RECRUTADO: {campos.get('recrutado','—')}\n👮 RECRUTADOR: {campos.get('recrutador','—')}\n📅 DATA: {campos.get('data','—')}\n📝 OBSERVAÇÕES: {campos.get('observacoes','—')}"
        elif tipo == "venda":
            msg = f"**💰 RELATÓRIO DE VENDA 💰**\n\n👤 COMPRADOR: {campos.get('nick','—')}\n🎖️ PATENTE: {campos.get('patente','—')}\n💵 VALOR: R$ {campos.get('preco','—')}\n📅 DATA: {campos.get('data','—')}\n⏳ STATUS: AGUARDANDO CONFIRMAÇÃO"
        elif tipo == "promocao":
            msg = f"**⬆️ SOLICITAÇÃO DE PROMOÇÃO ⬆️**\n\n👤 NICK: {campos.get('nick','—')}\n📊 PATENTE ATUAL: {campos.get('patente_atual','—')}\n🎯 PATENTE DESEJADA: {campos.get('patente_desejada','—')}\n📝 JUSTIFICATIVA: {campos.get('justificativa','—')}"
        elif tipo == "aviso":
            msg = f"**📢 AVISO OFICIAL 📢**\n\n**{campos.get('titulo','—')}**\n\n{campos.get('mensagem','—')}"
        elif tipo.startswith("evento_"):
            msg = f"**📅 NOVO EVENTO: {campos.get('nome','—')} 📅**\n\n🎯 TIPO: {campos.get('tipo','—')}\n📅 DATA: {campos.get('data','—')}\n📝 DESCRIÇÃO: {campos.get('descricao','—')}"
        else:
            msg = str(campos)

        # Envia com ou sem imagem
        if imagem_base64:
            img_data = base64.b64decode(imagem_base64.split(",")[-1])
            file = discord.File(fp=__import__("io").BytesIO(img_data), filename="prova.png")
            await canal.send(msg, file=file)
        else:
            await canal.send(msg)

        return web.Response(text=json.dumps({"ok": True}), headers=cors_headers())
    except Exception as e:
        return web.Response(text=json.dumps({"error": str(e)}), headers=cors_headers(), status=500)

async def start_web_server():
    app = web.Application()
    app.router.add_route("OPTIONS", "/{path_info:.*}", handle_options)
    app.router.add_get("/ping", handle_ping)
    app.router.add_get("/cargos", handle_cargos)
    app.router.add_post("/relatorio", handle_relatorio)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"API rodando na porta {PORT}")

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="pelo Exército Brasileiro 🪖"))
    await start_web_server()

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
    if verificar_flood(message.author.id):
        await message.reply("⛔ Devagar, soldado! Aguarde um momento.")
        return
    cargo_nome = get_cargo_principal(message.author)
    if cargo_nome and cargo_nome in SAUDACOES:
        patente, saudacao, nivel = SAUDACOES[cargo_nome]
    else:
        patente, saudacao, nivel = "Civil", "Olá, Civil! 🔒", "civil"
    canal_id = str(message.channel.id)
    if canal_id not in historico:
        historico[canal_id] = []
    historico[canal_id].append({"role": "user", "content": f"[{patente}] {message.author.display_name}: {pergunta}"})
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
        await ctx.send("🔒 Você não está verificado! Vá ao canal de verificação e use o bot Rover.")

@bot.command(name="limpar")
@commands.has_permissions(manage_messages=True)
async def limpar(ctx):
    canal_id = str(ctx.channel.id)
    if canal_id in historico:
        historico[canal_id] = []
    await ctx.send("🗑️ Histórico limpo!")

bot.run(DISCORD_TOKEN)
