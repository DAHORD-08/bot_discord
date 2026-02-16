# bot.py
import asyncio
import logging
import discord
from discord.ext import commands
from config import DISCORD_TOKEN, GUILD_IDS
import os # Nécessaire pour Render
from db import init_db # <-- NÉCESSAIRE POUR LA DB

# --- AJOUTS POUR LE SERVEUR WEB RENDER ---
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    # Render visitera ceci pour vérifier que le service est "en vie"
    return "DH2 Bot est ACTIF et tourne."

def run_flask_server():
    # Utilise le port fourni par Render (généralement 10000)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

def keep_alive():
    """Démarre le serveur Flask dans un thread séparé."""
    t = Thread(target=run_flask_server)
    t.start()
# -------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dh2")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True # Gardé si vous utilisez des commandes préfixées
bot = commands.Bot(command_prefix="!", intents=intents)

async def load_cogs():
    # Utilisation des noms de fichiers que vous avez fournis
    extensions = [
        "cogs.help",
        "cogs.connexion",
        "cogs.profile",
        "cogs.clan",
        "cogs.card",
        "cogs.rules"
    ]
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            logger.info(f"✅ Cog chargé : {extension}")
        except Exception as e:
            logger.error(f"❌ Erreur de chargement du cog {extension}: {e}")

@bot.event
async def on_ready():
    logger.info(f"✅ Connecté en tant que {bot.user} (id: {bot.user.id})")

    # Sync commands
    if GUILD_IDS:
        for guild_id in GUILD_IDS:
            guild = discord.Object(id=guild_id)
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        logger.info("🔄 Commandes synchronisées pour les serveurs de test.")
    else:
        await bot.tree.sync()
        logger.info("🌍 Commandes synchronisées globalement (peut prendre 1h).")

async def main():
    # 1. Initialiser la base de données
    await init_db()
    logger.info("✅ Base de données initialisée.")
    
    # 2. Démarrer le serveur Web pour Render
    keep_alive()
    logger.info("🌐 Serveur Web (pour Render) démarré.")
    
    # 3. Démarrer le bot
    await load_cogs()
    # Nous utilisons bot.start() et laissons Flask dans le thread séparé
    await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    try:
        # La boucle principale gère à la fois le bot Discord et la DB asynchrone
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Arrêt manuel du bot.")