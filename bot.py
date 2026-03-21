"""
╔══════════════════════════════════════════════════════════╗
║          EB DO RAFA — BOT + API v2.0                     ║
║  discord.py + aiohttp  |  Python 3.10+                   ║
║                                                          ║
║  ENDPOINTS:                                              ║
║   GET  /ping              — health check                 ║
║   GET  /cargos?user_id=   — busca cargos Discord         ║
║   POST /relatorio         — envia relatório aprovado     ║
║   POST /pendente          — recebe relatório pendente    ║
║   GET  /logs              — retorna logs (staff)         ║
║   GET  /permissoes        — retorna mapa de permissões   ║
║   POST /permissoes        — atualiza permissão           ║
╚══════════════════════════════════════════════════════════╝

Variáveis de ambiente necessárias:
  DISCORD_TOKEN  — token do bot
  GUILD_ID       — ID do servidor Discord
  GROQ_API_KEY   — chave da API Groq (IA)
  PORT           — porta da API (padrão: 8080)
  CANAL_APROVACAO — ID do canal para relatórios pendentes
"""

import discord
from discord.ext import commands
import requests
import os
import time
import json
import asyncio
import base64
import uuid
from collections import defaultdict
from aiohttp import web
from datetime import datetime

# ══════════════════════════════════════════════
# CONFIGURAÇÃO
# ══════════════════════════════════════════════
DISCORD_TOKEN    = os.environ.get("DISCORD_TOKEN")
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY")
GUILD_ID         = int(os.environ.get("GUILD_ID", "0"))
PORT             = int(os.environ.get("PORT", "8080"))

# IDs dos canais de destino final (após aprovação)
CANAL_RECRUTAMENTO = 1470637472781304022
CANAL_EVENTOS      = 1470635180535582720
CANAL_ANUNCIOS     = 1470635151523578078
CANAL_SORTEIOS     = 1472329428888584357
CANAL_TREINO       = 1470637515441569893
CANAL_EXILIO       = 1470637554825957591
CANAL_BANIMENTO    = 1470637613332431002
CANAL_REBAIXAMENTO = 1470637643888070762
CANAL_ADV          = 1470637705032499335
CANAL_APROVACAO    = int(os.environ.get("CANAL_APROVACAO", "0"))  # Canal de aprovação

# ══════════════════════════════════════════════
# HIERARQUIA E SAUDAÇÕES
# ══════════════════════════════════════════════
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
    "Fundador":                  ("Fundador",         "Olá, Fundador! 👑",                "alto"),
    "[CD] Con-Dono":             ("Con-Dono",          "Olá, Con-Dono! 👑",                "alto"),
    "[DG] Diretor Geral":        ("Diretor Geral",     "À vontade, Diretor Geral! 🏅",     "alto"),
    "[VDA] Vice-diretor-geral":  ("Vice-Diretor",      "À vontade, Vice-Diretor! 🏅",      "alto"),
    "[M] Maneger":               ("Manager",           "À vontade, Manager! 🏅",            "alto"),
    "[MAL] Marechal":            ("Marechal",          "Sentido, Marechal! 🎖️",             "alto"),
    "[GEN-E] General de Exército":("General de Exército","À vontade, General de Exército! ⭐⭐⭐⭐","alto"),
    "[GEN-D] General de Divisão": ("General de Divisão","À vontade, General de Divisão! ⭐⭐⭐","alto"),
    "[GEN-B] General de brigada": ("General de Brigada","À vontade, General de Brigada! ⭐⭐","alto"),
    "[GEN] Generais":            ("General",           "À vontade, General! ⭐",            "alto"),
    "[CEL] Coronel":             ("Coronel",           "À vontade, Coronel! 🔴",            "alto"),
    "[T-CEL] Tenente Coronel":   ("Tenente-Coronel",   "À vontade, Tenente-Coronel! 🔴",   "medio"),
    "[MAJ] Major":               ("Major",             "À vontade, Major! 🔴",              "medio"),
    "[CAP] Capitão":             ("Capitão",           "À vontade, Capitão! 🔴",            "medio"),
    "[1-TNT] Primeiro Tenente":  ("1º Tenente",        "À vontade, 1º Tenente! 🔴",         "medio"),
    "[2-TNT] Segundo tenente":   ("2º Tenente",        "À vontade, 2º Tenente! 🔴",         "medio"),
    "[AAO] Aspirante-A-oficial": ("Aspirante",         "À vontade, Aspirante! 🔴",          "medio"),
    "[CDT] Cadete":              ("Cadete",            "À vontade, Cadete! 🔴",             "medio"),
    "[OF] Oficiais":             ("Oficial",           "À vontade, Oficial! 🔴",            "medio"),
    "[SUB-T] Sub Tenente":       ("Subtenente",        "À vontade, Subtenente! 🟢",         "medio"),
    "[GDS] Graduados":           ("Graduado",          "À vontade, Graduado! 🟢",           "medio"),
    "[1-SGT] Primeiro sargento": ("1º Sargento",       "À vontade, 1º Sargento! 🟢",        "medio"),
    "[2-SGT] Segundo Sargento":  ("2º Sargento",       "À vontade, 2º Sargento! 🟢",        "medio"),
    "[3-SGT] Terceiro sargento": ("3º Sargento",       "Sentido, 3º Sargento! 🟢",          "baixo"),
    "[PRÇ] Praças":              ("Praça",             "Sentido, Praça! 🟢",                "baixo"),
    "[CB] Cabo":                 ("Cabo",              "Sentido, Cabo! 🟢",                 "baixo"),
    "[SLD] Soldado":             ("Soldado",           "Sentido, Soldado! 🟢",              "baixo"),
    "[RCT] Recruta":             ("Recruta",           "Sentido, Recruta! 🫡",              "baixo"),
    "Supervisores":              ("Supervisor",        "Olá, Supervisor! 🛡️",               "medio"),
    "[ADM] Administrador":       ("Administrador",     "Olá, Administrador! 🛡️",            "medio"),
    "[MOD] Moderador":           ("Moderador",         "Olá, Moderador! 🛡️",               "medio"),
    "[HLP] Helper":              ("Helper",            "Olá, Helper! 🛡️",                   "baixo"),
    "[T-STF] Trial Staff":       ("Trial Staff",       "Olá, Trial Staff! 🛡️",              "baixo"),
    "[DEV] Developers":          ("Developer",         "Olá, Dev! 💻",                      "medio"),
    "[B] Builder":               ("Builder",           "Olá, Builder! 🔨",                  "baixo"),
    "Verificado":                ("Cidadão",           "Olá, Cidadão! 🟡",                  "civil"),
}

# ══════════════════════════════════════════════
# SISTEMA DE LOGS IN-MEMORY
# ══════════════════════════════════════════════
system_logs: list[dict] = []

def add_log(log_type: str, message: str, user: str = "system"):
    """Adiciona entrada no log do sistema."""
    entry = {
        "id":   str(uuid.uuid4())[:8],
        "type": log_type,
        "msg":  message,
        "user": user,
        "ts":   datetime.utcnow().isoformat() + "Z",
    }
    system_logs.insert(0, entry)
    if len(system_logs) > 500:
        system_logs[:] = system_logs[:500]
    print(f"[LOG/{log_type.upper()}] {message}")
    return entry

# ══════════════════════════════════════════════
# PERMISSÕES IN-MEMORY (+ pode ser persistido via Supabase no frontend)
# ══════════════════════════════════════════════
permissions: dict[str, bool] = {}  # { "nick_ou_discord_id": True/False }

# ══════════════════════════════════════════════
# RELATÓRIOS PENDENTES IN-MEMORY
# ══════════════════════════════════════════════
pending_reports: list[dict] = []

# ══════════════════════════════════════════════
# ANTI-FLOOD
# ══════════════════════════════════════════════
flood_control: dict = defaultdict(list)
FLOOD_LIMIT  = 4   # mensagens
FLOOD_WINDOW = 60  # segundos

def check_flood(user_id: int) -> bool:
    """Retorna True se o usuário está em flood."""
    now = time.time()
    flood_control[user_id] = [t for t in flood_control[user_id] if now - t < FLOOD_WINDOW]
    if len(flood_control[user_id]) >= FLOOD_LIMIT:
        return True
    flood_control[user_id].append(now)
    return False

# ══════════════════════════════════════════════
# GROQ IA
# ══════════════════════════════════════════════
SYSTEM_PROMPT = """Você é o assistente oficial do Exército Brasileiro (EB) no Roblox.
Responda em português, de forma CURTA e direta (máximo 3 linhas).
Nunca mencione sites externos. Seja formal e respeitoso com os postos.
Foque apenas em: patentes, regras, treinamentos e eventos do EB no Roblox."""

def ask_groq(messages: list) -> str:
    """Chama a API Groq e retorna a resposta."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":      "llama-3.3-70b-versatile",
        "messages":   messages,
        "max_tokens": 150,
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
        raise ValueError(f"Erro da API Groq: {data}")
    return data["choices"][0]["message"]["content"]

# ══════════════════════════════════════════════
# BOT DISCORD
# ══════════════════════════════════════════════
intents = discord.Intents.default()
intents.message_content = True
intents.members         = True

bot = commands.Bot(command_prefix="!", intents=intents)
chat_history: dict[str, list] = {}  # { canal_id: [mensagens] }

def get_main_role(member: discord.Member) -> str | None:
    """Retorna o cargo mais alto do membro na hierarquia."""
    role_names = {r.name for r in member.roles}
    for rank in HIERARQUIA:
        if rank in role_names:
            return rank
    return None

# ══════════════════════════════════════════════
# HELPERS — MENSAGENS DO DISCORD
# ══════════════════════════════════════════════
def format_report_message(tipo: str, campos: dict) -> str:
    """Formata a mensagem do relatório para o Discord."""
    templates = {
        "treino": (
            "📖", "RELATÓRIO DE TREINAMENTO",
            [
                ("👤 INSTRUTOR",      campos.get("instrutor",    "—")),
                ("👥 TREINADO(S)",    campos.get("treinados",    "—")),
                ("📅 DATA E HORA",    campos.get("data",         "—")),
                ("📊 STATUS",         campos.get("status",       "—")),
                ("📝 OBSERVAÇÕES",    campos.get("observacoes",  "—")),
            ]
        ),
        "recrut": (
            "🪖", "RELATÓRIO DE RECRUTAMENTO",
            [
                ("👤 RECRUTADO",   campos.get("recrutado",   "—")),
                ("👮 RECRUTADOR",  campos.get("recrutador",  "—")),
                ("📅 DATA",        campos.get("data",        "—")),
                ("📝 OBSERVAÇÕES", campos.get("observacoes", "—")),
            ]
        ),
        "adv": (
            "⚠️", "RELATÓRIO DE ADVERTÊNCIA",
            [
                ("👤 JOGADOR",  campos.get("jogador", "—")),
                ("📝 MOTIVO",   campos.get("motivo",  "—")),
                ("🔢 GRAU",     campos.get("grau",    "—")),
                ("📅 DATA",     campos.get("data",    "—")),
            ]
        ),
        "rebx": (
            "📉", "RELATÓRIO DE REBAIXAMENTO",
            [
                ("👤 USUÁRIO",        campos.get("usuario",        "—")),
                ("⬆️ CARGO ANTERIOR", campos.get("cargo_anterior", "—")),
                ("⬇️ NOVO CARGO",     campos.get("novo_cargo",     "—")),
                ("📝 MOTIVO",         campos.get("motivo",         "—")),
                ("📅 DATA",           campos.get("data",           "—")),
            ]
        ),
        "ban": (
            "🚫", "RELATÓRIO DE BANIMENTO",
            [
                ("👤 JOGADOR", campos.get("jogador", "—")),
                ("📝 MOTIVO",  campos.get("motivo",  "—")),
                ("⏳ TEMPO",   campos.get("tempo",   "—")),
                ("📅 DATA",    campos.get("data",    "—")),
            ]
        ),
        "exil": (
            "🏴‍☠️", "RELATÓRIO DE EXÍLIO",
            [
                ("👤 EXILADO",      campos.get("exilado",     "—")),
                ("📝 MOTIVO",       campos.get("motivo",      "—")),
                ("⛓️ TIPO",          campos.get("tipo",        "—")),
                ("📅 DATA",         campos.get("data",        "—")),
                ("👮 RESPONSÁVEL",  campos.get("responsavel", "—")),
            ]
        ),
        "promocao": (
            "⬆️", "SOLICITAÇÃO DE PROMOÇÃO",
            [
                ("👤 NICK",             campos.get("nick",             "—")),
                ("📊 PATENTE ATUAL",    campos.get("patente_atual",    "—")),
                ("🎯 PATENTE DESEJADA", campos.get("patente_desejada", "—")),
                ("📝 JUSTIFICATIVA",    campos.get("justificativa",    "—")),
            ]
        ),
        "aviso": (
            "📢", "AVISO OFICIAL",
            [
                ("📌 TÍTULO",   campos.get("titulo",   "—")),
                ("📄 MENSAGEM", campos.get("mensagem", "—")),
            ]
        ),
    }

    if tipo.startswith("evento_"):
        emoji = "📅"
        titulo = f"NOVO EVENTO: {campos.get('nome', '—')}"
        linhas = [
            ("🎯 TIPO",        campos.get("tipo",      "—")),
            ("📅 DATA",        campos.get("data",      "—")),
            ("📝 DESCRIÇÃO",   campos.get("descricao", "—")),
        ]
    elif tipo in templates:
        emoji, titulo, linhas = templates[tipo]
    else:
        return str(campos)

    sep   = "─" * 35
    corpo = "\n".join(f"**{k}:** {v}" for k, v in linhas)
    return f"**{emoji} {titulo} {emoji}**\n{sep}\n{corpo}\n{sep}"

def canal_final_por_tipo(tipo: str) -> int | None:
    """Retorna o ID do canal Discord final para cada tipo."""
    mapa = {
        "treino":        CANAL_TREINO,
        "recrut":        CANAL_RECRUTAMENTO,
        "adv":           CANAL_ADV,
        "rebx":          CANAL_REBAIXAMENTO,
        "ban":           CANAL_BANIMENTO,
        "exil":          CANAL_EXILIO,
        "promocao":      CANAL_ANUNCIOS,
        "aviso":         CANAL_ANUNCIOS,
        "evento_eventos":  CANAL_EVENTOS,
        "evento_anuncios": CANAL_ANUNCIOS,
        "evento_sorteios": CANAL_SORTEIOS,
    }
    return mapa.get(tipo)

# ══════════════════════════════════════════════
# AIOHTTP — CORS
# ══════════════════════════════════════════════
CORS_HEADERS = {
    "Access-Control-Allow-Origin":  "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Content-Type": "application/json",
}

def json_resp(data: dict, status: int = 200) -> web.Response:
    return web.Response(
        text=json.dumps(data, ensure_ascii=False),
        status=status,
        headers=CORS_HEADERS,
    )

# ══════════════════════════════════════════════
# HANDLERS — API
# ══════════════════════════════════════════════

async def handle_options(request):
    """Handle CORS preflight."""
    return web.Response(status=204, headers=CORS_HEADERS)


async def handle_ping(request):
    """Health check."""
    return json_resp({"status": "online", "ts": datetime.utcnow().isoformat()})


async def handle_cargos(request):
    """
    GET /cargos?user_id=DISCORD_ID
    Retorna cargos e patente principal do membro.
    """
    user_id = request.rel_url.query.get("user_id")
    if not user_id:
        return json_resp({"error": "user_id obrigatório"}, 400)

    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return json_resp({"error": "Servidor não encontrado"}, 404)

    try:
        member = await guild.fetch_member(int(user_id))
    except discord.NotFound:
        return json_resp({"error": "Membro não encontrado no servidor"}, 404)
    except Exception as e:
        return json_resp({"error": str(e)}, 500)

    cargos = [
        {"id": str(r.id), "nome": r.name}
        for r in member.roles
        if r.name != "@everyone"
    ]

    cargo_nome = get_main_role(member)
    patente    = "Cidadão"
    if cargo_nome and cargo_nome in SAUDACOES:
        patente = SAUDACOES[cargo_nome][0]

    add_log("api", f"Cargos consultados para user_id={user_id}")

    return json_resp({
        "user_id":       user_id,
        "cargos":        cargos,
        "cargo_nome":    cargo_nome,
        "patente":       patente,
    })


async def handle_pendente(request):
    """
    POST /pendente
    Recebe relatório pendente do frontend e salva / envia ao canal de aprovação.
    """
    try:
        data = await request.json()
    except Exception:
        return json_resp({"error": "JSON inválido"}, 400)

    # Validação básica
    required = ["id", "tipo", "campos", "autor"]
    for field in required:
        if field not in data:
            return json_resp({"error": f"Campo '{field}' obrigatório"}, 400)

    tipo    = data["tipo"]
    campos  = data.get("campos", {})
    autor   = data.get("autor", "Desconhecido")
    rel_id  = data.get("id", str(uuid.uuid4())[:8])

    report = {
        "id":     rel_id,
        "tipo":   tipo,
        "campos": campos,
        "imagem": data.get("imagem"),
        "autor":  autor,
        "status": "pendente",
        "ts":     datetime.utcnow().isoformat(),
    }
    pending_reports.append(report)
    add_log("relat", f"Relatório pendente recebido: {tipo} | autor: {autor} | id: {rel_id}")

    # Envia ao canal de aprovação no Discord (se configurado)
    if CANAL_APROVACAO:
        canal = bot.get_channel(CANAL_APROVACAO)
        if canal:
            label_map = {
                "treino": "Treinamento", "recrut": "Recrutamento",
                "adv": "Advertência",   "rebx": "Rebaixamento",
                "ban": "Banimento",     "exil": "Exílio",
                "promocao": "Promoção",
            }
            label  = label_map.get(tipo, tipo.capitalize())
            corpo  = "\n".join(f"**{k}:** {v}" for k, v in campos.items())
            msg_txt = (
                f"🕐 **RELATÓRIO AGUARDANDO APROVAÇÃO**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**Tipo:** {label}\n"
                f"**Autor:** {autor}\n"
                f"**ID:** `{rel_id}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{corpo}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Use **/aprovar {rel_id}** ou **/reprovar {rel_id} <motivo>** para gerenciar."
            )
            try:
                await canal.send(msg_txt)
            except Exception as e:
                add_log("erro", f"Falha ao enviar ao canal de aprovação: {e}")

    return json_resp({"ok": True, "id": rel_id})


async def handle_relatorio(request):
    """
    POST /relatorio
    Envia relatório APROVADO ao canal final do Discord.
    """
    try:
        data = await request.json()
    except Exception:
        return json_resp({"error": "JSON inválido"}, 400)

    tipo    = data.get("tipo")
    campos  = data.get("campos", {})
    imagem  = data.get("imagem")

    if not tipo:
        return json_resp({"error": "Campo 'tipo' obrigatório"}, 400)

    canal_id = canal_final_por_tipo(tipo)
    if not canal_id:
        return json_resp({"error": f"Tipo '{tipo}' inválido ou sem canal configurado"}, 400)

    canal = bot.get_channel(canal_id)
    if not canal:
        return json_resp({"error": "Canal do Discord não encontrado"}, 404)

    msg_text = format_report_message(tipo, campos)

    try:
        if imagem:
            # Decodifica base64
            img_data = base64.b64decode(imagem.split(",")[-1])
            file = discord.File(
                fp=__import__("io").BytesIO(img_data),
                filename="prova.png"
            )
            await canal.send(msg_text, file=file)
        else:
            await canal.send(msg_text)
    except Exception as e:
        add_log("erro", f"Falha ao enviar relatório ao Discord: {e}")
        return json_resp({"error": str(e)}, 500)

    add_log("aprov", f"Relatório {tipo} enviado ao canal #{canal.name}")
    return json_resp({"ok": True})


async def handle_get_logs(request):
    """
    GET /logs?limit=50
    Retorna logs do sistema (para uso interno/staff).
    """
    limit  = int(request.rel_url.query.get("limit", 100))
    offset = int(request.rel_url.query.get("offset", 0))
    return json_resp({
        "logs":  system_logs[offset:offset + limit],
        "total": len(system_logs),
    })


async def handle_get_permissoes(request):
    """
    GET /permissoes
    Retorna mapa de permissões atual.
    """
    return json_resp({"permissoes": permissions})


async def handle_post_permissoes(request):
    """
    POST /permissoes
    Body: { "nick": "SoldadoX", "pode": true }
    Atualiza permissão de um membro.
    """
    try:
        data = await request.json()
    except Exception:
        return json_resp({"error": "JSON inválido"}, 400)

    nick = data.get("nick")
    pode = data.get("pode")

    if not nick or pode is None:
        return json_resp({"error": "Campos 'nick' e 'pode' obrigatórios"}, 400)

    permissions[nick] = bool(pode)
    acao = "concedida" if pode else "revogada"
    add_log("perm", f"Permissão de relatórios {acao} para {nick}")

    return json_resp({"ok": True, "nick": nick, "pode": bool(pode)})


# ══════════════════════════════════════════════
# SETUP DO SERVIDOR WEB
# ══════════════════════════════════════════════
async def start_web_server():
    app = web.Application()

    # CORS preflight para todas as rotas
    app.router.add_route("OPTIONS", "/{path_info:.*}", handle_options)

    # Endpoints
    app.router.add_get( "/ping",        handle_ping)
    app.router.add_get( "/cargos",      handle_cargos)
    app.router.add_post("/pendente",    handle_pendente)
    app.router.add_post("/relatorio",   handle_relatorio)
    app.router.add_get( "/logs",        handle_get_logs)
    app.router.add_get( "/permissoes",  handle_get_permissoes)
    app.router.add_post("/permissoes",  handle_post_permissoes)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"✅ API rodando em 0.0.0.0:{PORT}")
    add_log("system", f"API iniciada na porta {PORT}")


# ══════════════════════════════════════════════
# COMANDOS SLASH / PREFIX DO BOT
# ══════════════════════════════════════════════
@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="pelo Exército Brasileiro 🪖"
        )
    )
    await start_web_server()
    add_log("system", f"Bot iniciado: {bot.user}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

    # Só responde a mensagens com ! que não sejam comandos conhecidos
    if not message.content.startswith("!"):
        return

    pergunta = message.content[1:].strip()
    if not pergunta:
        return

    # Ignora comandos registrados
    known_cmds = {"ping", "patente", "limpar", "help", "aprovar", "reprovar", "perms"}
    if pergunta.split()[0].lower() in known_cmds:
        return

    # Anti-flood
    if check_flood(message.author.id):
        await message.reply("⛔ Devagar, soldado! Aguarde um momento antes de perguntar novamente.")
        add_log("block", f"Flood bloqueado: {message.author.display_name}")
        return

    # Identifica cargo
    cargo_nome = get_main_role(message.author)
    if cargo_nome and cargo_nome in SAUDACOES:
        patente, saudacao, nivel = SAUDACOES[cargo_nome]
    else:
        patente, saudacao, nivel = "Civil", "Olá, Civil! 🔒", "civil"

    canal_id = str(message.channel.id)
    if canal_id not in chat_history:
        chat_history[canal_id] = []

    chat_history[canal_id].append({
        "role": "user",
        "content": f"[{patente}] {message.author.display_name}: {pergunta}"
    })

    # Mantém apenas as últimas 6 mensagens para economizar tokens
    if len(chat_history[canal_id]) > 6:
        chat_history[canal_id] = chat_history[canal_id][-6:]

    async with message.channel.typing():
        try:
            msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history[canal_id]
            resposta = ask_groq(msgs)
            chat_history[canal_id].append({"role": "assistant", "content": resposta})
            await message.reply(f"{saudacao}\n{resposta}")
            add_log("ia", f"IA respondeu para {message.author.display_name}")
        except Exception as e:
            await message.reply(f"⚠️ Erro ao processar: {e}")
            add_log("erro", f"Erro IA: {e}")


@bot.command(name="ping")
async def cmd_ping(ctx):
    """!ping — verifica se o bot está online."""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🟢 Online! Latência: **{latency}ms** | EB DO RAFA 🪖")


@bot.command(name="patente")
async def cmd_patente(ctx):
    """!patente — exibe sua patente atual."""
    cargo_nome = get_main_role(ctx.author)
    if cargo_nome and cargo_nome in SAUDACOES:
        patente, saudacao, _ = SAUDACOES[cargo_nome]
        await ctx.send(f"{saudacao}\nSua patente é **{patente}**.")
    else:
        await ctx.send("🔒 Você não está verificado! Vá ao canal de verificação.")


@bot.command(name="aprovar")
@commands.has_permissions(manage_messages=True)
async def cmd_aprovar(ctx, rel_id: str):
    """
    !aprovar <id> — aprova relatório pendente e envia ao canal final.
    Apenas staff com 'manage_messages'.
    """
    report = next((r for r in pending_reports if r["id"] == rel_id and r["status"] == "pendente"), None)
    if not report:
        await ctx.send(f"⚠️ Relatório `{rel_id}` não encontrado ou já processado.")
        return

    report["status"] = "aprovado"
    tipo   = report["tipo"]
    campos = report["campos"]
    imagem = report.get("imagem")

    canal_id = canal_final_por_tipo(tipo)
    if canal_id:
        canal = bot.get_channel(canal_id)
        if canal:
            msg_text = format_report_message(tipo, campos)
            if imagem:
                img_data = base64.b64decode(imagem.split(",")[-1])
                file = discord.File(fp=__import__("io").BytesIO(img_data), filename="prova.png")
                await canal.send(msg_text, file=file)
            else:
                await canal.send(msg_text)

    add_log("aprov", f"Relatório {rel_id} ({tipo}) aprovado por {ctx.author.display_name}")
    await ctx.send(f"✅ Relatório `{rel_id}` aprovado e enviado ao canal!")


@bot.command(name="reprovar")
@commands.has_permissions(manage_messages=True)
async def cmd_reprovar(ctx, rel_id: str, *, motivo: str):
    """
    !reprovar <id> <motivo> — reprova relatório pendente.
    Apenas staff com 'manage_messages'.
    Exemplo: !reprovar abc123 Falta de evidências
    """
    report = next((r for r in pending_reports if r["id"] == rel_id and r["status"] == "pendente"), None)
    if not report:
        await ctx.send(f"⚠️ Relatório `{rel_id}` não encontrado ou já processado.")
        return

    report["status"]     = "reprovado"
    report["motivo_rep"] = motivo

    add_log("reprov", f"Relatório {rel_id} ({report['tipo']}) reprovado por {ctx.author.display_name} — Motivo: {motivo}")
    await ctx.send(
        f"❌ Relatório `{rel_id}` reprovado.\n"
        f"**Autor:** {report.get('autor', '—')}\n"
        f"**Motivo:** {motivo}"
    )


@bot.command(name="perms")
@commands.has_permissions(manage_messages=True)
async def cmd_perms(ctx, nick: str, acao: str):
    """
    !perms <nick> <dar|revogar> — gerencia permissão de relatórios.
    Exemplo: !perms SoldadoX dar
    """
    acao = acao.lower()
    if acao not in ("dar", "revogar"):
        await ctx.send("⚠️ Use: `!perms <nick> dar` ou `!perms <nick> revogar`")
        return

    permissions[nick] = (acao == "dar")
    msg = f"✅ Permissão **concedida** para `{nick}`." if acao == "dar" else f"🚫 Permissão **revogada** de `{nick}`."
    add_log("perm", f"Permissão {acao}da para {nick} por {ctx.author.display_name}")
    await ctx.send(msg)


@bot.command(name="limpar")
@commands.has_permissions(manage_messages=True)
async def cmd_limpar(ctx):
    """!limpar — limpa o histórico de IA do canal."""
    canal_id = str(ctx.channel.id)
    if canal_id in chat_history:
        chat_history[canal_id] = []
    await ctx.send("🗑️ Histórico de IA limpo para este canal.")


# ══════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("Variável DISCORD_TOKEN não definida!")
    bot.run(DISCORD_TOKEN)
