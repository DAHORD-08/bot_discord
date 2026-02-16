# config.py -- charge variables d'environnement
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CLASH_ROYALE_TOKEN = os.getenv("CLASH_ROYALE_TOKEN")
DB_PATH = os.getenv("DB_PATH", "./dh2.db")
# Optionnel : IDs de guilds pour synchroniser les slash commands pendant le dev
GUILD_IDS = [int(x) for x in os.getenv("GUILD_IDS", "").split(",") if x.strip()]

SALON_CONNEXION_NAME = "🔗・connexion" # Le nom du salon pour le message statique
SALON_CONNEXION_ID = os.getenv("SALON_CONNEXION_ID")  # ID du salon de connexion (optionnel)
SALON_ARRIVEE_NAME = "🚉・arrivée"     # Le nom du salon pour le message dynamique de bienvenue
SALON_ARRIVEE_ID = os.getenv("SALON_ARRIVEE_ID")  # ID du salon d'arrivée (optionnel)

WELCOME_BACKGROUND_PATH = "data/welcome_banner.png"
WELCOME_FONT_PATH = "data/welcom_font.ttf"

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN manquant dans .env")
if not CLASH_ROYALE_TOKEN:
    raise RuntimeError("CLASH_ROYALE_TOKEN manquant dans .env")
