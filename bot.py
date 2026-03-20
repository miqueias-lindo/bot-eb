import discord
from discord.ext import commands
import requests
import os

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

SYSTEM_PROMPT = """Você é o Assistente Oficial do grupo Exército Brasileiro (EB) no Roblox.
Responda SEMPRE em português brasileiro, de forma clara, respeitosa e militar.

=== PATENTES E HIERARQUIA ===
Praças: Soldado Recruta (SR), Soldado 2ª Classe (Sd2), Soldado 1ª Classe (Sd1), Cabo (Cb), 3º Sargento, 2º Sargento, 1º Sargento, Subtenente (ST)
Oficiais: Aspirante (Asp), 2º Tenente, 1º Tenente, Capitão (Cap), Major (Maj), Tenente-Coronel (TC), Coronel (Cel), General (Gen)

=== REGRAS DO GRUPO ===
1. Respeitar todos os membros
2. Não usar exploits ou hacks
3. Usar uniforme correto nas bases
4. Obedecer superiores hierárquicos
5. Não matar aliados (teamkill é punível)
6. Participar de pelo menos 1 evento por semana
7. Comportamento inadequado no Discord resulta em suspensão
8. Proibido vazar informações internas
9. Respeitar inimigos capturados
10. Pedidos de promoção pelo canal correto

=== TREINAMENTOS E EVENTOS ===
- Treinamento Básico (TB): Obrigatório para sair de Recruta
- Treinamento de Combate (TC): Táticas de CQB
- Patrulha: Varredura do mapa em esquadrão
- Operação: Requer patente mínima de Cabo
- Cerimônia de Promoção: Evento oficial
- Treinamento de Oficiais (TO): Para aspirantes e tenentes
- Guerra: Confronto contra grupos rivais

Nunca invente informações. Finalize com: "Sentido! 🫡" ou "À vontade, soldado!"
"""

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
        "model": "llama3-8b-8192",
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
        raise Exception(f"Resposta inesperada da API: {data}")
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
            texto = perguntar_groq(mensagens)

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
