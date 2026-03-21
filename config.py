"""
config.py — Configurações centrais do sistema EB DO RAFA
Todas as variáveis de ambiente ficam aqui.
"""

import os
from typing import List

# ══════════════════════════════════════════════
# AMBIENTE
# ══════════════════════════════════════════════
DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"

# ══════════════════════════════════════════════
# DISCORD
# ══════════════════════════════════════════════
DISCORD_TOKEN:    str = os.environ.get("DISCORD_TOKEN", "")
GUILD_ID:         int = int(os.environ.get("GUILD_ID", "0"))
STAFF_ROLE_ID:    str = os.environ.get("STAFF_ROLE_ID", "1470615090951880806")
ADMIN_IDS:        List[str] = os.environ.get("ADMIN_IDS", "1443070630294585436,1240467366408880198").split(",")

# ══════════════════════════════════════════════
# API
# ══════════════════════════════════════════════
API_PORT:         int = int(os.environ.get("PORT", "8080"))
API_SECRET:       str = os.environ.get("API_SECRET", "eb-secret-2026")  # token interno
CORS_ORIGINS:     str = os.environ.get("CORS_ORIGINS", "*")

# ══════════════════════════════════════════════
# BANCO DE DADOS
# ══════════════════════════════════════════════
DB_PATH:          str = os.environ.get("DB_PATH", "eb_database.db")

# ══════════════════════════════════════════════
# CANAIS DISCORD (destino final dos relatórios)
# ══════════════════════════════════════════════
CANAL_APROVACAO:    int = int(os.environ.get("CANAL_APROVACAO", "0"))
CANAL_TREINO:       int = 1470637515441569893
CANAL_RECRUTAMENTO: int = 1470637472781304022
CANAL_ADV:          int = 1470637705032499335
CANAL_REBAIXAMENTO: int = 1470637643888070762
CANAL_BANIMENTO:    int = 1470637613332431002
CANAL_EXILIO:       int = 1470637554825957591
CANAL_ANUNCIOS:     int = 1470635151523578078
CANAL_EVENTOS:      int = 1470635180535582720
CANAL_SORTEIOS:     int = 1472329428888584357

CANAL_POR_TIPO = {
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

# ══════════════════════════════════════════════
# ANTI-FLOOD
# ══════════════════════════════════════════════
FLOOD_LIMIT:      int = int(os.environ.get("FLOOD_LIMIT", "4"))
FLOOD_WINDOW:     int = int(os.environ.get("FLOOD_WINDOW", "60"))   # segundos
RELATORIO_LIMIT:  int = int(os.environ.get("RELATORIO_LIMIT", "10")) # por hora
RELATORIO_WINDOW: int = 3600  # 1 hora

# ══════════════════════════════════════════════
# GROQ IA
# ══════════════════════════════════════════════
GROQ_API_KEY:     str = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL:       str = "llama-3.3-70b-versatile"
GROQ_MAX_TOKENS:  int = 150
GROQ_HISTORY_LEN: int = 6   # mensagens por canal

# ══════════════════════════════════════════════
# CACHE DE CARGOS
# ══════════════════════════════════════════════
CARGO_CACHE_TTL:  int = int(os.environ.get("CARGO_CACHE_TTL", "300"))  # 5 minutos

# ══════════════════════════════════════════════
# HIERARQUIA
# ══════════════════════════════════════════════
HIERARQUIA = [
    "Fundador", "[CD] Con-Dono", "[DG] Diretor Geral", "[VDA] Vice-diretor-geral",
    "[M] Maneger", "[MAL] Marechal", "[GEN-E] General de Exército",
    "[GEN-D] General de Divisão", "[GEN-B] General de brigada", "[GEN] Generais",
    "[CEL] Coronel", "[T-CEL] Tenente Coronel", "[MAJ] Major", "[CAP] Capitão",
    "[1-TNT] Primeiro Tenente", "[2-TNT] Segundo tenente", "[AAO] Aspirante-A-oficial",
    "[CDT] Cadete", "[OF] Oficiais", "[SUB-T] Sub Tenente", "[GDS] Graduados",
    "[1-SGT] Primeiro sargento", "[2-SGT] Segundo Sargento", "[3-SGT] Terceiro sargento",
    "[PRÇ] Praças", "[CB] Cabo", "[SLD] Soldado", "[RCT] Recruta",
    "Supervisores", "[ADM] Administrador", "[MOD] Moderador", "[HLP] Helper",
    "[T-STF] Trial Staff", "[DEV] Developers", "[B] Builder", "Verificado",
]

SAUDACOES = {
    "Fundador":                   ("Fundador",           "Olá, Fundador! 👑",                    "alto"),
    "[CD] Con-Dono":              ("Con-Dono",            "Olá, Con-Dono! 👑",                    "alto"),
    "[DG] Diretor Geral":         ("Diretor Geral",       "À vontade, Diretor Geral! 🏅",          "alto"),
    "[VDA] Vice-diretor-geral":   ("Vice-Diretor",        "À vontade, Vice-Diretor! 🏅",           "alto"),
    "[M] Maneger":                ("Manager",             "À vontade, Manager! 🏅",                "alto"),
    "[MAL] Marechal":             ("Marechal",            "Sentido, Marechal! 🎖️",                 "alto"),
    "[GEN-E] General de Exército":("General de Exército", "À vontade, General de Exército! ⭐⭐⭐⭐","alto"),
    "[GEN-D] General de Divisão": ("General de Divisão",  "À vontade, General de Divisão! ⭐⭐⭐",  "alto"),
    "[GEN-B] General de brigada": ("General de Brigada",  "À vontade, General de Brigada! ⭐⭐",   "alto"),
    "[GEN] Generais":             ("General",             "À vontade, General! ⭐",                "alto"),
    "[CEL] Coronel":              ("Coronel",             "À vontade, Coronel! 🔴",                "alto"),
    "[T-CEL] Tenente Coronel":    ("Tenente-Coronel",     "À vontade, Tenente-Coronel! 🔴",        "medio"),
    "[MAJ] Major":                ("Major",               "À vontade, Major! 🔴",                  "medio"),
    "[CAP] Capitão":              ("Capitão",             "À vontade, Capitão! 🔴",                "medio"),
    "[1-TNT] Primeiro Tenente":   ("1º Tenente",          "À vontade, 1º Tenente! 🔴",             "medio"),
    "[2-TNT] Segundo tenente":    ("2º Tenente",          "À vontade, 2º Tenente! 🔴",             "medio"),
    "[AAO] Aspirante-A-oficial":  ("Aspirante",           "À vontade, Aspirante! 🔴",              "medio"),
    "[CDT] Cadete":               ("Cadete",              "À vontade, Cadete! 🔴",                 "medio"),
    "[OF] Oficiais":              ("Oficial",             "À vontade, Oficial! 🔴",                "medio"),
    "[SUB-T] Sub Tenente":        ("Subtenente",          "À vontade, Subtenente! 🟢",             "medio"),
    "[GDS] Graduados":            ("Graduado",            "À vontade, Graduado! 🟢",               "medio"),
    "[1-SGT] Primeiro sargento":  ("1º Sargento",         "À vontade, 1º Sargento! 🟢",            "medio"),
    "[2-SGT] Segundo Sargento":   ("2º Sargento",         "À vontade, 2º Sargento! 🟢",            "medio"),
    "[3-SGT] Terceiro sargento":  ("3º Sargento",         "Sentido, 3º Sargento! 🟢",              "baixo"),
    "[PRÇ] Praças":               ("Praça",               "Sentido, Praça! 🟢",                    "baixo"),
    "[CB] Cabo":                  ("Cabo",                "Sentido, Cabo! 🟢",                     "baixo"),
    "[SLD] Soldado":              ("Soldado",             "Sentido, Soldado! 🟢",                  "baixo"),
    "[RCT] Recruta":              ("Recruta",             "Sentido, Recruta! 🫡",                  "baixo"),
    "Supervisores":               ("Supervisor",          "Olá, Supervisor! 🛡️",                   "medio"),
    "[ADM] Administrador":        ("Administrador",       "Olá, Administrador! 🛡️",                "medio"),
    "[MOD] Moderador":            ("Moderador",           "Olá, Moderador! 🛡️",                    "medio"),
    "[HLP] Helper":               ("Helper",              "Olá, Helper! 🛡️",                       "baixo"),
    "[T-STF] Trial Staff":        ("Trial Staff",         "Olá, Trial Staff! 🛡️",                  "baixo"),
    "[DEV] Developers":           ("Developer",           "Olá, Dev! 💻",                          "medio"),
    "[B] Builder":                ("Builder",             "Olá, Builder! 🔨",                      "baixo"),
    "Verificado":                 ("Cidadão",             "Olá, Cidadão! 🟡",                      "civil"),
}
