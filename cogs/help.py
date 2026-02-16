# cogs/help.py
import discord
from discord import app_commands
from discord.ext import commands


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Affiche la liste des commandes du bot DH²")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📘 Aide - DH²",
            description="Voici la liste complète des commandes disponibles sur **DH²**, ton assistant Clash Royale.",
            color=0x00A2E8
        )
        embed.set_thumbnail(url="attachment://logo_serv.png")
        embed.set_footer(text="Développé par DAHORD 👑")

        # --- Section 1 : Connexion ---
        embed.add_field(
            name="🔐 Connexion",
            value=(
                "**Salon :** `#connexion`\n"
                "→ Clique sur le **bouton Connexion** et entre ton identifiant Clash Royale (`#TAG`).\n"
                "Cela permet au bot de lier ton compte à ton profil DH².\n\n"
                "\n"
            ),
            inline=False
        )

        # --- Section 2 : Profil ---
        embed.add_field(
            name="\n👤 Profil",
            value=(
                "`/profile info` → Affiche ton profil Clash Royale lié\n"
                "`/profile info <tag>` → Affiche le profil d’un joueur spécifique\n"
                "**Infos affichées :** nom, clan, trophées, niveau de roi, victoires 3 couronnes, % victoires\n"
                "`/profile battles` → Affiche tes 5 dernières batailles\n"
                "`/profile battles <tag>` → Affiche les 5 dernières batailles d’un joueur spécifique\n"
                "**Infos affichées :** mode de jeu, résultat, adversaire\n\n"
                "\n"
            ),
            inline=False
        )

        # --- Section 3 : Clan ---
        embed.add_field(
            name="\n🛡️ Clan",
            value=(
                "`/clan info` → Affiche ton clan actuel\n"
                "`/clan info <tag>` → Affiche le clan correspondant au tag\n"
                "**Infos affichées :** nom, tag, description, membres, trophées, guerre des clans\n"
                "`/clan donations` → Affiche les 25 premiers membres les plus donnateurs de ton clan\n"
                "`/clan donations <tag>` → Affiche les 25 premiers membres les plus donnateurs d'un clan spécifique\n"
                "**Infos affichées :** position, nom, statut, nombre de dons\n"
                "`/clan war-rankings` → Affiche les infos de la guerre des clans en cours de ton clan\n"
                "`/clan war-rankings <tag>` → Affiche les infos de la guerre des clans d'un clan spécifique\n"
                "**Infos affichées :** rang, score, participation des membres\n\n"
                "\n"
            ),
            inline=False
        )

        # --- Section 4 : Cartes ---
        embed.add_field(
            name="\n🃏 Cartes",
            value=(
                "`/carte <nom>` → Affiche les infos d’une carte Clash Royale\n"
                "🔎 Recherche possible via :\n"
                "- **Nom FR** (`Boule de feu`)\n"
                "- **Nom EN** (`Fireball`)\n"
                "- **Alias** (`BDF`)\n\n"
                "\n"
            ),
            inline=False
        )

        # --- Section 5 : Divers ---
        embed.add_field(
            name="\n⚙️ Autres commandes",
            value=(
                "`/help` → Affiche cette aide\n"
                "`/update` *(si activé)* → Met à jour les données locales du bot (cartes, clans, etc.)"
            ),
            inline=False
        )

        # Bouton vers support / crédits
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="🔗 Connexion",
                style=discord.ButtonStyle.blurple, # bouton bleu mais ne marche pas en lien
                url="https://discord.com/channels/1433100002917355593/1433100944618553425",
            )
        )

        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
