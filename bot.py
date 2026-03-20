import discord
from discord.ext import commands
from groq import Groq
import os

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

SYSTEM_PROMPT = """Você é o Assistente Oficial do grupo Exército Brasileiro (EB) no Roblox.
Responda SEMPRE em português brasileiro, de forma clara, respeitosa e militar.
Use linguagem formal mas acessível. Quando adequado, use termos militares.

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
9. Respeitar os inimigos capturados
10. Pedidos de promoção devem ser feitos pelo canal correto

=== TREINAMENTOS E EVENTOS ===
- Treinamento Básico (TB): Obrigatório para sair de Recruta.
- Treinamento de Combate (TC): Táticas de CQB e cobertura de território.
- Patrulha: Varredura do mapa em esquadrão.
- Operação: Missão com objetivo específico, requer patente mínima de Cabo.
- Cerimônia de Promoção: Evento oficial para promover membros.
- Treinamento de Oficiais (TO): Exclusivo para aspirantes e tenentes.
- Guerra: Confronto contra grupos rivais, requer convocação.

Nunca invente informações. Finalize com: "Sentido! 🫡" ou "À vontade, soldado!"
"""

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
client_ai = Groq(api_key=GROQ_API_KEY)
historico = {}

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

    if canal_id not in historico:
        historico[canal_id] = []

    historico[canal_id].append({
        "role": "user",
        "content": f"{message.author.display_name} pergunta: {pergunta}"
    })

    if len(historico[canal_id]) > 10:
        historico[canal_id] = historico[canal_id][-10:]

    async with message.channel.typing():
        try:
            mensagens = [{"role": "system", "content": SYSTEM_PROMPT}] + historico[canal_id]

            resposta = client_ai.chat.completions.create(
                model="llama3-8b-8192",
                messages=mensagens,
                max_tokens=500
            )

            texto = resposta.choices[0].message.content

            historico[canal_id].append({
                "role": "assistant",
                "content": texto
            })

            if len(texto) > 1990:
                partes = [texto[i:i+1990] for i in range(0, len(texto), 1990)]
                for parte in partes:
                    await message.reply(parte)
            else:
                await message.reply(texto)

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

bot.run(DISCORD_TOKEN)
