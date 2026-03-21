"""
api.py — Rotas da API REST (aiohttp)
Todos os endpoints do sistema EB DO RAFA.
"""

import json
import base64
import io
from typing import Optional
from aiohttp import web

import discord as _discord

import database as db
from permissions import (
    requer_auth, requer_staff, requer_perm_relatorio,
    gerar_token, verificar_token, is_staff, can_send_relatorio
)
from config import (
    DEBUG, ADMIN_IDS, CANAL_POR_TIPO, HIERARQUIA, SAUDACOES,
    CARGO_CACHE_TTL, STAFF_ROLE_ID
)

# Referência ao bot (injetada pelo main.py)
bot_ref: Optional[object] = None


# ══════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════
CORS = {
    "Access-Control-Allow-Origin":  "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}


def ok(data: dict, status: int = 200) -> web.Response:
    return web.Response(
        text=json.dumps({"ok": True, **data}, ensure_ascii=False),
        status=status,
        headers={**CORS, "Content-Type": "application/json; charset=utf-8"},
    )


def erro(mensagem: str, status: int = 400) -> web.Response:
    return web.Response(
        text=json.dumps({"ok": False, "error": mensagem}, ensure_ascii=False),
        status=status,
        headers={**CORS, "Content-Type": "application/json; charset=utf-8"},
    )


async def parse_json(request: web.Request) -> Optional[dict]:
    try:
        return await request.json()
    except Exception:
        return None


def get_main_role(member) -> Optional[str]:
    role_names = {r.name for r in member.roles}
    for rank in HIERARQUIA:
        if rank in role_names:
            return rank
    return None


def format_report_discord(tipo: str, campos: dict) -> str:
    SEP = "─" * 34
    templates = {
        "treino":   ("📖", "TREINAMENTO",   [("👤 Instrutor", "instrutor"), ("👥 Treinados", "treinados"), ("📅 Data", "data"), ("📊 Status", "status"), ("📝 Obs", "observacoes")]),
        "recrut":   ("🪖", "RECRUTAMENTO",  [("👤 Recrutado", "recrutado"), ("👮 Recrutador", "recrutador"), ("📅 Data", "data"), ("📝 Obs", "observacoes")]),
        "adv":      ("⚠️", "ADVERTÊNCIA",   [("👤 Jogador", "jogador"), ("📝 Motivo", "motivo"), ("🔢 Grau", "grau"), ("📅 Data", "data")]),
        "rebx":     ("📉", "REBAIXAMENTO",  [("👤 Usuário", "usuario"), ("⬆️ Anterior", "cargo_anterior"), ("⬇️ Novo", "novo_cargo"), ("📝 Motivo", "motivo"), ("📅 Data", "data")]),
        "ban":      ("🚫", "BANIMENTO",     [("👤 Jogador", "jogador"), ("📝 Motivo", "motivo"), ("⏳ Duração", "tempo"), ("📅 Data", "data")]),
        "exil":     ("🏴‍☠️", "EXÍLIO",     [("👤 Exilado", "exilado"), ("📝 Motivo", "motivo"), ("⛓️ Tipo", "tipo"), ("📅 Data", "data"), ("👮 Resp.", "responsavel")]),
        "aviso":    ("📢", "AVISO OFICIAL", [("📌 Título", "titulo"), ("📄 Mensagem", "mensagem")]),
    }
    if tipo.startswith("evento_"):
        emoji, titulo, fields = "📅", "EVENTO", [("🎯 Tipo", "tipo"), ("📅 Data", "data"), ("📝 Desc.", "descricao")]
        titulo = "EVENTO: " + campos.get("nome", "—")
    elif tipo in templates:
        emoji, titulo, fields = templates[tipo]
        titulo = f"RELATÓRIO DE {titulo}"
    else:
        return str(campos)
    corpo = "\n".join(f"**{label}:** {campos.get(key, '—')}" for label, key in fields)
    return f"**{emoji} {titulo} {emoji}**\n{SEP}\n{corpo}\n{SEP}"


async def send_to_discord(tipo: str, campos: dict, imagem_b64: Optional[str] = None) -> bool:
    """Envia mensagem para o canal Discord correto."""
    if bot_ref is None:
        return False
    canal_id = CANAL_POR_TIPO.get(tipo)
    if not canal_id:
        return False
    canal = bot_ref.get_channel(canal_id)
    if not canal:
        return False
    msg = format_report_discord(tipo, campos)
    try:
        if imagem_b64:
            raw  = imagem_b64.split(",")[-1]
            file = _discord.File(fp=io.BytesIO(base64.b64decode(raw)), filename="prova.png")
            await canal.send(msg, file=file)
        else:
            await canal.send(msg)
        return True
    except _discord.HTTPException as e:
        if DEBUG:
            print(f"[API] Erro ao enviar Discord: {e}")
        return False


async def notify_staff_novo_relatorio(rel_id: str, tipo: str, autor: str) -> None:
    """Notifica canal de aprovação quando novo relatório chega."""
    if not bot_ref or not CANAL_POR_TIPO:
        return
    from config import CANAL_APROVACAO
    if not CANAL_APROVACAO:
        return
    canal = bot_ref.get_channel(CANAL_APROVACAO)
    if not canal:
        return
    labels = {"treino": "Treinamento", "recrut": "Recrutamento", "adv": "Advertência",
              "rebx": "Rebaixamento", "ban": "Banimento", "exil": "Exílio"}
    label = labels.get(tipo, tipo.capitalize())
    try:
        await canal.send(
            f"🔔 **Novo relatório aguardando aprovação!**\n"
            f"**Tipo:** {label} | **Autor:** {autor} | **ID:** `{rel_id}`\n"
            f"Use `!aprovar {rel_id}` ou `!reprovar {rel_id} <motivo>`"
        )
    except Exception:
        pass


# ══════════════════════════════════════════════
# HANDLERS
# ══════════════════════════════════════════════

async def handle_options(request: web.Request) -> web.Response:
    return web.Response(status=204, headers=CORS)


async def handle_ping(request: web.Request) -> web.Response:
    from datetime import datetime
    return ok({"status": "online", "ts": datetime.utcnow().isoformat()})


# ── AUTH ────────────────────────────────────

async def handle_auth(request: web.Request) -> web.Response:
    """
    POST /auth
    Body: { "discord_id": "...", "nick": "..." }
    Retorna token para uso nas demais rotas.
    """
    data = await parse_json(request)
    if not data:
        return erro("JSON inválido")

    discord_id = str(data.get("discord_id", "")).strip()
    nick       = str(data.get("nick", "")).strip()

    if not discord_id:
        return erro("'discord_id' obrigatório")

    # Garante entrada na tabela
    perm = await db.get_permissao(discord_id)
    if not perm:
        await db.upsert_permissao(discord_id, nick)

    nivel = "admin" if discord_id in ADMIN_IDS else (perm.get("nivel", "user") if perm else "user")
    token = gerar_token(discord_id)

    await db.add_log("auth", f"Token gerado para {nick or discord_id}", discord_id, nick)

    return ok({
        "token":          token,
        "discord_id":     discord_id,
        "nivel":          nivel,
        "pode_relatorio": await can_send_relatorio(discord_id),
    })


# ── CARGOS ──────────────────────────────────

async def handle_cargos(request: web.Request) -> web.Response:
    """GET /cargos?user_id=DISCORD_ID"""
    user_id = request.rel_url.query.get("user_id", "").strip()
    if not user_id:
        return erro("'user_id' obrigatório", 400)

    # Tenta cache primeiro
    cached = await db.get_cargo_cache(user_id, CARGO_CACHE_TTL)
    if cached:
        if DEBUG:
            print(f"[API] Cache hit para cargos user_id={user_id}")
        return ok({"cargos": cached["cargos"], "patente": cached["patente"],
                   "cargo_nome": cached["cargo_nome"], "cache": True})

    # Busca no Discord
    if bot_ref is None:
        return erro("Bot não conectado", 503)

    from config import GUILD_ID
    guild = bot_ref.get_guild(GUILD_ID)
    if not guild:
        return erro("Servidor não encontrado", 404)

    try:
        member = await guild.fetch_member(int(user_id))
    except _discord.NotFound:
        return erro("Membro não encontrado no servidor", 404)
    except _discord.HTTPException as e:
        return erro(f"Erro Discord: {e}", 500)
    except ValueError:
        return erro("user_id deve ser inteiro", 400)

    cargos = [{"id": str(r.id), "nome": r.name} for r in member.roles if r.name != "@everyone"]
    cargo_nome = get_main_role(member)
    patente    = "Cidadão"
    if cargo_nome and cargo_nome in SAUDACOES:
        patente = SAUDACOES[cargo_nome][0]

    is_staff_member = any(str(r.id) == STAFF_ROLE_ID for r in member.roles) or user_id in ADMIN_IDS

    # Salva cache
    await db.set_cargo_cache(user_id, cargos, patente, cargo_nome)

    # Atualiza nível se for staff
    if is_staff_member:
        perm = await db.get_permissao(user_id)
        if not perm or perm.get("nivel") == "user":
            await db.upsert_permissao(user_id, member.display_name, "staff", True)

    return ok({"cargos": cargos, "patente": patente, "cargo_nome": cargo_nome,
               "is_staff": is_staff_member, "cache": False})


# ── RELATÓRIOS ──────────────────────────────

@requer_perm_relatorio
async def handle_post_relatorio(request: web.Request) -> web.Response:
    """POST /relatorio — envia relatório para aprovação."""
    data = await parse_json(request)
    if not data:
        return erro("JSON inválido")

    tipo   = str(data.get("tipo", "")).strip()
    campos = data.get("campos", {})
    imagem = data.get("imagem")

    if not tipo or not campos:
        return erro("'tipo' e 'campos' obrigatórios")

    if tipo not in CANAL_POR_TIPO:
        return erro(f"Tipo '{tipo}' inválido")

    discord_id = request["discord_id"]
    perm       = await db.get_permissao(discord_id)
    nick       = perm.get("nick", discord_id) if perm else discord_id

    rel_id = await db.criar_relatorio(tipo, campos, discord_id, nick)

    await db.add_log(
        "relat",
        f"Relatório {tipo} enviado → pendente | ID:{rel_id}",
        discord_id, nick
    )

    # Notifica staff no Discord
    await notify_staff_novo_relatorio(rel_id, tipo, nick)

    return ok({"id": rel_id, "status": "pendente"}, 201)


async def handle_get_relatorios(request: web.Request) -> web.Response:
    """GET /relatorios?status=pendente&limit=50&offset=0 (staff only)"""
    discord_id, token = _extrair(request)
    if not discord_id or not verificar_token(discord_id, token or ""):
        return erro("Não autenticado", 401)
    if not await is_staff(discord_id):
        return erro("Acesso negado", 403)

    status = request.rel_url.query.get("status") or None
    limit  = int(request.rel_url.query.get("limit", 50))
    offset = int(request.rel_url.query.get("offset", 0))

    rels    = await db.listar_relatorios(status, limit, offset)
    contagem = await db.contar_relatorios_por_status()

    return ok({"relatorios": rels, "contagem": contagem})


@requer_staff
async def handle_aprovar(request: web.Request) -> web.Response:
    """POST /relatorio/{id}/aprovar"""
    rel_id     = request.match_info["id"]
    discord_id = request["discord_id"]

    rel = await db.get_relatorio(rel_id)
    if not rel:
        return erro("Relatório não encontrado", 404)
    if rel.get("status") != "pendente":
        return erro("Relatório já foi processado")

    perm = await db.get_permissao(discord_id)
    nick = perm.get("nick", discord_id) if perm else discord_id

    ok_db = await db.aprovar_relatorio(rel_id, nick)
    if not ok_db:
        return erro("Erro ao aprovar relatório")

    # Envia ao Discord
    await send_to_discord(rel["tipo"], rel["campos"])

    await db.add_log("aprov", f"Relatório {rel_id} ({rel['tipo']}) aprovado", discord_id, nick)

    return ok({"id": rel_id, "status": "aprovado"})


@requer_staff
async def handle_reprovar(request: web.Request) -> web.Response:
    """POST /relatorio/{id}/reprovar  Body: { motivo }"""
    rel_id = request.match_info["id"]
    data   = await parse_json(request)
    if not data:
        return erro("JSON inválido")

    motivo = str(data.get("motivo", "")).strip()
    if not motivo:
        return erro("'motivo' obrigatório para reprovação")

    discord_id = request["discord_id"]
    rel = await db.get_relatorio(rel_id)
    if not rel:
        return erro("Relatório não encontrado", 404)
    if rel.get("status") != "pendente":
        return erro("Relatório já foi processado")

    perm = await db.get_permissao(discord_id)
    nick = perm.get("nick", discord_id) if perm else discord_id

    ok_db = await db.reprovar_relatorio(rel_id, motivo, nick)
    if not ok_db:
        return erro("Erro ao reprovar")

    await db.add_log(
        "reprov",
        f"Relatório {rel_id} ({rel['tipo']}) reprovado — Motivo: {motivo}",
        discord_id, nick
    )

    return ok({"id": rel_id, "status": "reprovado", "motivo": motivo})


# ── PERMISSÕES ──────────────────────────────

@requer_staff
async def handle_get_permissoes(request: web.Request) -> web.Response:
    """GET /permissoes?limit=100&offset=0"""
    limit  = int(request.rel_url.query.get("limit", 100))
    offset = int(request.rel_url.query.get("offset", 0))
    perms  = await db.listar_permissoes(limit, offset)
    return ok({"permissoes": perms})


@requer_staff
async def handle_set_permissao(request: web.Request) -> web.Response:
    """
    POST /permissoes
    Body: { "discord_id": "...", "pode_relatorio": true, "nivel": "user" }
    """
    data = await parse_json(request)
    if not data:
        return erro("JSON inválido")

    target_id = str(data.get("discord_id", "")).strip()
    if not target_id:
        return erro("'discord_id' obrigatório")

    pode     = bool(data.get("pode_relatorio", False))
    nivel    = str(data.get("nivel", "user"))
    nick     = str(data.get("nick", ""))

    await db.upsert_permissao(target_id, nick, nivel, pode)

    discord_id = request["discord_id"]
    perm_req   = await db.get_permissao(discord_id)
    nick_req   = perm_req.get("nick", discord_id) if perm_req else discord_id

    acao = "concedida" if pode else "revogada"
    await db.add_log(
        "perm",
        f"Permissão de relatório {acao} para {nick or target_id} por {nick_req}",
        discord_id, nick_req
    )

    return ok({"discord_id": target_id, "pode_relatorio": pode, "nivel": nivel})


# ── LOGS ────────────────────────────────────

@requer_staff
async def handle_get_logs(request: web.Request) -> web.Response:
    """GET /logs?tipo=&busca=&limit=100&offset=0"""
    tipo   = request.rel_url.query.get("tipo") or None
    busca  = request.rel_url.query.get("busca") or None
    limit  = int(request.rel_url.query.get("limit", 100))
    offset = int(request.rel_url.query.get("offset", 0))
    total  = await db.contar_logs()
    logs   = await db.listar_logs(tipo, busca, limit, offset)
    return ok({"logs": logs, "total": total})


# ── STATS ───────────────────────────────────

@requer_staff
async def handle_stats(request: web.Request) -> web.Response:
    """GET /stats — estatísticas gerais do sistema"""
    stats = await db.get_stats()
    return ok(stats)


# ── DISCORD SEND (staff) ─────────────────────

@requer_staff
async def handle_send_discord(request: web.Request) -> web.Response:
    """
    POST /discord/send
    Envia mensagem direta ao canal (avisos, eventos).
    Body: { "tipo": "aviso", "campos": {...}, "imagem": null }
    """
    data = await parse_json(request)
    if not data:
        return erro("JSON inválido")

    tipo   = str(data.get("tipo", ""))
    campos = data.get("campos", {})
    imagem = data.get("imagem")

    if not tipo:
        return erro("'tipo' obrigatório")

    enviado = await send_to_discord(tipo, campos, imagem)
    if not enviado:
        return erro("Falha ao enviar ao Discord", 500)

    discord_id = request["discord_id"]
    perm = await db.get_permissao(discord_id)
    nick = perm.get("nick", discord_id) if perm else discord_id
    await db.add_log("staff", f"Mensagem enviada ao Discord: tipo={tipo}", discord_id, nick)

    return ok({"enviado": True})


# ══════════════════════════════════════════════
# REGISTRO DAS ROTAS
# ══════════════════════════════════════════════
def _extrair(request: web.Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, None
    try:
        payload = auth[7:]
        discord_id, token = payload.split(":", 1)
        return discord_id.strip(), token.strip()
    except ValueError:
        return None, None


def registrar_rotas(app: web.Application) -> None:
    # CORS preflight
    app.router.add_route("OPTIONS", "/{path_info:.*}", handle_options)

    # Públicas
    app.router.add_get( "/ping",                 handle_ping)
    app.router.add_post("/auth",                 handle_auth)
    app.router.add_get( "/cargos",               handle_cargos)

    # Autenticadas
    app.router.add_post("/relatorio",            handle_post_relatorio)
    app.router.add_get( "/relatorios",           handle_get_relatorios)
    app.router.add_post("/relatorio/{id}/aprovar",  handle_aprovar)
    app.router.add_post("/relatorio/{id}/reprovar", handle_reprovar)

    # Staff
    app.router.add_get( "/permissoes",           handle_get_permissoes)
    app.router.add_post("/permissoes",           handle_set_permissao)
    app.router.add_get( "/logs",                 handle_get_logs)
    app.router.add_get( "/stats",                handle_stats)
    app.router.add_post("/discord/send",         handle_send_discord)
