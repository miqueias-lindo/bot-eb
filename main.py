"""
main.py — Entry point do sistema EB DO RAFA
Inicializa: banco de dados → API (aiohttp) → Bot (discord.py)
"""

import asyncio
import sys
from aiohttp import web

from config import API_PORT, DEBUG
import database as db
import api
import bot as bot_module


async def main() -> None:
    print("═" * 50)
    print("  EB DO RAFA — Sistema v2.0")
    print("═" * 50)

    # 1. Inicializa banco de dados
    print("[INIT] Inicializando banco de dados...")
    await db.init_db()
    print("[INIT] ✅ Banco de dados pronto")

    # 2. Configura e inicia servidor API
    print(f"[INIT] Iniciando API na porta {API_PORT}...")
    app = web.Application()
    api.registrar_rotas(app)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=API_PORT)
    await site.start()
    print(f"[INIT] ✅ API rodando em 0.0.0.0:{API_PORT}")

    # 3. Inicia bot Discord (injeta referência no módulo api)
    print("[INIT] Conectando bot Discord...")
    try:
        # Injeta bot no api.py para envio de mensagens
        await bot_module.bot.login(bot_module.bot.http.token if hasattr(bot_module.bot, 'http') and bot_module.bot.http.token else __import__('config').DISCORD_TOKEN)
    except Exception:
        pass

    # Cria task do bot
    bot_task = asyncio.create_task(bot_module.start_bot())

    # Aguarda bot conectar e injeta referência
    await asyncio.sleep(3)
    api.bot_ref = bot_module.bot
    print("[INIT] ✅ Bot Discord conectado")

    await db.add_log("system", f"Sistema iniciado na porta {API_PORT}")
    print("[INIT] ✅ Sistema completamente inicializado")
    print("═" * 50)

    # Mantém tudo rodando
    try:
        await bot_task
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Encerrando sistema...")
        await runner.cleanup()
        sys.exit(0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Sistema encerrado.")
