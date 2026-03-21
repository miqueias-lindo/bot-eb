"""
bot.py — EB DO RAFA
Sistema de aprovação de relatórios com botões nativos do Discord.

Fluxo:
  1. Frontend envia POST /relatorio → bot manda no canal de aprovação
  2. Staff vê o card com botões ✅ Aprovar / ❌ Reprovar
  3. Aprovado → bot envia pro canal correto + registra no banco
  4. Reprovado → bot avisa no canal + registra motivo

Dependências: discord.py==2.3.2, aiohttp==3.9.5, aiosqlite==0.20.0
"""

import asyncio
import base64
import io
import json
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

import aiosqlite
import discord
from discord.ext import commands
from discord import ui
import requests
from aiohttp import web

# ══════════════════════════════════════════════
# CONFIG (via variáveis de ambiente)
# ══════════════════════════════════════════════
DISCORD_TOKEN    = os.environ.get("DISCORD_TOKEN", "")
GUILD_ID         = int(os.environ.get("GUILD_ID", "0"))
PORT             = int(os.environ.get("PORT", "8080"))
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")
DEBUG            = os.environ.get("DEBUG", "false").lower() == "true"

# Canal onde chegam os relatórios para aprovação
CANAL_APROVACAO  = 1472483300743577631

# Canais de destino final por tipo de relatório
CANAL_TREINO       = 1470637515441569893
CANAL_RECRUTAMENTO = 1470637472781304022
CANAL_ADV          = 1470637705032499335
CANAL_REBAIXAMENTO = 1470637643888070762
CANAL_BANIMENTO    = 1470637613332431002
CANAL_EXILIO       = 1470637554825957591
CANAL_ANUNCIOS     = 1470635151523578078
CANAL_EVENTOS      = 1470635180535582720
CANAL_SORTEIOS     = 1472329428888584357

CANAL_POR_TIPO = {
    "treino":          CANAL_TREINO,
    "recrut":          CANAL_RECRUTAMENTO,
    "adv":             CANAL_ADV,
    "rebx":            CANAL_REBAIXAMENTO,
    "ban":             CANAL_BANIMENTO,
    "exil":            CANAL_EXILIO,
    "aviso":           CANAL_ANUNCIOS,
    "evento_eventos":  CANAL_EVENTOS,
    "evento_anuncios": CANAL_ANUNCIOS,
    "evento_sorteios": CANAL_SORTEIOS,
}

LABEL_POR_TIPO = {
    "treino":  "Treinamento",
    "recrut":  "Recrutamento",
    "adv":     "Advertência",
    "rebx":    "Rebaixamento",
    "ban":     "Banimento",
    "exil":    "Exílio",
    "aviso":   "Aviso",
}

EMOJI_POR_TIPO = {
    "treino": "📖", "recrut": "🪖", "adv": "⚠️",
    "rebx": "📉",   "ban": "🚫",    "exil": "🏴‍☠️",
    "aviso": "📢",
}

DB_PATH = os.environ.get("DB_PATH", "eb_database.db")

# ══════════════════════════════════════════════
# HIERARQUIA / IA
# ══════════════════════════════════════════════
HIERARQUIA = [
    "Fundador","[CD] Con-Dono","[DG] Diretor Geral","[VDA] Vice-diretor-geral","[M] Maneger",
    "[MAL] Marechal","[GEN-E] General de Exército","[GEN-D] General de Divisão",
    "[GEN-B] General de brigada","[GEN] Generais","[CEL] Coronel","[T-CEL] Tenente Coronel",
    "[MAJ] Major","[CAP] Capitão","[1-TNT] Primeiro Tenente","[2-TNT] Segundo tenente",
    "[AAO] Aspirante-A-oficial","[CDT] Cadete","[OF] Oficiais","[SUB-T] Sub Tenente",
    "[GDS] Graduados","[1-SGT] Primeiro sargento","[2-SGT] Segundo Sargento",
    "[3-SGT] Terceiro sargento","[PRÇ] Praças","[CB] Cabo","[SLD] Soldado","[RCT] Recruta",
    "Supervisores","[ADM] Administrador","[MOD] Moderador","[HLP] Helper","[T-STF] Trial Staff",
    "[DEV] Developers","[B] Builder","Verificado",
]
SAUDACOES = {
    "Fundador":("Fundador","Olá, Fundador! 👑","alto"),
    "[CD] Con-Dono":("Con-Dono","Olá, Con-Dono! 👑","alto"),
    "[DG] Diretor Geral":("Diretor Geral","À vontade, Diretor Geral! 🏅","alto"),
    "[MAL] Marechal":("Marechal","Sentido, Marechal! 🎖️","alto"),
    "[GEN-E] General de Exército":("General de Exército","À vontade, General! ⭐⭐⭐⭐","alto"),
    "[CEL] Coronel":("Coronel","À vontade, Coronel! 🔴","alto"),
    "[T-CEL] Tenente Coronel":("Tenente-Coronel","À vontade, Ten-Cel! 🔴","medio"),
    "[MAJ] Major":("Major","À vontade, Major! 🔴","medio"),
    "[CAP] Capitão":("Capitão","À vontade, Capitão! 🔴","medio"),
    "[1-TNT] Primeiro Tenente":("1º Tenente","À vontade, 1º Ten! 🔴","medio"),
    "[SUB-T] Sub Tenente":("Subtenente","À vontade, Subtenente! 🟢","medio"),
    "[1-SGT] Primeiro sargento":("1º Sargento","À vontade, 1º Sgt! 🟢","medio"),
    "[CB] Cabo":("Cabo","Sentido, Cabo! 🟢","baixo"),
    "[SLD] Soldado":("Soldado","Sentido, Soldado! 🟢","baixo"),
    "[RCT] Recruta":("Recruta","Sentido, Recruta! 🫡","baixo"),
    "[ADM] Administrador":("Administrador","Olá, Administrador! 🛡️","medio"),
    "[MOD] Moderador":("Moderador","Olá, Moderador! 🛡️","medio"),
    "[DEV] Developers":("Developer","Olá, Dev! 💻","medio"),
    "Verificado":("Cidadão","Olá, Cidadão! 🟡","civil"),
}

SYSTEM_PROMPT = (
    "Você é o assistente oficial do Exército Brasileiro (EB) no Roblox. "
    "Responda em português, de forma CURTA e direta (máximo 3 linhas). "
    "Seja formal e respeitoso com os postos."
)

# ══════════════════════════════════════════════
# BANCO DE DADOS
# ══════════════════════════════════════════════
SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS relatorios (
    id           TEXT PRIMARY KEY,
    tipo         TEXT NOT NULL,
    campos       TEXT NOT NULL,
    autor_nick   TEXT NOT NULL DEFAULT '',
    autor_id     TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'pendente',
    motivo_rep   TEXT,
    aprovado_por TEXT,
    discord_msg_id TEXT,
    criado_em    TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS logs (
    id        TEXT PRIMARY KEY,
    tipo      TEXT NOT NULL,
    mensagem  TEXT NOT NULL,
    user_nick TEXT DEFAULT 'system',
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()

async def salvar_relatorio(rel_id, tipo, campos, autor_nick, autor_id, msg_id=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO relatorios (id,tipo,campos,autor_nick,autor_id,discord_msg_id,criado_em,atualizado_em) VALUES (?,?,?,?,?,?,datetime('now'),datetime('now'))",
            (rel_id, tipo, json.dumps(campos, ensure_ascii=False), autor_nick, autor_id, str(msg_id))
        )
        await db.commit()

async def aprovar_db(rel_id, aprovado_por):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE relatorios SET status='aprovado', aprovado_por=?, atualizado_em=datetime('now') WHERE id=?",
            (aprovado_por, rel_id)
        )
        await db.commit()

async def reprovar_db(rel_id, motivo, reprovado_por):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE relatorios SET status='reprovado', motivo_rep=?, aprovado_por=?, atualizado_em=datetime('now') WHERE id=?",
            (motivo, reprovado_por, rel_id)
        )
        await db.commit()

async def get_relatorio(rel_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM relatorios WHERE id=?", (rel_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            d = dict(row)
            d["campos"] = json.loads(d["campos"])
            return d

async def listar_relatorios(status=None, limit=50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            q = "SELECT * FROM relatorios WHERE status=? ORDER BY criado_em DESC LIMIT ?"
            async with db.execute(q, (status, limit)) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute("SELECT * FROM relatorios ORDER BY criado_em DESC LIMIT ?", (limit,)) as cur:
                rows = await cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["campos"] = json.loads(d["campos"])
            result.append(d)
        return result

async def add_log(tipo, msg, user="system"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO logs (id,tipo,mensagem,user_nick,criado_em) VALUES (?,?,?,?,datetime('now'))",
            (str(uuid.uuid4())[:8], tipo, msg, user)
        )
        await db.commit()

async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM relatorios WHERE status='pendente'") as c:
            pendentes = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM relatorios WHERE status='aprovado'") as c:
            aprovados = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM relatorios WHERE status='reprovado'") as c:
            reprovados = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM logs") as c:
            total_logs = (await c.fetchone())[0]
    return {"pendentes": pendentes, "aprovados": aprovados, "reprovados": reprovados, "total_logs": total_logs}

# ══════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════
def fmt_campos(campos: dict) -> str:
    linhas = []
    nomes = {
        "instrutor": "Instrutor", "treinados": "Treinados", "data": "Data",
        "status": "Status", "observacoes": "Observações", "recrutado": "Recrutado",
        "recrutador": "Recrutador", "jogador": "Jogador", "motivo": "Motivo",
        "grau": "Grau", "usuario": "Usuário", "cargo_anterior": "Cargo Anterior",
        "novo_cargo": "Novo Cargo", "tempo": "Duração", "exilado": "Exilado",
        "tipo": "Tipo", "responsavel": "Responsável",
    }
    for k, v in campos.items():
        if v and v != "—":
            label = nomes.get(k, k.replace("_", " ").title())
            linhas.append(f"**{label}:** {v}")
    return "\n".join(linhas)

def get_main_role(member: discord.Member) -> Optional[str]:
    role_names = {r.name for r in member.roles}
    for rank in HIERARQUIA:
        if rank in role_names:
            return rank
    return None

def gen_id() -> str:
    return str(uuid.uuid4())[:10]

def now_str() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")

# ══════════════════════════════════════════════
# BOT SETUP
# ══════════════════════════════════════════════
intents                 = discord.Intents.default()
intents.message_content = True
intents.members         = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Anti-flood IA
flood_control: defaultdict = defaultdict(list)
FLOOD_LIMIT  = 4
FLOOD_WINDOW = 60

chat_history: Dict[str, List[Dict]] = {}
KNOWN_CMDS = frozenset({"ping", "patente", "limpar", "help"})

# ══════════════════════════════════════════════
# BOTÕES DE APROVAÇÃO (discord.py 2.x UI)
# ══════════════════════════════════════════════
class BotoesAprovacao(ui.View):
    """
    View com 2 botões: Aprovar ✅ e Reprovar ❌.
    Persistente — funciona mesmo após reinício do bot usando custom_id.
    """
    def __init__(self, rel_id: str, tipo: str, autor_nick: str):
        super().__init__(timeout=None)  # sem timeout — fica permanente
        self.rel_id     = rel_id
        self.tipo       = tipo
        self.autor_nick = autor_nick

        # Adiciona botões com custom_id único por relatório
        self.add_item(BtnAprovar(rel_id, tipo, autor_nick))
        self.add_item(BtnReprovar(rel_id, tipo, autor_nick))


class BtnAprovar(ui.Button):
    def __init__(self, rel_id, tipo, autor_nick):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="✅ Aprovar",
            custom_id=f"aprovar:{rel_id}",
        )
        self.rel_id     = rel_id
        self.tipo       = tipo
        self.autor_nick = autor_nick

    async def callback(self, interaction: discord.Interaction):
        rel = await get_relatorio(self.rel_id)
        if not rel:
            await interaction.response.send_message("⚠️ Relatório não encontrado.", ephemeral=True)
            return
        if rel["status"] != "pendente":
            await interaction.response.send_message(
                f"⚠️ Este relatório já foi **{rel['status']}**.", ephemeral=True
            )
            return

        # Salva aprovação no banco
        await aprovar_db(self.rel_id, interaction.user.display_name)
        await add_log("aprov", f"Relatório {self.rel_id} ({self.tipo}) aprovado por {interaction.user.display_name}")

        # Envia pro canal final do tipo
        canal_id = CANAL_POR_TIPO.get(self.tipo)
        if canal_id:
            canal = bot.get_channel(canal_id)
            if canal:
                emoji = EMOJI_POR_TIPO.get(self.tipo, "📋")
                label = LABEL_POR_TIPO.get(self.tipo, self.tipo.capitalize())
                embed = discord.Embed(
                    title=f"{emoji} {label}",
                    color=0x00dd66,  # verde
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Autor", value=self.autor_nick, inline=True)
                embed.add_field(name="Aprovado por", value=interaction.user.display_name, inline=True)
                embed.add_field(name="ID", value=f"`{self.rel_id}`", inline=True)

                campos = rel.get("campos", {})
                corpo = fmt_campos(campos)
                if corpo:
                    embed.add_field(name="Informações", value=corpo, inline=False)

                embed.set_footer(text="EB DO RAFA — Sistema de Relatórios")
                await canal.send(embed=embed)

        # Edita a mensagem original desabilitando os botões
        await interaction.response.edit_message(
            content=(
                f"✅ **Relatório aprovado!**\n"
                f"**Tipo:** {LABEL_POR_TIPO.get(self.tipo, self.tipo)} | "
                f"**Autor:** {self.autor_nick} | "
                f"**Aprovado por:** {interaction.user.display_name}\n"
                f"ID: `{self.rel_id}`"
            ),
            view=None  # Remove os botões
        )

        await interaction.followup.send(
            f"✅ Relatório de **{LABEL_POR_TIPO.get(self.tipo, self.tipo)}** aprovado e enviado ao canal!",
            ephemeral=True
        )


class BtnReprovar(ui.Button):
    def __init__(self, rel_id, tipo, autor_nick):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="❌ Reprovar",
            custom_id=f"reprovar:{rel_id}",
        )
        self.rel_id     = rel_id
        self.tipo       = tipo
        self.autor_nick = autor_nick

    async def callback(self, interaction: discord.Interaction):
        rel = await get_relatorio(self.rel_id)
        if not rel:
            await interaction.response.send_message("⚠️ Relatório não encontrado.", ephemeral=True)
            return
        if rel["status"] != "pendente":
            await interaction.response.send_message(
                f"⚠️ Este relatório já foi **{rel['status']}**.", ephemeral=True
            )
            return

        # Abre modal para pedir motivo
        await interaction.response.send_modal(ModalMotivo(self.rel_id, self.tipo, self.autor_nick))


class ModalMotivo(ui.Modal, title="❌ Motivo da Reprovação"):
    motivo = ui.TextInput(
        label="Motivo",
        placeholder="Descreva o motivo da reprovação...",
        style=discord.TextStyle.paragraph,
        required=True,
        min_length=5,
        max_length=300,
    )

    def __init__(self, rel_id, tipo, autor_nick):
        super().__init__()
        self.rel_id     = rel_id
        self.tipo       = tipo
        self.autor_nick = autor_nick

    async def on_submit(self, interaction: discord.Interaction):
        motivo_txt = self.motivo.value.strip()

        await reprovar_db(self.rel_id, motivo_txt, interaction.user.display_name)
        await add_log("reprov", f"Relatório {self.rel_id} ({self.tipo}) reprovado por {interaction.user.display_name} — {motivo_txt}")

        # Edita a mensagem original
        await interaction.response.edit_message(
            content=(
                f"❌ **Relatório reprovado.**\n"
                f"**Tipo:** {LABEL_POR_TIPO.get(self.tipo, self.tipo)} | "
                f"**Autor:** {self.autor_nick}\n"
                f"**Motivo:** {motivo_txt}\n"
                f"**Reprovado por:** {interaction.user.display_name}\n"
                f"ID: `{self.rel_id}`"
            ),
            view=None
        )


# ══════════════════════════════════════════════
# FUNÇÃO PRINCIPAL: ENVIAR RELATÓRIO PARA APROVAÇÃO
# ══════════════════════════════════════════════
async def enviar_para_aprovacao(tipo: str, campos: dict, autor_nick: str,
                                 autor_id: str, imagem_b64: Optional[str] = None) -> str:
    """
    Envia o relatório para o canal de aprovação com botões.
    Retorna o ID gerado do relatório.
    """
    rel_id = gen_id()
    canal  = bot.get_channel(CANAL_APROVACAO)

    if not canal:
        await add_log("erro", f"Canal de aprovação {CANAL_APROVACAO} não encontrado")
        return rel_id

    emoji = EMOJI_POR_TIPO.get(tipo, "📋")
    label = LABEL_POR_TIPO.get(tipo, tipo.capitalize())
    corpo = fmt_campos(campos)

    # Monta a mensagem
    texto = (
        f"## {emoji} Novo relatório de {label}\n"
        f"**Enviado por:** {autor_nick}\n"
        f"**Data:** {now_str()}\n"
        f"**ID:** `{rel_id}`\n"
        f"{'─'*35}\n"
        f"{corpo}\n"
        f"{'─'*35}\n"
        f"*Aprove ou reprove abaixo 👇*"
    )

    view = BotoesAprovacao(rel_id, tipo, autor_nick)

    try:
        if imagem_b64:
            raw  = imagem_b64.split(",")[-1]
            file = discord.File(fp=io.BytesIO(base64.b64decode(raw)), filename="prova.png")
            msg  = await canal.send(content=texto, file=file, view=view)
        else:
            msg  = await canal.send(content=texto, view=view)

        # Salva no banco com o ID da mensagem Discord
        await salvar_relatorio(rel_id, tipo, campos, autor_nick, autor_id, msg.id)
        await add_log("relat", f"Relatório {label} enviado para aprovação por {autor_nick} | ID:{rel_id}")

    except discord.HTTPException as e:
        await add_log("erro", f"Erro ao enviar para aprovação: {e}")

    return rel_id


# ══════════════════════════════════════════════
# EVENTOS DO BOT
# ══════════════════════════════════════════════
@bot.event
async def on_ready():
    print(f"🤖 Bot: {bot.user} | Guilds: {len(bot.guilds)}")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="pelo EB 🪖")
    )
    await add_log("system", f"Bot iniciado: {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

    if not message.content.startswith("!"):
        return
    pergunta = message.content[1:].strip()
    if not pergunta or pergunta.split()[0].lower() in KNOWN_CMDS:
        return

    # Anti-flood
    now = time.time()
    flood_control[message.author.id] = [
        t for t in flood_control[message.author.id] if now - t < FLOOD_WINDOW
    ]
    if len(flood_control[message.author.id]) >= FLOOD_LIMIT:
        await message.reply("⛔ Devagar, soldado! Aguarde antes de perguntar novamente.")
        return
    flood_control[message.author.id].append(now)

    if not GROQ_API_KEY:
        return

    cargo = get_main_role(message.author)
    patente, saudacao = "Civil", "Olá! 🔒"
    if cargo and cargo in SAUDACOES:
        patente, saudacao, _ = SAUDACOES[cargo]

    canal_key = str(message.channel.id)
    if canal_key not in chat_history:
        chat_history[canal_key] = []
    chat_history[canal_key].append({
        "role": "user",
        "content": f"[{patente}] {message.author.display_name}: {pergunta}"
    })
    if len(chat_history[canal_key]) > 6:
        chat_history[canal_key] = chat_history[canal_key][-6:]

    async with message.channel.typing():
        try:
            loop = asyncio.get_event_loop()
            msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history[canal_key]
            resposta = await loop.run_in_executor(None, _groq_sync, msgs)
            chat_history[canal_key].append({"role": "assistant", "content": resposta})
            await message.reply(f"{saudacao}\n{resposta}")
        except Exception as e:
            if DEBUG:
                await message.reply(f"⚠️ Erro: {e}")


def _groq_sync(messages):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 150, "temperature": 0.7},
        timeout=30,
    )
    d = r.json()
    if "choices" not in d:
        raise ValueError(str(d))
    return d["choices"][0]["message"]["content"]


# ══════════════════════════════════════════════
# COMANDOS
# ══════════════════════════════════════════════
@bot.command(name="ping")
async def cmd_ping(ctx):
    await ctx.send(f"🟢 Online! **{round(bot.latency*1000)}ms** | EB DO RAFA 🪖")


@bot.command(name="patente")
async def cmd_patente(ctx):
    cargo = get_main_role(ctx.author)
    if cargo and cargo in SAUDACOES:
        patente, saudacao, _ = SAUDACOES[cargo]
        await ctx.send(f"{saudacao}\nSua patente é **{patente}**.")
    else:
        await ctx.send("🔒 Você não está verificado!")


@bot.command(name="limpar")
@commands.has_permissions(manage_messages=True)
async def cmd_limpar(ctx):
    chat_history.pop(str(ctx.channel.id), None)
    await ctx.send("🗑️ Histórico de IA limpo.")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("⛔ Sem permissão.")
    elif isinstance(error, commands.CommandNotFound):
        pass


# ══════════════════════════════════════════════
# API REST (aiohttp)
# ══════════════════════════════════════════════
CORS = {
    "Access-Control-Allow-Origin":  "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}

def jresp(data: dict, status=200) -> web.Response:
    return web.Response(
        text=json.dumps(data, ensure_ascii=False),
        status=status,
        headers={**CORS, "Content-Type": "application/json; charset=utf-8"},
    )

async def h_options(r): return web.Response(status=204, headers=CORS)

async def h_ping(r):
    return jresp({"status": "online", "ts": datetime.utcnow().isoformat()})

async def h_cargos(r: web.Request):
    user_id = r.rel_url.query.get("user_id", "").strip()
    if not user_id:
        return jresp({"error": "user_id obrigatório"}, 400)

    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return jresp({"error": "Servidor não encontrado"}, 404)

    try:
        member = await guild.fetch_member(int(user_id))
    except discord.NotFound:
        return jresp({"error": "Membro não encontrado"}, 404)
    except Exception as e:
        return jresp({"error": str(e)}, 500)

    STAFF_ROLE_ID = os.environ.get("STAFF_ROLE_ID", "1470615090951880806")
    cargos = [{"id": str(rr.id), "nome": rr.name} for rr in member.roles if rr.name != "@everyone"]
    cargo_nome = get_main_role(member)
    patente    = "Cidadão"
    if cargo_nome and cargo_nome in SAUDACOES:
        patente = SAUDACOES[cargo_nome][0]
    is_staff = any(str(rr.id) == STAFF_ROLE_ID for rr in member.roles)

    return jresp({"cargos": cargos, "patente": patente, "cargo_nome": cargo_nome,
                  "is_staff": is_staff})

async def h_relatorio(r: web.Request):
    """
    POST /relatorio
    Recebe relatório do site e envia para o canal de aprovação com botões.
    """
    try:
        data = await r.json()
    except Exception:
        return jresp({"error": "JSON inválido"}, 400)

    tipo       = str(data.get("tipo", "")).strip()
    campos     = data.get("campos", {})
    autor_nick = str(data.get("autor_nick", "Desconhecido"))
    autor_id   = str(data.get("autor_id", ""))
    imagem     = data.get("imagem")

    if not tipo or not campos:
        return jresp({"error": "tipo e campos obrigatórios"}, 400)
    if tipo not in CANAL_POR_TIPO and tipo != "aviso":
        return jresp({"error": f"Tipo '{tipo}' inválido"}, 400)

    rel_id = await enviar_para_aprovacao(tipo, campos, autor_nick, autor_id, imagem)
    return jresp({"ok": True, "id": rel_id, "status": "pendente"}, 201)

async def h_relatorios(r: web.Request):
    """GET /relatorios?status=pendente — lista relatórios"""
    status = r.rel_url.query.get("status")
    limit  = int(r.rel_url.query.get("limit", 50))
    rels   = await listar_relatorios(status, limit)
    stats  = await get_stats()
    return jresp({"relatorios": rels, "stats": stats})

async def h_logs(r: web.Request):
    """GET /logs — lista logs"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        limit = int(r.rel_url.query.get("limit", 100))
        async with db.execute(
            "SELECT * FROM logs ORDER BY criado_em DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
            logs = [dict(row) for row in rows]
    return jresp({"logs": logs, "total": len(logs)})

async def h_send_discord(r: web.Request):
    """POST /discord/send — envia aviso/evento direto ao canal (sem aprovação)"""
    try:
        data = await r.json()
    except Exception:
        return jresp({"error": "JSON inválido"}, 400)

    tipo   = str(data.get("tipo", ""))
    campos = data.get("campos", {})
    imagem = data.get("imagem")

    canal_id = CANAL_POR_TIPO.get(tipo)
    if not canal_id:
        return jresp({"error": f"Tipo '{tipo}' sem canal configurado"}, 400)

    canal = bot.get_channel(canal_id)
    if not canal:
        return jresp({"error": "Canal não encontrado"}, 404)

    label = LABEL_POR_TIPO.get(tipo, tipo.capitalize())
    corpo = fmt_campos(campos)
    texto = f"**📢 {label.upper()}**\n{'─'*30}\n{corpo}"

    try:
        if imagem:
            raw  = imagem.split(",")[-1]
            file = discord.File(fp=io.BytesIO(base64.b64decode(raw)), filename="img.png")
            await canal.send(texto, file=file)
        else:
            await canal.send(texto)
        await add_log("staff", f"{label} enviado diretamente ao Discord")
        return jresp({"ok": True})
    except Exception as e:
        return jresp({"error": str(e)}, 500)


# ══════════════════════════════════════════════
# SERVIDOR WEB
# ══════════════════════════════════════════════
async def start_api():
    app = web.Application()
    app.router.add_route("OPTIONS", "/{p:.*}", h_options)
    app.router.add_get( "/ping",       h_ping)
    app.router.add_get( "/cargos",     h_cargos)
    app.router.add_post("/relatorio",  h_relatorio)
    app.router.add_get( "/relatorios", h_relatorios)
    app.router.add_get( "/logs",       h_logs)
    app.router.add_post("/discord/send", h_send_discord)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"✅ API rodando na porta {PORT}")


# ══════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════
async def main():
    print("═"*45)
    print("  EB DO RAFA — Bot v3.0")
    print("═"*45)
    await init_db()
    print("✅ Banco de dados pronto")
    await start_api()
    print("✅ API iniciada")
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN não definido!")
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
