"""
permissions.py — Sistema de verificação de permissões
Verifica autenticação, nível de acesso e rate limit em todas as rotas.
"""

import hashlib
import hmac
from typing import Optional, Tuple
from aiohttp import web

from config import API_SECRET, ADMIN_IDS, DEBUG
from database import get_permissao, check_rate_limit, add_log
from config import RELATORIO_LIMIT, RELATORIO_WINDOW, FLOOD_LIMIT, FLOOD_WINDOW


# ══════════════════════════════════════════════
# TOKEN INTERNO
# ══════════════════════════════════════════════
def gerar_token(discord_id: str) -> str:
    """Gera token HMAC para autenticação interna."""
    return hmac.new(
        API_SECRET.encode(),
        discord_id.encode(),
        hashlib.sha256
    ).hexdigest()


def verificar_token(discord_id: str, token: str) -> bool:
    """Verifica se o token é válido para o discord_id."""
    esperado = gerar_token(discord_id)
    return hmac.compare_digest(esperado, token)


# ══════════════════════════════════════════════
# EXTRAÇÃO DE CREDENCIAIS DO REQUEST
# ══════════════════════════════════════════════
def extrair_credenciais(request: web.Request) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrai discord_id e token do header Authorization.
    Formato: 'Bearer DISCORD_ID:TOKEN'
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, None
    try:
        payload = auth[7:]  # Remove 'Bearer '
        discord_id, token = payload.split(":", 1)
        return discord_id.strip(), token.strip()
    except ValueError:
        return None, None


# ══════════════════════════════════════════════
# DECORATORS / MIDDLEWARES DE ROTA
# ══════════════════════════════════════════════
def requer_auth(handler):
    """
    Decorator: exige autenticação válida.
    Injeta 'discord_id' no request.
    """
    async def wrapper(request: web.Request) -> web.Response:
        discord_id, token = extrair_credenciais(request)

        if not discord_id or not token:
            return _erro(401, "Autenticação necessária")

        if not verificar_token(discord_id, token):
            await add_log("block", f"Token inválido para discord_id={discord_id}")
            return _erro(403, "Token inválido")

        request["discord_id"] = discord_id
        return await handler(request)
    return wrapper


def requer_staff(handler):
    """
    Decorator: exige autenticação + nível staff ou admin.
    """
    async def wrapper(request: web.Request) -> web.Response:
        discord_id, token = extrair_credenciais(request)

        if not discord_id or not token:
            return _erro(401, "Autenticação necessária")

        if not verificar_token(discord_id, token):
            await add_log("block", f"Tentativa não autorizada de acesso staff: discord_id={discord_id}")
            return _erro(403, "Token inválido")

        # Admin sempre passa
        if discord_id in ADMIN_IDS:
            request["discord_id"] = discord_id
            request["nivel"] = "admin"
            return await handler(request)

        # Verifica no banco
        perm = await get_permissao(discord_id)
        if not perm or perm.get("nivel") not in ("staff", "admin"):
            await add_log(
                "block",
                f"Acesso staff negado para discord_id={discord_id}",
                discord_id
            )
            return _erro(403, "Acesso negado — área restrita ao staff")

        request["discord_id"] = discord_id
        request["nivel"] = perm.get("nivel", "user")
        return await handler(request)
    return wrapper


def requer_perm_relatorio(handler):
    """
    Decorator: exige autenticação + permissão de envio de relatório.
    Staff/admin sempre tem permissão.
    """
    async def wrapper(request: web.Request) -> web.Response:
        discord_id, token = extrair_credenciais(request)

        if not discord_id or not token:
            return _erro(401, "Autenticação necessária")

        if not verificar_token(discord_id, token):
            return _erro(403, "Token inválido")

        # Admin sempre passa
        if discord_id in ADMIN_IDS:
            request["discord_id"] = discord_id
            return await handler(request)

        perm = await get_permissao(discord_id)

        # Staff também pode
        if perm and perm.get("nivel") in ("staff", "admin"):
            request["discord_id"] = discord_id
            return await handler(request)

        # Usuário comum precisa de permissão explícita
        if not perm or not perm.get("pode_relatorio"):
            await add_log(
                "block",
                f"Tentativa de envio sem permissão: discord_id={discord_id}",
                discord_id,
                perm.get("nick", "?") if perm else "?"
            )
            return _erro(403, "Sem permissão para enviar relatórios. Solicite ao staff.")

        # Rate limit
        bloqueado = await check_rate_limit(
            discord_id, "relatorio",
            RELATORIO_LIMIT, RELATORIO_WINDOW
        )
        if bloqueado:
            await add_log(
                "block",
                f"Rate limit atingido para relatórios: discord_id={discord_id}",
                discord_id
            )
            return _erro(429, f"Limite de {RELATORIO_LIMIT} relatórios por hora atingido.")

        request["discord_id"] = discord_id
        return await handler(request)
    return wrapper


# ══════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════
def _erro(status: int, mensagem: str) -> web.Response:
    import json
    return web.Response(
        text=json.dumps({"ok": False, "error": mensagem}, ensure_ascii=False),
        status=status,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": "*",
        }
    )


async def is_staff(discord_id: str) -> bool:
    """Verifica se um discord_id tem nível staff ou admin."""
    if discord_id in ADMIN_IDS:
        return True
    perm = await get_permissao(discord_id)
    return bool(perm and perm.get("nivel") in ("staff", "admin"))


async def can_send_relatorio(discord_id: str) -> bool:
    """Verifica se pode enviar relatórios."""
    if discord_id in ADMIN_IDS:
        return True
    perm = await get_permissao(discord_id)
    if not perm:
        return False
    if perm.get("nivel") in ("staff", "admin"):
        return True
    return bool(perm.get("pode_relatorio"))
