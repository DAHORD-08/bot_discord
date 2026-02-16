# db.py -- stockage simple des tags (discord_id -> clash tag)
import aiosqlite
from config import DB_PATH # DB_PATH doit être défini dans config.py

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS users (
    discord_id INTEGER PRIMARY KEY,
    cr_tag TEXT NOT NULL
);
"""

async def init_db():
    """Initialise la base de données (crée le fichier et la table si nécessaire)."""
    # aiosqlite.connect est déjà asynchrone
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_SQL)
        await db.commit()

async def set_user_tag(discord_id: int, tag: str):
    """Sauvegarde ou met à jour le tag CR d'un utilisateur."""
    # Nettoyage du tag (retire # et met en majuscules)
    clean_tag = tag.upper().replace("#","")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Utilise ON CONFLICT (UPSERT) pour insérer ou mettre à jour
        await db.execute(
            "INSERT INTO users(discord_id, cr_tag) VALUES(?, ?) ON CONFLICT(discord_id) DO UPDATE SET cr_tag=excluded.cr_tag", 
            (discord_id, clean_tag)
        )
        await db.commit()

async def get_user_tag(discord_id: int) -> str | None:
    """Récupère le tag CR d'un utilisateur Discord."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT cr_tag FROM users WHERE discord_id = ?", (discord_id,))
        row = await cur.fetchone()
        # Retourne le tag ou None si non trouvé
        return None if row is None else row[0]