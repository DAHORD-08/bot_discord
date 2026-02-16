# cogs/profile.py
from discord.ext import commands
import discord
from discord import app_commands
from cr_api import CRClient, CRApiError
# --- Import Corrigé ---
from db import get_user_tag # Utilise la DB asynchrone
import os
# json et la fonction get_user_tag_from_json sont supprimés

# --- FONCTION D'AIDE : Traduction des Types de Combat ---
def translate_battle_type(api_type: str) -> str:
    """Traduit les types de combat bruts de l'API en français clair."""
    translations = {
        "PvP": "1v1 Ladder (No Trophées)", "ladder": "Ladder Classique (Trophées)",
        "riverRace": "Guerre des Clans (Course)", "riverRacePvP": "1v1 Guerre des Clans (Course)",
        "riverRaceDuelColosseum": "Duel Guerre des Clans (Course)", "boatBattle": "Guerre des Clans (Bateau)",
        "challenge": "Défi (Global ou Événement)", "tournament": "Tournoi Privé", 
        "friendly": "1v1 Combat Amical (Classique)", "twoVsTwo": "2v2 Combat Amical",
        "clanMate": "Combat de Membres de Clan", "tutorial": "Tutoriel / Entraînement",
        "pathOfLegend": "1v1 Classé (Ligues)", "draft": "Défi Tirage",
        "trail": "1v1 Ladder (Trophées)", "trainingCamp": "Camp d'Entraînement (Bots)",
        "unknown": "Type Inconnu"
    }
    return translations.get(api_type, api_type.title())
# -------------------------------------------------------------------

# --- FONCTION D'AIDE : Formatage du Profil (inchangée) ---
def format_profile(p: dict) -> str:
    # ... (Votre code de formatage de profil) ...
    name = p.get("name", "—"); tag = p.get("tag", "—")
    clan = p.get("clan", {}).get("name", "—"); clan_tag = p.get("clan", {}).get("tag", "—")
    level = p.get("expLevel", "—"); exp = p.get("expPoints", "—")
    if level == 70: exp = "Max"
    trophies = p.get("trophies", "—"); wins = p.get("wins", 0)
    total_battles = p.get("battleCount", 0); losses = p.get("losses", 0)
    draws = p.get("draws", 0); best_trophies = p.get("bestTrophies", "—")
    win_rate = (wins / total_battles * 100) if total_battles > 0 else 0
    three_crown_wins = p.get("threeCrownWins", 0)
    league_stats = p.get("leagueStatistics", {}); current_pol = league_stats.get("currentSeason", {})
    best_pol = league_stats.get("bestSeason", {}); best_pol_score = best_pol.get("trophies", "—")
    best_pol_rank = best_pol.get("rank")
    rank_display = f" (Rang #{best_pol_rank:,})" if best_pol_rank and best_pol_rank > 0 else ""
    text = (
        f"**🔖 Tag :** `{tag}`\n"
        f"**🌟 Niveau :** {level} (`Exp : {exp}`)\n"
        f"**🛡️ Clan :** {clan} (`{clan_tag}`)\n\n"
        "__**Statistiques de Combat Générales**__\n"
        f"**🏆 Trophées Classiques :** {trophies}\n"
        f"**🏅 Record de Saison (PoL) :** {best_pol_score} 🏆 {rank_display}\n"
        f"**⚔️ Victoires :** {wins} | **3 Couronnes :** {three_crown_wins}\n"
        f"**❌ Défaites/Nuls :** {losses}/{draws}\n"
        f"**📊 Taux de Victoire :** {win_rate:.1f}%\n"
    )
    return text
# -----------------------------------------------


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- DÉCLARATION DU GROUPE DE COMMANDES /profile ---
    profile_group = app_commands.Group(name="profile", description="Commandes liées au profil Clash Royale.")

    @profile_group.command(name="info", description="Affiche le profil principal du joueur connecté ou du tag indiqué.")
    @app_commands.describe(tag="Tag du joueur (ex: #AB12). Si omis, utilise ton compte connecté.")
    async def profile_info(self, interaction: discord.Interaction, tag: str = None):
        
        # 1. DEFER IMMÉDIAT (Corrige l'erreur 404 Discord sur timeout)
        await interaction.response.defer(ephemeral=True) 
        
        target_tag = None
        if tag:
            target_tag = tag.strip().replace("#", "").upper()
        else:
            # 2. MIGRATION DB (Lecture asynchrone)
            user_tag = await get_user_tag(interaction.user.id)
            if not user_tag:
                await interaction.followup.send(
                    "⚠️ Tu n'as pas encore lié ton compte Clash Royale.\n"
                    "Va dans le salon **#connexion** et clique sur le bouton **Connexion**.",
                    ephemeral=True
                )
                return
            target_tag = user_tag.replace("#", "").upper()

        try:
            # 3. MIGRATION API (Utilisation de 'async with')
            async with CRClient() as cr:
                player = await cr.get_player(target_tag)
                
        except CRApiError as e:
            await interaction.followup.send(f"❌ Erreur Clash Royale : {e}", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Profil de {player.get('name', '—')} (`#{target_tag}`)",
            color=0x00A2E8
        )
        embed.description = format_profile(player)
        
        badge_url = player.get("badgeUrls", {}).get("large")
        if badge_url:
            embed.set_thumbnail(url=badge_url)
            
        embed.set_footer(text="Utilise /profile battles pour plus d'infos.")

        # Envoi en non-éphémère pour permettre le partage
        await interaction.followup.send(embed=embed, ephemeral=False)

    # --- SOUS-COMMANDE : /profile battles ---
    @profile_group.command(name="battles", description="Affiche l'historique des 5 derniers combats du joueur.")
    @app_commands.describe(tag="Tag du joueur (optionnel).")
    async def profile_battles(self, interaction: discord.Interaction, tag: str = None):
        
        # 1. DEFER IMMÉDIAT
        await interaction.response.defer(ephemeral=True) 
        
        target_tag = None
        if tag:
            target_tag = tag.strip().replace("#", "").upper()
        else:
            # 2. MIGRATION DB
            user_tag = await get_user_tag(interaction.user.id)
            if not user_tag:
                 await interaction.followup.send("⚠️ Tu dois lier ton compte ou fournir un tag pour voir l'historique.", ephemeral=True)
                 return
            target_tag = user_tag

        target_tag = target_tag.replace("#", "").upper()

        try:
            # 3. MIGRATION API
            async with CRClient() as cr:
                battle_log = await cr.get_battle_log(target_tag)
                
        except CRApiError as e:
            await interaction.followup.send(f"❌ Erreur Clash Royale : {e}", ephemeral=True)
            return

        if not battle_log:
            await interaction.followup.send("ℹ️ Aucun combat récent trouvé pour ce joueur.", ephemeral=True)
            return

        battle_summaries = []
        for battle in battle_log[:5]:
            if not battle.get("team") or not battle.get("opponent"): continue
            
            api_type = battle.get("type", "unknown"); battle_type_display = translate_battle_type(api_type) 
            team_member = battle["team"][0]; opponent_member = battle["opponent"][0]
            team_crowns = team_member.get("crowns", 0); opponent_crowns = opponent_member.get("crowns", 0)
            
            result_icon = "❓"
            if team_crowns > opponent_crowns: result_icon = "✅ Victoire"
            elif team_crowns < opponent_crowns: result_icon = "❌ Défaite"
            elif team_crowns == opponent_crowns and team_crowns > 0: result_icon = "🤝 Égalité"
            elif team_crowns == 0 and opponent_crowns == 0: result_icon = "🚫 Null"

            summary = (
                f"**{result_icon}** ({team_crowns}-{opponent_crowns} 👑) | "
                f"Type : *{battle_type_display}* | " 
                f"Adversaire : **{opponent_member.get('name', 'Anonyme')}**"
            )
            battle_summaries.append(summary)

        embed = discord.Embed(
            title="⚔️ Historique des 5 Derniers Combats",
            description="\n\n".join(battle_summaries),
            color=0x8A2BE2
        )
        embed.set_footer(text=f"Données officielles Clash Royale © Supercell pour #{target_tag}")
        
        await interaction.followup.send(embed=embed, ephemeral=False)


async def setup(bot):
    await bot.add_cog(Profile(bot))