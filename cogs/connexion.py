# cogs/connexion.py

import discord
from discord.ext import commands
from discord import ui
import os
import aiohttp
import io
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pathlib import Path
import colorsys
import math 
# --- Imports Corrigés ---
from db import set_user_tag  # Utilise la fonction de la DB (asynchrone)
from cr_api import CRClient, CRApiError
from config import (
    SALON_CONNEXION_NAME, SALON_CONNEXION_ID, SALON_ARRIVEE_NAME, SALON_ARRIVEE_ID,
    WELCOME_BACKGROUND_PATH, WELCOME_FONT_PATH
)

# --- Constantes pour l'Image (Votre code original) ---
TEXT_COLOR_FILL = (250, 250, 250, 255) 
OUTLINE_COLOR_DARK_RED = (139, 0, 0, 255)  
GLOW_COLOR_SINGLE = (255, 200, 200, 255) 
AVATAR_SIZE = 180 
GLOW_ITERATIONS = 2 
OUTLINE_THICKNESS = 5 
GLOW_RADIUS_SINGLE = 12 

font_path = Path(WELCOME_FONT_PATH)
try:
    if font_path.exists():
        resolved_font_path = str(font_path.resolve())
        FONT_NOM = ImageFont.truetype(resolved_font_path, 100) 
    else:
        # Fallback pour le développement ou l'hébergement
        FONT_NOM = ImageFont.load_default(size=60)
except Exception:
    FONT_NOM = ImageFont.load_default(size=60)
# ----------------------------------------------------


class ConnexionModal(discord.ui.Modal, title="Connexion Clash Royale"):
    tag = discord.ui.TextInput(
        label="Entrez votre identifiant Clash Royale (#TAG)",
        placeholder="#ABCDEFG",
        min_length=6,
        max_length=15,
        required=True,
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Vérifie le tag via l'API et sauvegarde dans la DB."""
        # 1. DEFER IMMÉDIAT (Pour éviter le timeout Discord pendant la requête API)
        await interaction.response.defer(ephemeral=True)
        
        player_tag = self.tag.value.strip().upper().replace('#', '')
        user_id = interaction.user.id

        # 2. Vérification du tag via l'API (utilisation de 'async with')
        try:
            async with CRClient() as cr:
                player_data = await cr.get_player(player_tag)
                
            player_name = player_data.get('name', 'Joueur Inconnu')

            # 3. Sauvegarde asynchrone dans la base de données
            await set_user_tag(user_id, player_tag)
            
            await interaction.followup.send(
                f"✅ **Connexion réussie !**\n"
                f"Ton compte Discord est maintenant lié au joueur **{player_name}** (`#{player_tag}`).",
                ephemeral=True
            )
        except CRApiError as e:
            await interaction.followup.send(
                f"❌ **Erreur :** Le tag `#{player_tag}` n'a pas pu être vérifié.\n"
                f"Message de l'API : `{e}`. Assure-toi que le tag est correct.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Une erreur inattendue est survenue : {e}",
                ephemeral=True
            )


class ConnexionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 

    @discord.ui.button(label="🔗 Connexion", style=discord.ButtonStyle.primary, custom_id="connect_button")
    async def connect(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ConnexionModal()
        await interaction.response.send_modal(modal)


# --- Votre fonction generate_welcome_banner (inchangée) ---
async def generate_welcome_banner(member: discord.Member) -> discord.File | None:
    background_path = Path(WELCOME_BACKGROUND_PATH)
    if not background_path.exists():
        return None
    try:
        background = Image.open(str(background_path.resolve())).convert("RGBA")
        draw = ImageDraw.Draw(background)
        async with aiohttp.ClientSession() as session:
            async with session.get(member.display_avatar.url) as resp:
                avatar_data = io.BytesIO(await resp.read())
        avatar = Image.open(avatar_data).convert("RGBA").resize((AVATAR_SIZE, AVATAR_SIZE))
        mask = Image.new("L", (AVATAR_SIZE, AVATAR_SIZE), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, AVATAR_SIZE, AVATAR_SIZE), fill=255)
        avatar_x = (background.width // 2) - (AVATAR_SIZE // 2) 
        avatar_y = 50 
        background.paste(avatar, (avatar_x, avatar_y), mask)
        nom_text = member.display_name
        bbox_nom = draw.textbbox((0, 0), nom_text, font=FONT_NOM)
        nom_width = bbox_nom[2] - bbox_nom[0]
        nom_x_base = (background.width - nom_width) // 2
        nom_y_base = (background.height // 2) + 10 
        text_y_offset = -bbox_nom[1] 
        nom_y_final = nom_y_base + text_y_offset
        GLOW_DIRECTIONS_UNITS = [
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (0.707, 0.707), (-0.707, 0.707), (0.707, -0.707), (-0.707, -0.707)
        ]
        def draw_centered_glow(draw_context, text, font, x, y, radius, color):
            for iteration in range(1, GLOW_ITERATIONS + 1):
                scale = radius * (iteration / GLOW_ITERATIONS)
                for dx_unit, dy_unit in GLOW_DIRECTIONS_UNITS:
                    offset_x = dx_unit * scale
                    offset_y = dy_unit * scale
                    draw_context.text((x + offset_x, y + offset_y), text, font=font, fill=color)
        draw_centered_glow(
            draw, nom_text, FONT_NOM, 
            nom_x_base, nom_y_final, 
            GLOW_RADIUS_SINGLE, GLOW_COLOR_SINGLE
        )
        offsets = [
            (OUTLINE_THICKNESS, 0), (-OUTLINE_THICKNESS, 0), (0, OUTLINE_THICKNESS), (0, -OUTLINE_THICKNESS),
            (OUTLINE_THICKNESS, OUTLINE_THICKNESS), (-OUTLINE_THICKNESS, OUTLINE_THICKNESS),
            (OUTLINE_THICKNESS, -OUTLINE_THICKNESS), (-OUTLINE_THICKNESS, -OUTLINE_THICKNESS),
            (OUTLINE_THICKNESS // 2, OUTLINE_THICKNESS), (-OUTLINE_THICKNESS // 2, OUTLINE_THICKNESS),
            (OUTLINE_THICKNESS, OUTLINE_THICKNESS // 2), (-OUTLINE_THICKNESS, OUTLINE_THICKNESS // 2),
        ]
        for dx, dy in offsets:
            draw.text(
                (nom_x_base + dx, nom_y_final + dy), 
                nom_text, 
                font=FONT_NOM, 
                fill=OUTLINE_COLOR_DARK_RED 
            )
        draw.text(
            (nom_x_base, nom_y_final), 
            nom_text, 
            font=FONT_NOM, 
            fill=TEXT_COLOR_FILL
        )
        buffer_final = io.BytesIO()
        background.save(buffer_final, format="PNG")
        buffer_final.seek(0)
        return discord.File(fp=buffer_final, filename="welcome_banner.png")
    except Exception as e:
        print(f"Erreur critique lors de la génération de la bannière: {e}")
        return None
# ----------------------------------------------------

class ConnexionCog(commands.Cog, name="Connexion"):
    def __init__(self, bot):
        self.bot = bot
        # Enregistre la vue persistante
        self.bot.add_view(ConnexionView())

    # === MESSAGE STATIQUE DANS #connexion ===
    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        channel_name = SALON_CONNEXION_NAME
        guild = self.bot.guilds[0] if self.bot.guilds else None
        if not guild: return
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if not channel: return
        
        # Vérifie si le message est déjà là
        async for msg in channel.history(limit=20):
            if msg.author == self.bot.user and msg.components:
                return # Message déjà envoyé avec le bouton

        embed = discord.Embed(
            title="🔐 Connexion à DH²",
            description=(
                "Bienvenue sur **DH²**, ton assistant Clash Royale !\n\n"
                "Pour lier ton compte Clash Royale à ton profil Discord :\n"
                "1️⃣ Clique sur le bouton **Connexion** ci-dessous.\n"
                "2️⃣ Entre ton **tag Clash Royale** (ex: `#9LPJQ2YY`).\n"
                "3️⃣ Une fois validé, tu pourras utiliser `/profile` et `/clan` librement.\n\n"
                "⚠️ *Ton tag reste privé et ne sera jamais affiché publiquement.*"
            ),
            color=0x00A2E8
        )
        embed.set_thumbnail(url="https://cdn.royaleapi.com/static/img/badge/icon.png")
        embed.set_footer(text="DH² - Connecté au royaume de Clash Royale 🛡️")
        view = ConnexionView()
        await channel.send(embed=embed, view=view)


    # === MESSAGE DE BIENVENUE DYNAMIQUE DANS #arrivée ===
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot: return
        channel = discord.utils.get(member.guild.text_channels, name=SALON_ARRIVEE_NAME)
        if channel is None: return 
        
        file = await generate_welcome_banner(member)

        if file:
            embed = discord.Embed(
                title=f"🎉 Nouveau membre dans l'arène !",
                description=(
                    f"Salut {member.mention}, sois le bienvenu sur **{member.guild.name}** !\n\n"
                    f"N'oublie pas de te connecter à ton compte Clash Royale dans le salon <#{SALON_CONNEXION_ID}>."
                ),
                color=discord.Color.gold()
            )
            embed.set_image(url="attachment://welcome_banner.png")
            embed.set_footer(text="Généré par DH²")
            
            # Note: Remplacez <URL_VERS_SALON_CONNEXION> par l'ID réel du salon dans votre serveur si possible, ou laissez ainsi.
            await channel.send(embed=embed, file=file)
        else:
            await channel.send(f"Bienvenue, {member.mention} sur le serveur **{member.guild.name}** ! 👋")


async def setup(bot):
    await bot.add_cog(ConnexionCog(bot))