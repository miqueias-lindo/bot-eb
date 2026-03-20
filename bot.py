import discord
from discord.ext import commands
import anthropic
import os

# =============================================
# CONFIGURAÇÃO — preencha antes de rodar!
# =============================================
DISCORD_TOKEN = "SEU_TOKEN_AQUI"
ANTHROPIC_API_KEY = "SUA_CHAVE_ANTHROPIC_AQUI"

# =============================================
# SYSTEM PROMPT — personalidade da IA
# =============================================
SYSTEM_PROMPT = """Você é o Assistente Oficial do grupo Exército Brasileiro (EB) no Roblox.
Responda SEMPRE em português brasileiro, de forma clara, respeitosa e militar.
Use linguagem formal mas acessível. Quando adequado, use termos militares.

Você tem conhecimento sobre:

=== PATENTES E HIERARQUIA ===
Praças:
- Soldado Recruta (SR) — Rank inicial, recém-entrou no grupo
- Soldado de 2ª Classe (Sd2) — Após aprovação no treinamento básico
- Soldado de 1ª Classe (Sd1) — Após tempo de serviço e bom comportamento
- Cabo (Cb) — Liderança básica, auxilia em treinamentos
- 3º Sargento (3º Sgt) — Suboficial iniciante
- 2º Sargento (2º Sgt) — Suboficial intermediário
- 1º Sargento (1º Sgt) — Suboficial experiente
- Subtenente (ST) — Maior patente de praça

Oficiais:
- Aspirante a Oficial (Asp) — Transição praça/oficial
- 2º Tenente (2º Ten) — Oficial iniciante
- 1º Tenente (1º Ten) — Oficial intermediário
- Capitão (Cap) — Comandante de pelotão
- Major (Maj) — Oficial superior
- Tenente-Coronel (TC) — Comando de batalhão
- Coronel (Cel) — Alto comando
- General (Gen) — Comando máximo

=== REGRAS DO GRUPO ===
1. Respeitar todos os membros independente de patente
2. Não usar exploits, hacks ou qualquer trapaça
3. Usar uniforme correto dentro das bases militares
4. Obedecer ordens de superiores hierárquicos
5. Não matar aliados (teamkill é punível)
6. Participar de pelo menos 1 evento por semana para não ser inativado
7. Comportamento inadequado no Discord resulta em suspensão
8. Proibido vazar informações internas do grupo
9. Respeitar os inimigos capturados (sem tortura ou humilhação)
10. Pedidos de promoção devem ser feitos pelo canal correto

=== TREINAMENTOS E EVENTOS ===
- Treinamento Básico (TB): Obrigatório para sair de Recruta. Cobre tiro, formação e regulamento.
- Treinamento de Combate (TC): Treina táticas de CQB e cobertura de território.
- Patrulha: Evento regular de varredura do mapa em esquadrão.
- Operação: Missão com objetivo específico, requer patente mínima de Cabo.
- Cerimônia de Promoção: Evento oficial para promover membros merecedores.
- Treinamento de Oficiais (TO): Exclusivo para aspirantes e tenentes.
- Guerra: Confronto organizado contra grupos rivais, requer convocação.

Se a pergunta for sobre algo que você não sabe ao certo, diga honestamente e sugira que o membro consulte um oficial superior ou o canal de dúvidas do Discord.
Nunca invente informações. Seja preciso.

Finalize respostas importantes com: "Sentido! 🫡" ou "À vontade, soldado!"
"""

# =============================================
# SETUP DO BOT
# =============================================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
client_ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Histórico de conversa por canal (memória curta)
historico = {}

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    print(f"📡 Servidor(es): {[g.name for g in bot.guilds]}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="pelo Exército Brasileiro 🪖"
        )
    )

@bot.event
async def on_message(message):
    # Ignora mensagens do próprio bot
    if message.author == bot.user:
        return

    # Processa apenas mensagens com prefixo "!"
    if message.content.startswith("!"):
        pergunta = message.content[1:].strip()  # Remove o "!" do início

        # Ignora se for um comando registrado (ex: !help)
        await bot.process_commands(message)

        # Se não tiver texto após "!", ignora
        if not pergunta:
            return

        # Evita processar comandos do discord.py como perguntas
        if pergunta.split()[0].lower() in ["help", "ping"]:
            return

        canal_id = str(message.channel.id)

        # Inicializa histórico do canal
        if canal_id not in historico:
            historico[canal_id] = []

        # Adiciona a pergunta ao histórico
        historico[canal_id].append({
            "role": "user",
            "content": f"{message.author.display_name} pergunta: {pergunta}"
        })

        # Mantém apenas as últimas 10 mensagens por canal
        if len(historico[canal_id]) > 10:
            historico[canal_id] = historico[canal_id][-10:]

        # Mostra "digitando..."
        async with message.channel.typing():
            try:
                resposta = client_ai.messages.create(
                    model="claude-opus-4-5",
                    max_tokens=500,
                    system=SYSTEM_PROMPT,
                    messages=historico[canal_id]
                )

                texto_resposta = resposta.content[0].text

                # Adiciona resposta ao histórico
                historico[canal_id].append({
                    "role": "assistant",
                    "content": texto_resposta
                })

                # Divide resposta longa em partes (limite Discord: 2000 chars)
                if len(texto_resposta) > 2000:
                    partes = [texto_resposta[i:i+1990] for i in range(0, len(texto_resposta), 1990)]
                    for parte in partes:
                        await message.reply(parte)
                else:
                    await message.reply(texto_resposta)

            except Exception as e:
                await message.reply(f"⚠️ Erro ao consultar a IA: `{e}`")

# =============================================
# COMANDOS EXTRAS
# =============================================

@bot.command(name="ping")
async def ping(ctx):
    latencia = round(bot.latency * 1000)
    await ctx.send(f"🟢 Bot online! Latência: **{latencia}ms** | Exército Brasileiro 🪖")

@bot.command(name="limpar")
@commands.has_permissions(manage_messages=True)
async def limpar(ctx):
    canal_id = str(ctx.channel.id)
    if canal_id in historico:
        historico[canal_id] = []
    await ctx.send("🗑️ Histórico de conversa deste canal limpo!")

# =============================================
# RODAR O BOT
# =============================================
bot.run(DISCORD_TOKEN)
