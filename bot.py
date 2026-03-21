"""
╔══════════════════════════════════════════════════════════╗
║          EB DO RAFA — BOT + API v2.1                     ║
║  discord.py==2.3.2  |  aiohttp==3.9.5  |  Python 3.10+  ║
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
  DISCORD_TOKEN   — token do bot
  GUILD_ID        — ID do servidor Discord
  GROQ_API_KEY    — chave da API Groq (IA)
  PORT            — porta da API (padrão: 8080)
  CANAL_APROVACAO — ID do canal de fila de aprovação
"""

# ── stdlib ──────────────────────────────────────────────
import asyncio
import base64
import io
import json
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Optional, List, Dict

# ── third-party ─────────────────────────────────────────
import discord
from discord.ext import commands
import requests
from aiohttp import web

# ════════════════════════════════════════════════════════
# NOTAS DE COMPATIBILIDADE
# ════════════════════════════════════════════════════════
# discord.py 2.3.2
#   - Sintaxe "X | Y" para type hints de RETORNO não funciona
#     no Python < 3.10 em runtime; usamos Optional[X] para segurança.
#   - commands.Bot, discord.Intents, discord.Activity: sem mudanças.
#   - commands.has_permissions: OK.
#   - guild.fetch_member: coroutine, await obrigatório.
#   - discord.File(fp=..., filename=...): OK.
#
# aiohttp 3.9.5
#   - web.Application(), web.AppRunner(), web.TCPSite(): OK.
#   - request.json(): coroutine → await obrigatório.
#   - web.Response(text=..., headers=...): OK.
#   - Nenhum breaking change relevante nesta versão.
#
# audioop-lts 0.2.1
#   - Substituição do audioop removido no Python 3.13.
#   - Não requer import direto; instalado apenas para
#     compatibilidade de voz do discord.py, se necessário.
# ════════════════════════════════════════════════════════


# ══════════════════════════════════════════════
# CONFIGURAÇÃO
# ══════════════════════════════════════════════
DISCORD_TOKEN   = os.environ.get("DISCORD_TOKEN")
GROQ_API_KEY    = os.environ.get("GROQ_API_KEY")
GUILD_ID        = int(os.environ.get("GUILD_ID", "0"))
PORT            = int(os.environ.get("PORT", "8080"))
CANAL_APROVACAO = int(os.environ.get("CANAL_APROVACAO", "0"))

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

# Tuple: (patente_display, saudacao, nivel)
SAUDACOES = {
    "Fundador":                   ("Fundador",            "Olá, Fundador! 👑",                    "alto"),
    "[CD] Con-Dono":              ("Con-Dono",             "Olá, Con-Dono! 👑",                    "alto"),
    "[DG] Diretor Geral":         ("Diretor Geral",        "À vontade, Diretor Geral! 🏅",          "alto"),
    "[VDA] Vice-diretor-geral":   ("Vice-Diretor",         "À vontade, Vice-Diretor! 🏅",           "alto"),
    "[M] Maneger":                ("Manager",              "À vontade, Manager! 🏅",                "alto"),
    "[MAL] Marechal":             ("Marechal",             "Sentido, Marechal! 🎖️",                 "alto"),
    "[GEN-E] General de Exército":("General de Exército",  "À vontade, General de Exército! ⭐⭐⭐⭐", "alto"),
    "[GEN-D] General de Divisão": ("General de Divisão",   "À vontade, General de Divisão! ⭐⭐⭐",  "alto"),
    "[GEN-B] General de brigada": ("General de Brigada",   "À vontade, General de Brigada! ⭐⭐",   "alto"),
    "[GEN] Generais":             ("General",              "À vontade, General! ⭐",                "alto"),
    "[CEL] Coronel":              ("Coronel",              "À vontade, Coronel! 🔴",                "alto"),
    "[T-CEL] Tenente Coronel":    ("Tenente-Coronel",      "À vontade, Tenente-Coronel! 🔴",        "medio"),
    "[MAJ] Major":                ("Major",                "À vontade, Major! 🔴",                  "medio"),
    "[CAP] Capitão":              ("Capitão",              "À vontade, Capitão! 🔴",                "medio"),
    "[1-TNT] Primeiro Tenente":   ("1º Tenente",           "À vontade, 1º Tenente! 🔴",             "medio"),
    "[2-TNT] Segundo tenente":    ("2º Tenente",           "À vontade, 2º Tenente! 🔴",             "medio"),
    "[AAO] Aspirante-A-oficial":  ("Aspirante",            "À vontade, Aspirante! 🔴",              "medio"),
    "[CDT] Cadete":               ("Cadete",               "À vontade, Cadete! 🔴",                 "medio"),
    "[OF] Oficiais":              ("Oficial",              "À vontade, Oficial! 🔴",                "medio"),
    "[SUB-T] Sub Tenente":        ("Subtenente",           "À vontade, Subtenente! 🟢",             "medio"),
    "[GDS] Graduados":            ("Graduado",             "À vontade, Graduado! 🟢",               "medio"),
    "[1-SGT] Primeiro sargento":  ("1º Sargento",          "À vontade, 1º Sargento! 🟢",            "medio"),
    "[2-SGT] Segundo Sargento":   ("2º Sargento",          "À vontade, 2º Sargento! 🟢",            "medio"),
    "[3-SGT] Terceiro sargento":  ("3º Sargento",          "Sentido, 3º Sargento! 🟢",              "baixo"),
    "[PRÇ] Praças":               ("Praça",                "Sentido, Praça! 🟢",                    "baixo"),
    "[CB] Cabo":                  ("Cabo",                 "Sentido, Cabo! 🟢",                     "baixo"),
    "[SLD] Soldado":              ("Soldado",              "Sentido, Soldado! 🟢",                  "baixo"),
    "[RCT] Recruta":              ("Recruta",              "Sentido, Recruta! 🫡",                  "baixo"),
    "Supervisores":               ("Supervisor",           "Olá, Supervisor! 🛡️",                   "medio"),
    "[ADM] Administrador":        ("Administrador",        "Olá, Administrador! 🛡️",                "medio"),
    "[MOD] Moderador":            ("Moderador",            "Olá, Moderador! 🛡️",                    "medio"),
    "[HLP] Helper":               ("Helper",               "Olá, Helper! 🛡️",                       "baixo"),
    "[T-STF] Trial Staff":        ("Trial Staff",          "Olá, Trial Staff! 🛡️",                  "baixo"),
    "[DEV] Developers":           ("Developer",            "Olá, Dev! 💻",                          "medio"),
    "[B] Builder":                ("Builder",              "Olá, Builder! 🔨",                      "baixo"),
    "Verificado":                 ("Cidadão",              "Olá, Cidadão! 🟡",                      "civil"),
}


# ══════════════════════════════════════════════
# ESTADO GLOBAL (in-memory)
# ══════════════════════════════════════════════
system_logs: List[Dict]    = []   # logs do sistema
permissions: Dict[str, bool] = {}  # nick → pode_enviar
pending_reports: List[Dict] = []  # relatórios pendentes
chat_history: Dict[str, List[Dict]] = {}  # canal_id → mensagens IA


# ══════════════════════════════════════════════
# HELPERS — LOG
# ══════════════════════════════════════════════
def add_log(log_type: str, message: str, user: str = "system") -> Dict:
    """Insere entrada no log do sistema."""
    entry: Dict = {
        "id":   str(uuid.uuid4())[:8],
        "type": log_type,
        "msg":  message,
        "user": user,
        "ts":   datetime.utcnow().isoformat() + "Z",
    }
    system_logs.insert(0, entry)
    if len(system_logs) > 500:
        del system_logs[500:]
    print("[LOG/{}] {}".format(log_type.upper(), message))
    return entry


# ══════════════════════════════════════════════
# HELPERS — HIERARQUIA
# ══════════════════════════════════════════════
def get_main_role(member: discord.Member) -> Optional[str]:
    """Retorna o cargo mais alto do membro na hierarquia definida."""
    role_names = {r.name for r in member.roles}
    for rank in HIERARQUIA:
        if rank in role_names:
            return rank
    return None


# ══════════════════════════════════════════════
# ANTI-FLOOD
# ══════════════════════════════════════════════
flood_control: defaultdict = defaultdict(list)
FLOOD_LIMIT  = 4   # mensagens por janela
FLOOD_WINDOW = 60  # segundos


def check_flood(user_id: int) -> bool:
    """Retorna True se o usuário deve ser bloqueado por flood."""
    now = time.time()
    flood_control[user_id] = [
        t for t in flood_control[user_id] if now - t < FLOOD_WINDOW
    ]
    if len(flood_control[user_id]) >= FLOOD_LIMIT:
        return True
    flood_control[user_id].append(now)
    return False


# ══════════════════════════════════════════════
# GROQ IA
# ══════════════════════════════════════════════
SYSTEM_PROMPT = (
    "Você é o assistente oficial do Exército Brasileiro (EB) no Roblox. "
    "Responda em português, de forma CURTA e direta (máximo 3 linhas). "
    "Nunca mencione sites externos. Seja formal e respeitoso com os postos. "
    "Foque apenas em: patentes, regras, treinamentos e eventos do EB no Roblox."
)


def _ask_groq_sync(messages: List[Dict]) -> str:
    """Chamada síncrona à API Groq. Executada em thread separada via run_in_executor."""
    headers = {
        "Authorization": "Bearer {}".format(GROQ_API_KEY),
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       "llama-3.3-70b-versatile",
        "messages":    messages,
        "max_tokens":  150,
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
        raise ValueError("Groq API error: {}".format(data))
    return data["choices"][0]["message"]["content"]


async def ask_groq(messages: List[Dict]) -> str:
    """
    Wrapper assíncrono: roda _ask_groq_sync em executor para não
    bloquear o event loop do discord.py e do aiohttp.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _ask_groq_sync, messages)


# ══════════════════════════════════════════════
# HELPERS — FORMATAÇÃO DE RELATÓRIO
# ══════════════════════════════════════════════
def format_report_message(tipo: str, campos: Dict) -> str:
    """Formata a mensagem do relatório para envio ao Discord."""
    SEP = "─" * 34

    templates: Dict = {
        "treino": (
            "📖", "RELATÓRIO DE TREINAMENTO",
            [
                ("👤 INSTRUTOR",   campos.get("instrutor",   "—")),
                ("👥 TREINADO(S)", campos.get("treinados",   "—")),
                ("📅 DATA E HORA", campos.get("data",        "—")),
                ("📊 STATUS",      campos.get("status",      "—")),
                ("📝 OBS",         campos.get("observacoes", "—")),
            ],
        ),
        "recrut": (
            "🪖", "RELATÓRIO DE RECRUTAMENTO",
            [
                ("👤 RECRUTADO",   campos.get("recrutado",   "—")),
                ("👮 RECRUTADOR",  campos.get("recrutador",  "—")),
                ("📅 DATA",        campos.get("data",        "—")),
                ("📝 OBS",         campos.get("observacoes", "—")),
            ],
        ),
        "adv": (
            "⚠️", "RELATÓRIO DE ADVERTÊNCIA",
            [
                ("👤 JOGADOR", campos.get("jogador", "—")),
                ("📝 MOTIVO",  campos.get("motivo",  "—")),
                ("🔢 GRAU",    campos.get("grau",    "—")),
                ("📅 DATA",    campos.get("data",    "—")),
            ],
        ),
        "rebx": (
            "📉", "RELATÓRIO DE REBAIXAMENTO",
            [
                ("👤 USUÁRIO",        campos.get("usuario",        "—")),
                ("⬆️ CARGO ANTERIOR", campos.get("cargo_anterior", "—")),
                ("⬇️ NOVO CARGO",     campos.get("novo_cargo",     "—")),
                ("📝 MOTIVO",         campos.get("motivo",         "—")),
                ("📅 DATA",           campos.get("data",           "—")),
            ],
        ),
        "ban": (
            "🚫", "RELATÓRIO DE BANIMENTO",
            [
                ("👤 JOGADOR", campos.get("jogador", "—")),
                ("📝 MOTIVO",  campos.get("motivo",  "—")),
                ("⏳ DURAÇÃO", campos.get("tempo",   "—")),
                ("📅 DATA",    campos.get("data",    "—")),
            ],
        ),
        "exil": (
            "🏴‍☠️", "RELATÓRIO DE EXÍLIO",
            [
                ("👤 EXILADO",     campos.get("exilado",     "—")),
                ("📝 MOTIVO",      campos.get("motivo",      "—")),
                ("⛓️ TIPO",         campos.get("tipo",        "—")),
                ("📅 DATA",        campos.get("data",        "—")),
                ("👮 RESPONSÁVEL", campos.get("responsavel", "—")),
            ],
        ),
        "promocao": (
            "⬆️", "SOLICITAÇÃO DE PROMOÇÃO",
            [
                ("👤 NICK",             campos.get("nick",             "—")),
                ("📊 PATENTE ATUAL",    campos.get("patente_atual",    "—")),
                ("🎯 PATENTE DESEJADA", campos.get("patente_desejada", "—")),
                ("📝 JUSTIFICATIVA",    campos.get("justificativa",    "—")),
            ],
        ),
        "aviso": (
            "📢", "AVISO OFICIAL",
            [
                ("📌 TÍTULO",   campos.get("titulo",   "—")),
                ("📄 MENSAGEM", campos.get("mensagem", "—")),
            ],
        ),
    }

    if tipo.startswith("evento_"):
        emoji  = "📅"
        titulo = "NOVO EVENTO: {}".format(campos.get("nome", "—"))
        linhas = [
            ("🎯 TIPO",      campos.get("tipo",      "—")),
            ("📅 DATA",      campos.get("data",      "—")),
            ("📝 DESCRIÇÃO", campos.get("descricao", "—")),
        ]
    elif tipo in templates:
        emoji, titulo, linhas = templates[tipo]
    else:
        emoji  = "📋"
        titulo = "RELATÓRIO — {}".format(tipo.upper())
        linhas = list(campos.items())

    corpo = "\n".join("**{}:** {}".format(k, v) for k, v in linhas)
    return "**{} {} {}**\n{}\n{}\n{}".format(emoji, titulo, emoji, SEP, corpo, SEP)


def canal_final_por_tipo(tipo: str) -> Optional[int]:
    """Mapeia tipo de relatório para o ID do canal Discord de destino."""
    mapa: Dict[str, int] = {
        "treino":          CANAL_TREINO,
        "recrut":          CANAL_RECRUTAMENTO,
        "adv":             CANAL_ADV,
        "rebx":            CANAL_REBAIXAMENTO,
        "ban":             CANAL_BANIMENTO,
        "exil":            CANAL_EXILIO,
        "promocao":        CANAL_ANUNCIOS,
        "aviso":           CANAL_ANUNCIOS,
        "evento_eventos":  CANAL_EVENTOS,
        "evento_anuncios": CANAL_ANUNCIOS,
        "evento_sorteios": CANAL_SORTEIOS,
    }
    return mapa.get(tipo)


# ══════════════════════════════════════════════
# AIOHTTP — CORS E HELPER DE RESPOSTA
# ══════════════════════════════════════════════
CORS_HEADERS = {
    "Access-Control-Allow-Origin":  "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}


def json_resp(data: Dict, status: int = 200) -> web.Response:
    """Cria Response JSON com headers CORS."""
    headers = {**CORS_HEADERS, "Content-Type": "application/json; charset=utf-8"}
    return web.Response(
        text=json.dumps(data, ensure_ascii=False),
        status=status,
        headers=headers,
    )


# ══════════════════════════════════════════════
# HANDLERS — API REST
# ══════════════════════════════════════════════

async def handle_options(request: web.Request) -> web.Response:
    """CORS preflight — responde a qualquer OPTIONS."""
    return web.Response(status=204, headers=CORS_HEADERS)


async def handle_ping(request: web.Request) -> web.Response:
    """GET /ping — health check."""
    return json_resp({
        "status": "online",
        "bot":    str(bot.user) if bot.user else "connecting",
        "ts":     datetime.utcnow().isoformat() + "Z",
    })


async def handle_cargos(request: web.Request) -> web.Response:
    """
    GET /cargos?user_id=DISCORD_ID
    Retorna lista de cargos e patente do membro.
    """
    user_id = request.rel_url.query.get("user_id", "").strip()
    if not user_id:
        return json_resp({"error": "Parâmetro 'user_id' obrigatório"}, 400)

    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return json_resp({"error": "Servidor Discord não encontrado"}, 404)

    try:
        member = await guild.fetch_member(int(user_id))
    except discord.NotFound:
        return json_resp({"error": "Membro não encontrado no servidor"}, 404)
    except discord.HTTPException as exc:
        add_log("erro", "fetch_member falhou: {}".format(exc))
        return json_resp({"error": "Erro ao buscar membro"}, 500)
    except ValueError:
        return json_resp({"error": "user_id deve ser um inteiro"}, 400)

    cargos = [
        {"id": str(r.id), "nome": r.name}
        for r in member.roles
        if r.name != "@everyone"
    ]

    cargo_nome = get_main_role(member)
    patente    = "Cidadão"
    if cargo_nome and cargo_nome in SAUDACOES:
        patente = SAUDACOES[cargo_nome][0]

    add_log("api", "Cargos consultados — user_id={}".format(user_id))
    return json_resp({
        "user_id":    user_id,
        "cargos":     cargos,
        "cargo_nome": cargo_nome,
        "patente":    patente,
    })


async def handle_pendente(request: web.Request) -> web.Response:
    """
    POST /pendente
    Recebe relatório pendente, armazena e notifica canal de aprovação.
    """
    try:
        data = await request.json()
    except Exception:
        return json_resp({"error": "Body JSON inválido"}, 400)

    for field in ("id", "tipo", "campos", "autor"):
        if field not in data:
            return json_resp({"error": "Campo '{}' obrigatório".format(field)}, 400)

    tipo   = str(data["tipo"])
    campos = data.get("campos", {})
    autor  = str(data.get("autor", "Desconhecido"))
    rel_id = str(data.get("id", str(uuid.uuid4())[:8]))
    imagem = data.get("imagem")  # base64 string ou None

    report: Dict = {
        "id":     rel_id,
        "tipo":   tipo,
        "campos": campos,
        "imagem": imagem,
        "autor":  autor,
        "status": "pendente",
        "ts":     datetime.utcnow().isoformat() + "Z",
    }
    pending_reports.append(report)
    add_log("relat", "Pendente recebido — tipo={} autor={} id={}".format(tipo, autor, rel_id))

    # Notifica canal de aprovação (se configurado)
    if CANAL_APROVACAO:
        canal = bot.get_channel(CANAL_APROVACAO)
        if canal:
            label_map: Dict[str, str] = {
                "treino": "Treinamento", "recrut": "Recrutamento",
                "adv":    "Advertência", "rebx":   "Rebaixamento",
                "ban":    "Banimento",   "exil":   "Exílio",
                "promocao": "Promoção",
            }
            label     = label_map.get(tipo, tipo.capitalize())
            campos_txt = "\n".join(
                "**{}:** {}".format(k.replace("_", " ").title(), v)
                for k, v in campos.items()
            )
            msg_txt = (
                "🕐 **RELATÓRIO AGUARDANDO APROVAÇÃO**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "**Tipo:** {}\n"
                "**Autor:** {}\n"
                "**ID:** `{}`\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "{}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Use `!aprovar {}` ou `!reprovar {} <motivo>`"
            ).format(label, autor, rel_id, campos_txt, rel_id, rel_id)

            try:
                await canal.send(msg_txt)
            except discord.HTTPException as exc:
                add_log("erro", "Falha ao notificar canal de aprovação: {}".format(exc))

    return json_resp({"ok": True, "id": rel_id})


async def handle_relatorio(request: web.Request) -> web.Response:
    """
    POST /relatorio
    Envia relatório APROVADO ao canal final do Discord.
    """
    try:
        data = await request.json()
    except Exception:
        return json_resp({"error": "Body JSON inválido"}, 400)

    tipo   = str(data.get("tipo", "")).strip()
    campos = data.get("campos", {})
    imagem = data.get("imagem")

    if not tipo:
        return json_resp({"error": "Campo 'tipo' obrigatório"}, 400)

    canal_id = canal_final_por_tipo(tipo)
    if not canal_id:
        return json_resp(
            {"error": "Tipo '{}' inválido ou sem canal configurado".format(tipo)},
            400,
        )

    canal = bot.get_channel(canal_id)
    if not canal:
        return json_resp(
            {"error": "Canal Discord não encontrado (id={})".format(canal_id)},
            404,
        )

    msg_text = format_report_message(tipo, campos)

    try:
        if imagem:
            raw          = imagem.split(",")[-1]
            img_bytes    = base64.b64decode(raw)
            discord_file = discord.File(fp=io.BytesIO(img_bytes), filename="prova.png")
            await canal.send(msg_text, file=discord_file)
        else:
            await canal.send(msg_text)
    except discord.HTTPException as exc:
        add_log("erro", "Falha ao enviar relatório: {}".format(exc))
        return json_resp({"error": str(exc)}, 500)

    add_log("aprov", "Relatório {} enviado ao canal #{}".format(tipo, canal.name))
    return json_resp({"ok": True})


async def handle_get_logs(request: web.Request) -> web.Response:
    """
    GET /logs?limit=100&offset=0
    Retorna logs do sistema.
    """
    try:
        limit  = int(request.rel_url.query.get("limit",  100))
        offset = int(request.rel_url.query.get("offset", 0))
    except ValueError:
        return json_resp({"error": "limit e offset devem ser inteiros"}, 400)

    return json_resp({
        "logs":  system_logs[offset:offset + limit],
        "total": len(system_logs),
    })


async def handle_get_permissoes(request: web.Request) -> web.Response:
    """GET /permissoes — retorna mapa de permissões."""
    return json_resp({"permissoes": permissions})


async def handle_post_permissoes(request: web.Request) -> web.Response:
    """
    POST /permissoes
    Body: { "nick": "SoldadoX", "pode": true }
    """
    try:
        data = await request.json()
    except Exception:
        return json_resp({"error": "Body JSON inválido"}, 400)

    nick = data.get("nick", "").strip()
    pode = data.get("pode")

    if not nick:
        return json_resp({"error": "Campo 'nick' obrigatório"}, 400)
    if pode is None:
        return json_resp({"error": "Campo 'pode' obrigatório (true/false)"}, 400)

    pode_bool = bool(pode)
    permissions[nick] = pode_bool
    acao = "concedida" if pode_bool else "revogada"
    add_log("perm", "Permissão {} para {}".format(acao, nick))

    return json_resp({"ok": True, "nick": nick, "pode": pode_bool})


# ══════════════════════════════════════════════
# SETUP DO SERVIDOR WEB
# ══════════════════════════════════════════════
async def start_web_server() -> None:
    """Inicializa o servidor aiohttp de forma assíncrona."""
    app = web.Application()

    # CORS preflight — registrar antes das outras rotas
    app.router.add_route("OPTIONS", "/{path_info:.*}", handle_options)

    # Rotas da API
    app.router.add_get( "/ping",       handle_ping)
    app.router.add_get( "/cargos",     handle_cargos)
    app.router.add_post("/pendente",   handle_pendente)
    app.router.add_post("/relatorio",  handle_relatorio)
    app.router.add_get( "/logs",       handle_get_logs)
    app.router.add_get( "/permissoes", handle_get_permissoes)
    app.router.add_post("/permissoes", handle_post_permissoes)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()

    add_log("system", "API iniciada na porta {}".format(PORT))
    print("✅ API rodando em 0.0.0.0:{}".format(PORT))


# ══════════════════════════════════════════════
# BOT DISCORD
# ══════════════════════════════════════════════
intents                 = discord.Intents.default()
intents.message_content = True
intents.members         = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Comandos nativos — IA não deve interceptar
KNOWN_COMMANDS = frozenset({
    "ping", "patente", "limpar", "help",
    "aprovar", "reprovar", "perms",
})


@bot.event
async def on_ready() -> None:
    print("🤖 Bot conectado como {} (ID: {})".format(bot.user, bot.user.id))
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="pelo Exército Brasileiro 🪖",
        )
    )
    await start_web_server()
    add_log("system", "Bot pronto: {}".format(str(bot.user)))


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author == bot.user:
        return

    # Processa comandos prefix (ex: !ping, !aprovar)
    await bot.process_commands(message)

    # Responde somente a mensagens com "!"
    if not message.content.startswith("!"):
        return

    pergunta = message.content[1:].strip()
    if not pergunta:
        return

    # Se for comando registrado, ignora (já foi processado acima)
    if pergunta.split()[0].lower() in KNOWN_COMMANDS:
        return

    # Anti-flood
    if check_flood(message.author.id):
        await message.reply("⛔ Devagar, soldado! Aguarde antes de perguntar novamente.")
        add_log("block", "Flood bloqueado: {}".format(message.author.display_name))
        return

    # Identifica patente/saudação
    cargo_nome = get_main_role(message.author)
    if cargo_nome and cargo_nome in SAUDACOES:
        patente, saudacao, _nivel = SAUDACOES[cargo_nome]
    else:
        patente, saudacao = "Civil", "Olá, Civil! 🔒"

    # Histórico de contexto por canal
    canal_key = str(message.channel.id)
    if canal_key not in chat_history:
        chat_history[canal_key] = []

    chat_history[canal_key].append({
        "role":    "user",
        "content": "[{}] {}: {}".format(patente, message.author.display_name, pergunta),
    })

    # Mantém as últimas 6 trocas para economizar tokens
    if len(chat_history[canal_key]) > 6:
        chat_history[canal_key] = chat_history[canal_key][-6:]

    async with message.channel.typing():
        try:
            mensagens_groq = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ] + chat_history[canal_key]

            resposta = await ask_groq(mensagens_groq)
            chat_history[canal_key].append({"role": "assistant", "content": resposta})
            await message.reply("{}\n{}".format(saudacao, resposta))
            add_log("ia", "IA respondeu para {}".format(message.author.display_name))

        except Exception as exc:
            await message.reply("⚠️ Erro ao processar: {}".format(exc))
            add_log("erro", "Erro IA: {}".format(exc))


# ══════════════════════════════════════════════
# COMANDOS PREFIX
# ══════════════════════════════════════════════

@bot.command(name="ping")
async def cmd_ping(ctx: commands.Context) -> None:
    """!ping — verifica latência e status do bot."""
    ms = round(bot.latency * 1000)
    await ctx.send("🟢 Online! Latência: **{}ms** | EB DO RAFA 🪖".format(ms))


@bot.command(name="patente")
async def cmd_patente(ctx: commands.Context) -> None:
    """!patente — exibe sua patente."""
    cargo_nome = get_main_role(ctx.author)
    if cargo_nome and cargo_nome in SAUDACOES:
        patente, saudacao, _nivel = SAUDACOES[cargo_nome]
        await ctx.send("{}\nSua patente é **{}**.".format(saudacao, patente))
    else:
        await ctx.send("🔒 Você não está verificado! Vá ao canal de verificação.")


@bot.command(name="aprovar")
@commands.has_permissions(manage_messages=True)
async def cmd_aprovar(ctx: commands.Context, rel_id: str) -> None:
    """
    !aprovar <id>
    Aprova relatório pendente e envia ao canal final.
    Requer: Gerenciar Mensagens.
    """
    report = next(
        (r for r in pending_reports if r["id"] == rel_id and r["status"] == "pendente"),
        None,
    )
    if not report:
        await ctx.send("⚠️ Relatório `{}` não encontrado ou já processado.".format(rel_id))
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
            try:
                if imagem:
                    raw  = imagem.split(",")[-1]
                    file = discord.File(fp=io.BytesIO(base64.b64decode(raw)), filename="prova.png")
                    await canal.send(msg_text, file=file)
                else:
                    await canal.send(msg_text)
            except discord.HTTPException as exc:
                await ctx.send("⚠️ Erro ao enviar: {}".format(exc))
                return

    add_log("aprov", "Relatório {} ({}) aprovado por {}".format(
        rel_id, tipo, ctx.author.display_name))
    await ctx.send("✅ Relatório `{}` aprovado e enviado!".format(rel_id))


@bot.command(name="reprovar")
@commands.has_permissions(manage_messages=True)
async def cmd_reprovar(ctx: commands.Context, rel_id: str, *, motivo: str) -> None:
    """
    !reprovar <id> <motivo>
    Reprova relatório com motivo obrigatório.
    Requer: Gerenciar Mensagens.
    Exemplo: !reprovar abc123 Falta de evidências
    """
    report = next(
        (r for r in pending_reports if r["id"] == rel_id and r["status"] == "pendente"),
        None,
    )
    if not report:
        await ctx.send("⚠️ Relatório `{}` não encontrado ou já processado.".format(rel_id))
        return

    report["status"]     = "reprovado"
    report["motivo_rep"] = motivo

    add_log("reprov", "Relatório {} ({}) reprovado por {} — Motivo: {}".format(
        rel_id, report["tipo"], ctx.author.display_name, motivo))
    await ctx.send(
        "❌ Relatório `{}` reprovado.\n"
        "**Autor:** {}\n"
        "**Motivo:** {}".format(rel_id, report.get("autor", "—"), motivo)
    )


@bot.command(name="perms")
@commands.has_permissions(manage_messages=True)
async def cmd_perms(ctx: commands.Context, nick: str, acao: str) -> None:
    """
    !perms <nick> <dar|revogar>
    Gerencia permissão de envio de relatórios.
    Requer: Gerenciar Mensagens.
    Exemplo: !perms SoldadoX dar
    """
    acao = acao.lower().strip()
    if acao not in ("dar", "revogar"):
        await ctx.send("⚠️ Use: `!perms <nick> dar` ou `!perms <nick> revogar`")
        return

    permissions[nick] = (acao == "dar")
    resp = (
        "✅ Permissão **concedida** para `{}`.".format(nick)
        if acao == "dar"
        else "🚫 Permissão **revogada** de `{}`.".format(nick)
    )
    add_log("perm", "Permissão {}da para {} por {}".format(
        acao, nick, ctx.author.display_name))
    await ctx.send(resp)


@bot.command(name="limpar")
@commands.has_permissions(manage_messages=True)
async def cmd_limpar(ctx: commands.Context) -> None:
    """!limpar — limpa o histórico de IA do canal atual."""
    canal_key = str(ctx.channel.id)
    if canal_key in chat_history:
        chat_history[canal_key] = []
    await ctx.send("🗑️ Histórico de IA limpo para este canal.")


# ══════════════════════════════════════════════
# ERROR HANDLER
# ══════════════════════════════════════════════
@bot.event
async def on_command_error(ctx: commands.Context, error: Exception) -> None:
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("⛔ Você não tem permissão para usar este comando.")
    elif isinstance(error, commands.MissingRequiredArgument):
        cmd_name = ctx.command.name if ctx.command else "?"
        await ctx.send("⚠️ Argumento faltando. Use `!help {}` para ver o uso.".format(cmd_name))
    elif isinstance(error, commands.CommandNotFound):
        pass  # Silencia — a IA trata comandos desconhecidos
    else:
        cmd_name = ctx.command.name if ctx.command else "?"
        add_log("erro", "Erro no comando {}: {}".format(cmd_name, str(error)))


# ══════════════════════════════════════════════
# REQUIREMENTS.TXT (referência)
# ══════════════════════════════════════════════
# discord.py==2.3.2
# requests==2.31.0
# audioop-lts==0.2.1
# aiohttp==3.9.5


# ══════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError(
            "\n[ERRO] Variável DISCORD_TOKEN não definida!\n"
            "Configure-a no Railway antes de iniciar o bot.\n"
        )
    bot.run(DISCORD_TOKEN)
