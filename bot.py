import discord
from discord.ext import commands
import requests
import os

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Hierarquia de cargos (ordem do mais alto pro mais baixo)
HIERARQUIA = [
    # Fundação/Direção
    "Fundador",
    "[CD] Con-Dono",
    "[DG] Diretor Geral",
    "[VDA] Vice-diretor-geral",
    "[M] Maneger",
    # Militares superiores
    "[MAL] Marechal",
    "[GEN-E] General de Exército",
    "[GEN-D] General de Divisão",
    "[GEN-B] General de brigada",
    "[GEN] Generais",
    # Oficiais superiores
    "[CEL] Coronel",
    "[T-CEL] Tenente Coronel",
    "[MAJ] Major",
    "[CAP] Capitão",
    # Oficiais subalternos
    "[1-TNT] Primeiro Tenente",
    "[2-TNT] Segundo tenente",
    "[AAO] Aspirante-A-oficial",
    "[CDT] Cadete",
    "[OF] Oficiais",
    # Suboficiais
    "[SUB-T] Sub Tenente",
    "[GDS] Graduados",
    "[1-SGT] Primeiro sargento",
    "[2-SGT] Segundo Sargento",
    "[3-SGT] Terceiro sargento",
    # Praças
    "[PRÇ] Praças",
    "[CB] Cabo",
    "[SLD] Soldado",
    "[RCT] Recruta",
    # Staff
    "Supervisores",
    "[ADM] Administrador",
    "[MOD] Moderador",
    "[HLP] Helper",
    "[T-STF] Trial Staff",
    # Dev
    "[DEV] Developers",
    "[B] Builder",
    # Outros
    "Verificado",
]

# Saudações por cargo
SAUDACOES = {
    "Fundador": ("Fundador", "Olá, Fundador! 👑 O EB é seu!", "alto"),
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
    "[T-CEL] Tenente Coronel": ("Tenente-Coronel", "À vontade, Tenente-Coronel! 🔴", "alto"),
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
    "[2-SGT] Segundo Sargento": ("2º Sargento", "À vontade, 2º Sargento! 🟢", "baixo"),
    "[3-SGT] Terceiro sargento": ("3º Sargento", "Sentido, 3º Sargento! 🟢", "baixo"),
    "[PRÇ] Praças": ("Praça", "Sentido, Praça! 🟢", "baixo"),
    "[CB] Cabo": ("Cabo", "Sentido, Cabo! 🟢", "baixo"),
    "[SLD] Soldado": ("Soldado", "Sentido, Soldado! 🟢", "baixo"),
    "[RCT] Recruta": ("Recruta", "Sentido, Recruta! 🫡 Bem-vindo ao EB!", "baixo"),
    "Supervisores": ("Supervisor", "Olá, Supervisor! 🛡️", "medio"),
    "[ADM] Administrador": ("Administrador", "Olá, Administrador! 🛡️", "medio"),
    "[MOD] Moderador": ("Moderador", "Olá, Moderador! 🛡️", "medio"),
    "[HLP] Helper": ("Helper", "Olá, Helper! 🛡️", "baixo"),
    "[T-STF] Trial Staff": ("Trial Staff", "Olá, Trial Staff! 🛡️", "baixo"),
    "[DEV] Developers": ("Developer", "Olá, Dev! 💻", "medio"),
    "[B] Builder": ("Builder", "Olá, Builder! 🔨", "baixo"),
    "Verificado": ("Verificado", "Olá, soldado verificado! 🟢", "baixo"),
}

SYSTEM_PROMPT_BASE = """Você é o Assistente Oficial do Exército Brasileiro (EB) no Roblox.
Responda SEMPRE em português brasileiro. NUNCA mencione sites externos, apenas informações do próprio jogo EB no Roblox.

=== PATENTES E HIERARQUIA ===
Praças: [RCT] Recruta → [SLD] Soldado → [CB] Cabo → [PRÇ] Praças → [3-SGT] → [2-SGT] → [1-SGT] → [GDS] Graduados → [SUB-T] Subtenente
Oficiais: [CDT] Cadete → [AAO] Aspirante → [2-TNT] → [1-TNT] → [CAP] Capitão → [MAJ] Major → [T-CEL] → [CEL] Coronel → [GEN-B] → [GEN-D] → [GEN-E] → [MAL] Marechal

=== REGRAS DO GRUPO ===
1. Respeitar todos os membros independente de patente
2. Não usar exploits ou hacks — punição imediata
3. Usar uniforme correto dentro das bases
4. Obedecer ordens de superiores
5. Não matar aliados (teamkill é punível)
6. Participar de pelo menos 1 evento por semana
7. Comportamento inadequado no Discord resulta em suspensão
8. Proibido vazar informações internas
9. Respeitar inimigos capturados
10. Pedidos de promoção pelo canal correto no Discord

=== TREINAMENTOS E EVENTOS ===
- Treinamento Básico (TB): Obrigatório para sair de Recruta
- Treinamento de Combate (TC): Táticas de CQB
- Patrulha: Varredura do mapa em esquadrão
- Operação: Requer patente mínima de Cabo
- Cerimônia de Promoção: Evento oficial para promover membros
- Treinamento de Oficiais (TO): Exclusivo para aspirantes e tenentes
- Guerra: Confronto contra grupos rivais, requer convocação

=== VERIFICAÇÃO ===
Para se verificar no servidor: vá ao canal de verificação e siga as instruções do bot Rover para vincular sua conta Roblox ao Discord. Isso é obrigatório para participar das atividades do EB.

Adapte o tom conforme o nível do usuário:
- Nível ALTO (Generais, Diretores, Fundadores): tom muito respeitoso e formal
- Nível MEDIO (Oficiais, Sargentos, Staff): tom respeitoso e profissional  
- Nível BAIXO (Praças, Recrutas): tom firme, encorajador e didático

Nunca mencione sites externos. Finalize respostas com: "Sentido! 🫡" ou "À vontade, {patente}!"
"""

def get_cargo_principal(member):
    nomes_cargos = [r.name for r in member.roles]
    for cargo in HIERARQUIA:
        if cargo in nomes_cargos:
            return cargo
    return None

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
historico = {}

def perguntar_groq(mensagens):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": mensagens,
        "max_tokens": 500
    }
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )
    data = response.json()
    if "choices" not in data:
        raise Exception(f"Erro da API: {data}")
    return data["choices"][0]["message"]["content"]

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="pelo Exército Brasileiro 🪖"
        )
    )

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

    if pergunta.split()[0].lower() in ["ping", "limpar", "help"]:
        return

    canal_id = str(message.channel.id)
    member = message.author

    # Detecta cargo principal
    cargo_nome = get_cargo_principal(member)

    if cargo_nome and cargo_nome in SAUDACOES:
        patente, saudacao, nivel = SAUDACOES[cargo_nome]
    else:
        # Não verificado
        patente = "Civil"
        saudacao = "Olá, civil! Você ainda não está verificado no servidor. 🔒"
        nivel = "civil"

    if canal_id not in historico:
        historico[canal_id] = []

    historico[canal_id].append({
        "role": "user",
        "content": f"{saudacao} {message.author.display_name} ({patente}) pergunta: {pergunta}"
    })

    if len(historico[canal_id]) > 10:
        historico[canal_id] = historico[canal_id][-10:]

    async with message.channel.typing():
        try:
            system = SYSTEM_PROMPT_BASE.replace("{patente}", patente)

            # Adiciona contexto extra para não verificados
            if nivel == "civil":
                system += "\nEste usuário NÃO está verificado. Oriente-o a ir ao canal de verificação e usar o bot Rover para vincular sua conta Roblox. Sem verificação não é possível participar das atividades do EB."

            mensagens = [{"role": "system", "content": system}] + historico[canal_id]
            texto = perguntar_groq(mensagens)

            historico[canal_id].append({
                "role": "assistant",
                "content": texto
            })

            # Adiciona saudação antes da resposta
            resposta_final = f"{saudacao}\n\n{texto}"

            if len(resposta_final) > 1990:
                partes = [resposta_final[i:i+1990] for i in range(0, len(resposta_final), 1990)]
                for parte in partes:
                    await message.reply(parte)
            else:
                await message.reply(resposta_final)

        except Exception as e:
            await message.reply(f"Erro: {e}")

@bot.command(name="ping")
async def ping(ctx):
    latencia = round(bot.latency * 1000)
    await ctx.send(f"🟢 Online! Latência: {latencia}ms | Exército Brasileiro 🪖")

@bot.command(name="limpar")
@commands.has_permissions(manage_messages=True)
async def limpar(ctx):
    canal_id = str(ctx.channel.id)
    if canal_id in historico:
        historico[canal_id] = []
    await ctx.send("🗑️ Histórico limpo!")

@bot.command(name="patente")
async def patente(ctx):
    member = ctx.author
    cargo_nome = get_cargo_principal(member)
    if cargo_nome and cargo_nome in SAUDACOES:
        patente_nome, saudacao, nivel = SAUDACOES[cargo_nome]
        await ctx.send(f"{saudacao} Sua patente é **{patente_nome}**.")
    else:
        await ctx.send("🔒 Você não está verificado! Vá ao canal de verificação e use o bot Rover para vincular sua conta Roblox.")

bot.run(DISCORD_TOKEN)
