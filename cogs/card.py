# cogs/card.py
import json
import os
from discord.ext import commands
from discord import app_commands
import discord
from cr_api import CRClient, CRApiError


class CardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cr = CRClient()
        self.cards_data = self.load_cards_data()

    # -------------------------------
    # 🔹 Chargement des données locales
    # -------------------------------
    def load_cards_data(self):
        """Charge les données depuis cartes_data.json et indexe par nom FR, EN et alias."""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(base_dir, "data", "cartes_data.json")
        cards = {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for c in data:
                    # Indexe par nom FR, EN et alias
                    keys = {
                        c["nom_fr"].lower(),
                        c["nom_en"].lower(),
                        c["alias"].lower()
                    }
                    for k in keys:
                        cards[k] = c
                print(f"✅ {len(data)} cartes chargées avec alias depuis cartes_data.json")
        except Exception as e:
            print(f"⚠️ Erreur de chargement du fichier cartes_data.json : {e}")

        return cards

    # -------------------------------
    # 🔹 Auto-complétion Discord
    # -------------------------------
    async def card_autocomplete(self, interaction: discord.Interaction, current: str):
        """Suggestions FR, EN et alias pour la commande /carte"""
        current_lower = current.lower()
        results = []

        added = set()
        for _, card in self.cards_data.items():
            nom_fr = card["nom_fr"]
            nom_en = card["nom_en"]
            alias = card["alias"]

            # Crée une ligne d'affichage
            display = f"{nom_fr} ({nom_en})"
            if current_lower in nom_fr.lower() or current_lower in nom_en.lower() or current_lower in alias.lower():
                if display not in added:
                    results.append(
                        app_commands.Choice(name=f"{display} [{alias}]", value=nom_fr)
                    )
                    added.add(display)

            if len(results) >= 25:
                break

        return results

    # -------------------------------
    # 🔹 Slash Command : /carte
    # -------------------------------
    @app_commands.command(name="carte", description="Affiche les informations d'une carte Clash Royale (FR, EN ou alias)")
    @app_commands.describe(nom="Nom français, anglais ou alias de la carte (ex: Boule de feu / Fireball / BdF)")
    @app_commands.autocomplete(nom=card_autocomplete)
    async def carte(self, interaction: discord.Interaction, nom: str):
        await interaction.response.defer()

        nom_lower = nom.lower()
        card_info = self.cards_data.get(nom_lower)

        # Recherche tolérante si l'utilisateur tape un nom proche
        if not card_info:
            for key, c in self.cards_data.items():
                if nom_lower in [c["nom_fr"].lower(), c["nom_en"].lower(), c["alias"].lower()]:
                    card_info = c
                    break

        if not card_info:
            await interaction.followup.send(
                f"❌ Carte « {nom} » introuvable dans la base locale.", ephemeral=True
            )
            return

        # Récupération image API
        try:
            card_api = await self.cr.get_card(card_info["nom_en"])
        except CRApiError:
            card_api = {}

        embed = discord.Embed(
            title=f"{card_info['nom_fr']} ({card_info['nom_en']})",
            color=0x00A2E8,
        )
        embed.add_field(name="💧 Élixir", value=str(card_info["cout_elixir"]), inline=True)
        embed.add_field(name="🏅 Rareté", value=card_info["rarete"], inline=True)
        embed.add_field(name="⚔️ Type", value=card_info["type"], inline=True)
        embed.add_field(
            name="🔄 Évolution", value="Oui ✅" if card_info["evolution"] else "Coming Soon ⌛" if card_info["evolution"] == "coming soon" else "Non ❌", inline=True
        )
        embed.add_field(name="🔣 Alias", value=card_info["alias"], inline=True)

        icon_url = card_api.get("iconUrls", {}).get("medium")
        if icon_url:
            embed.set_thumbnail(url=icon_url)
        else:
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/emojis/1189420413190334555.webp?size=96&quality=lossless"
            )

        await interaction.followup.send(embed=embed)

    async def cog_unload(self):
        await self.cr.close()


async def setup(bot):
    await bot.add_cog(CardCog(bot))
