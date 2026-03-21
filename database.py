"""
database.py — Banco de dados SQLite assíncrono (aiosqlite)
Gerencia: relatórios, logs, permissões, rate limit, cache de cargos.
"""

import aiosqlite
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from config import DB_PATH, DEBUG


# ══════════════════════════════════════════════
# SCHEMA
# ══════════════════════════════════════════════
SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Permissões de usuários
CREATE TABLE IF NOT EXISTS permissoes (
    discord_id   TEXT PRIMARY KEY,
    nick         TEXT NOT NULL DEFAULT '',
    nivel        TEXT NOT NULL DEFAULT 'user',   -- user | staff | admin
    pode_relatorio INTEGER NOT NULL DEFAULT 0,
    criado_em    TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Relatórios
CREATE TABLE IF NOT EXISTS relatorios (
    id           TEXT PRIMARY KEY,
    tipo         TEXT NOT NULL,
    campos       TEXT NOT NULL,   -- JSON
    autor_id     TEXT NOT NULL,
    autor_nick   TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'pendente',  -- pendente | aprovado | reprovado
    motivo_rep   TEXT,
    aprovado_por TEXT,
    criado_em    TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Logs do sistema
CREATE TABLE IF NOT EXISTS logs (
    id        TEXT PRIMARY KEY,
    tipo      TEXT NOT NULL,   -- auth | relat | aprov | reprov | perm | block | staff | erro | ia
    mensagem  TEXT NOT NULL,
    user_id   TEXT DEFAULT 'system',
    user_nick TEXT DEFAULT 'system',
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Rate limit de relatórios (anti-spam)
CREATE TABLE IF NOT EXISTS rate_limit (
    user_id      TEXT NOT NULL,
    acao         TEXT NOT NULL,  -- relatorio | login
    criado_em    TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, acao, criado_em)
);

-- Cache de cargos Discord
CREATE TABLE IF NOT EXISTS cargo_cache (
    discord_id  TEXT PRIMARY KEY,
    cargos_json TEXT NOT NULL,
    patente     TEXT NOT NULL DEFAULT '',
    cargo_nome  TEXT,
    cached_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_relatorios_status   ON relatorios(status);
CREATE INDEX IF NOT EXISTS idx_relatorios_autor    ON relatorios(autor_id);
CREATE INDEX IF NOT EXISTS idx_logs_tipo           ON logs(tipo);
CREATE INDEX IF NOT EXISTS idx_logs_criado         ON logs(criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_rate_limit_user     ON rate_limit(user_id, acao);
"""


# ══════════════════════════════════════════════
# CONEXÃO
# ══════════════════════════════════════════════
async def get_db() -> aiosqlite.Connection:
    """Retorna conexão com o banco. Row factory ativa para dicts."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db() -> None:
    """Cria todas as tabelas se não existirem."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.executescript(SCHEMA)
        await db.commit()
    if DEBUG:
        print("[DB] Banco inicializado em:", DB_PATH)


def _now() -> str:
    return datetime.utcnow().isoformat()


def _gen_id() -> str:
    return str(uuid.uuid4())[:12]


def row_to_dict(row) -> Dict:
    """Converte aiosqlite.Row para dict."""
    if row is None:
        return {}
    return dict(row)


# ══════════════════════════════════════════════
# PERMISSÕES
# ══════════════════════════════════════════════
async def get_permissao(discord_id: str) -> Dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM permissoes WHERE discord_id = ?", (discord_id,)
        ) as cur:
            row = await cur.fetchone()
            return row_to_dict(row)


async def upsert_permissao(discord_id: str, nick: str = "", nivel: str = "user",
                           pode_relatorio: bool = False) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO permissoes (discord_id, nick, nivel, pode_relatorio, atualizado_em)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(discord_id) DO UPDATE SET
                nick = excluded.nick,
                nivel = excluded.nivel,
                pode_relatorio = excluded.pode_relatorio,
                atualizado_em = excluded.atualizado_em
        """, (discord_id, nick, nivel, int(pode_relatorio), _now()))
        await db.commit()


async def set_permissao_relatorio(discord_id: str, pode: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO permissoes (discord_id, pode_relatorio, atualizado_em)
            VALUES (?, ?, ?)
            ON CONFLICT(discord_id) DO UPDATE SET
                pode_relatorio = excluded.pode_relatorio,
                atualizado_em = excluded.atualizado_em
        """, (discord_id, int(pode), _now()))
        await db.commit()


async def listar_permissoes(limit: int = 100, offset: int = 0) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM permissoes ORDER BY criado_em DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ) as cur:
            rows = await cur.fetchall()
            return [row_to_dict(r) for r in rows]


# ══════════════════════════════════════════════
# RELATÓRIOS
# ══════════════════════════════════════════════
async def criar_relatorio(tipo: str, campos: Dict, autor_id: str,
                          autor_nick: str = "") -> str:
    rel_id = _gen_id()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO relatorios (id, tipo, campos, autor_id, autor_nick, status, criado_em, atualizado_em)
            VALUES (?, ?, ?, ?, ?, 'pendente', ?, ?)
        """, (rel_id, tipo, json.dumps(campos, ensure_ascii=False),
              autor_id, autor_nick, _now(), _now()))
        await db.commit()
    return rel_id


async def get_relatorio(rel_id: str) -> Dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM relatorios WHERE id = ?", (rel_id,)
        ) as cur:
            row = await cur.fetchone()
            d = row_to_dict(row)
            if d.get("campos"):
                d["campos"] = json.loads(d["campos"])
            return d


async def listar_relatorios(status: Optional[str] = None, limit: int = 50,
                            offset: int = 0) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            async with db.execute(
                "SELECT * FROM relatorios WHERE status = ? ORDER BY criado_em DESC LIMIT ? OFFSET ?",
                (status, limit, offset)
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM relatorios ORDER BY criado_em DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ) as cur:
                rows = await cur.fetchall()
        result = []
        for r in rows:
            d = row_to_dict(r)
            if d.get("campos"):
                d["campos"] = json.loads(d["campos"])
            result.append(d)
        return result


async def aprovar_relatorio(rel_id: str, aprovado_por: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "UPDATE relatorios SET status='aprovado', aprovado_por=?, atualizado_em=? WHERE id=? AND status='pendente'",
            (aprovado_por, _now(), rel_id)
        )
        await db.commit()
        return cur.rowcount > 0


async def reprovar_relatorio(rel_id: str, motivo: str, reprovado_por: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "UPDATE relatorios SET status='reprovado', motivo_rep=?, aprovado_por=?, atualizado_em=? WHERE id=? AND status='pendente'",
            (motivo, reprovado_por, _now(), rel_id)
        )
        await db.commit()
        return cur.rowcount > 0


async def contar_relatorios_por_status() -> Dict[str, int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT status, COUNT(*) as n FROM relatorios GROUP BY status"
        ) as cur:
            rows = await cur.fetchall()
            return {r[0]: r[1] for r in rows}


# ══════════════════════════════════════════════
# LOGS
# ══════════════════════════════════════════════
async def add_log(tipo: str, mensagem: str, user_id: str = "system",
                  user_nick: str = "system") -> None:
    log_id = _gen_id()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO logs (id, tipo, mensagem, user_id, user_nick, criado_em)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (log_id, tipo, mensagem, user_id, user_nick, _now()))
        await db.commit()
    if DEBUG:
        print(f"[LOG/{tipo.upper()}] {mensagem}")


async def listar_logs(tipo: Optional[str] = None, busca: Optional[str] = None,
                      limit: int = 100, offset: int = 0) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        conditions = []
        params: List[Any] = []

        if tipo:
            conditions.append("tipo = ?")
            params.append(tipo)
        if busca:
            conditions.append("(mensagem LIKE ? OR user_nick LIKE ?)")
            params.extend([f"%{busca}%", f"%{busca}%"])

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.extend([limit, offset])

        async with db.execute(
            f"SELECT * FROM logs {where} ORDER BY criado_em DESC LIMIT ? OFFSET ?",
            params
        ) as cur:
            rows = await cur.fetchall()
            return [row_to_dict(r) for r in rows]


async def contar_logs() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM logs") as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


# ══════════════════════════════════════════════
# RATE LIMIT
# ══════════════════════════════════════════════
async def check_rate_limit(user_id: str, acao: str,
                           limite: int, janela_segundos: int) -> bool:
    """
    Retorna True se o usuário EXCEDEU o limite (deve ser bloqueado).
    Limpa entradas antigas automaticamente.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Limpa entradas antigas
        await db.execute("""
            DELETE FROM rate_limit
            WHERE user_id = ? AND acao = ?
            AND criado_em < datetime('now', ? || ' seconds')
        """, (user_id, acao, f"-{janela_segundos}"))

        # Conta entradas recentes
        async with db.execute("""
            SELECT COUNT(*) FROM rate_limit
            WHERE user_id = ? AND acao = ?
        """, (user_id, acao)) as cur:
            row = await cur.fetchone()
            count = row[0] if row else 0

        if count >= limite:
            await db.commit()
            return True

        # Registra nova ação
        await db.execute("""
            INSERT INTO rate_limit (user_id, acao, criado_em)
            VALUES (?, ?, datetime('now'))
        """, (user_id, acao))
        await db.commit()
        return False


# ══════════════════════════════════════════════
# CACHE DE CARGOS
# ══════════════════════════════════════════════
async def get_cargo_cache(discord_id: str, ttl_seconds: int) -> Optional[Dict]:
    """Retorna cache se válido, None se expirado."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM cargo_cache
            WHERE discord_id = ?
            AND cached_at > datetime('now', ? || ' seconds')
        """, (discord_id, f"-{ttl_seconds}")) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            d = row_to_dict(row)
            d["cargos"] = json.loads(d["cargos_json"])
            return d


async def set_cargo_cache(discord_id: str, cargos: List[Dict],
                          patente: str, cargo_nome: Optional[str]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO cargo_cache (discord_id, cargos_json, patente, cargo_nome, cached_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(discord_id) DO UPDATE SET
                cargos_json = excluded.cargos_json,
                patente     = excluded.patente,
                cargo_nome  = excluded.cargo_nome,
                cached_at   = excluded.cached_at
        """, (discord_id, json.dumps(cargos, ensure_ascii=False), patente, cargo_nome))
        await db.commit()


# ══════════════════════════════════════════════
# STATS GERAIS
# ══════════════════════════════════════════════
async def get_stats() -> Dict:
    """Retorna estatísticas gerais para o painel staff."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM permissoes") as cur:
            total_users = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM permissoes WHERE pode_relatorio = 1") as cur:
            com_perm = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM relatorios WHERE status = 'pendente'") as cur:
            pendentes = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM relatorios WHERE status = 'aprovado'") as cur:
            aprovados = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM relatorios WHERE status = 'reprovado'") as cur:
            reprovados = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM logs") as cur:
            total_logs = (await cur.fetchone())[0]

    return {
        "total_users":   total_users,
        "com_perm":      com_perm,
        "sem_perm":      total_users - com_perm,
        "pendentes":     pendentes,
        "aprovados":     aprovados,
        "reprovados":    reprovados,
        "total_logs":    total_logs,
    }
