# cogs/clan.py
from discord.ext import commands
from discord import app_commands
import discord
from cr_api import CRClient, CRApiError
# --- Import Corrigé (DB) ---
from db import get_user_tag # Utilise la DB asynchrone
# import os et import json supprimés car non nécessaires avec l'approche DB/API asynchrone
from typing import List, Dict, Any
from operator import itemgetter 


class Clan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- DÉCLARATION DU GROUPE DE COMMANDES /clan (Correction de l'omission) ---
    clan_group = app_commands.Group(name="clan", description="Commandes liées au clan Clash Royale.")

    async def get_clan_tag_from_user_or_arg(self, interaction: discord.Interaction, tag: str = None) -> str | None:
        """Détermine le tag du clan à partir de l'argument ou du joueur lié (via DB)."""
        # 1. Tente de récupérer le tag du clan directement à partir de l'argument
        if tag and tag.startswith("#"):
            return tag.strip("#").upper()
        # Si c'est un tag potentiel sans '#', on le normalise et le retourne
        if tag and len(tag) >= 4 and all(c.isalnum() or c in '#_.' for c in tag):
             return tag.strip("#").upper()

        # 2. Si pas de tag fourni, tente de récupérer le tag du joueur via la DB
        user_tag = await get_user_tag(interaction.user.id)
        if not user_tag:
            return None 

        try:
            # 3. Récupère les infos du joueur pour trouver son clan (via nouvelle API)
            async with CRClient() as cr:
                player = await cr.get_player(user_tag)
                
            clan_info = player.get("clan")
            if clan_info:
                return clan_info.get("tag", "").strip("#").upper()
            return None # Le joueur n'est dans aucun clan
        except Exception:
            # Échoue silencieusement si le joueur n'est pas trouvé ou s'il y a une erreur API
            return None


    @clan_group.command(name="info", description="Affiche le profil principal du clan (basé sur ton compte ou un tag).")
    @app_commands.describe(tag="Tag du clan ou du joueur (optionnel).")
    async def clan_info(self, interaction: discord.Interaction, tag: str = None):
        
        # 1. DEFER IMMÉDIAT
        await interaction.response.defer()

        clan_tag = await self.get_clan_tag_from_user_or_arg(interaction, tag)

        if not clan_tag:
            await interaction.followup.send(
                "⚠️ Tu dois lier ton compte Discord à un compte Clash Royale avec un clan, ou fournir le tag du clan (ex: `#P8UQQ9G`) ou le tag d'un membre.",
                ephemeral=True
            )
            return
            
        try:
            # 2. MIGRATION API
            async with CRClient() as cr:
                clan = await cr.get_clan(clan_tag)
                
        except CRApiError as e:
            await interaction.followup.send(f"❌ Erreur Clash Royale : {e}", ephemeral=True)
            return
        
        clan_tag_display = clan.get("tag", clan_tag) 

        # --- Embed final ---
        embed = discord.Embed(
            title=f"🛡️ {clan.get('name', '—')}",
            description=clan.get("description", "—"),
            color=0xFFD700,
        )
        embed.add_field(name="🔖 Tag", value=f"`{clan_tag_display}`", inline=True)
        embed.add_field(name="🎯 Conditions d’entrée", value=f"{clan.get('requiredTrophies', '—')} 🏆", inline=True)
        embed.add_field(name="👥 Membres", value=f"{clan.get('members', 0)}/50 👤", inline=True)
        embed.add_field(name="🏆 Trophées", value=f"{clan.get('clanScore', '—')} 🏆", inline=True)
        embed.add_field(name="⚔️ Trophées de guerre", value=f"{clan.get('clanWarTrophies', '—')} ⚔️", inline=True)
        embed.add_field(name="🌎 Localisation", value=clan.get('location', {}).get('name', '—'), inline=True)
        
        badge_url = clan.get('badgeUrls', {}).get('large')
        if badge_url:
            embed.set_thumbnail(url=badge_url)
            
        embed.set_footer(text="Utilise /clan donations ou /clan war-rankings pour plus d'infos.")

        await interaction.followup.send(embed=embed)


    # --- SOUS-COMMANDE : /clan donations ---
    @clan_group.command(name="donations", description="Affiche la liste des membres triée par dons (du plus donneur au moins donneur).")
    @app_commands.describe(tag="Tag du clan (optionnel).")
    async def clan_donations(self, interaction: discord.Interaction, tag: str = None):
        
        await interaction.response.defer()
        clan_tag = await self.get_clan_tag_from_user_or_arg(interaction, tag)

        if not clan_tag:
            await interaction.followup.send(
                "⚠️ Tu dois lier ton compte Discord à un compte Clash Royale avec un clan, ou fournir le tag du clan.",
                ephemeral=True
            )
            return

        try:
            async with CRClient() as cr:
                clan = await cr.get_clan(clan_tag)
                
        except CRApiError as e:
            await interaction.followup.send(f"❌ Erreur Clash Royale : {e}", ephemeral=True)
            return

        members = clan.get("memberList", [])
        if not members:
            await interaction.followup.send(f"ℹ️ Le clan `{clan.get('name', clan_tag)}` ne contient aucun membre.")
            return

        # Trie par donations (du plus grand au plus petit)
        sorted_members = sorted(members, key=itemgetter("donations"), reverse=True)

        rankings = []
        for i, member in enumerate(sorted_members[:25], 1): # Limité à 25 pour l'embed
            name = member.get("name", "Anonyme")
            donations = member.get("donations", 0)
            role = member.get("role", "Membre").title() 
            rankings.append(f"**{i}.** {name} *({role})*: **{donations}** 🃏")

        embed = discord.Embed(
            title=f"🥇 Classement des Dons - {clan.get('name', '—')}",
            description="\n".join(rankings),
            color=0x4CAF50 
        )
        embed.set_footer(text=f"Total des membres : {len(members)}. Affichage du Top 25.")
        
        await interaction.followup.send(embed=embed)


    # --- SOUS-COMMANDE : /clan war-rankings ---
    @clan_group.command(name="war-rankings", description="Affiche le classement de guerre actuel et les absents de la dernière guerre.")
    @app_commands.describe(tag="Tag du clan (optionnel).")
    async def clan_war_rankings(self, interaction: discord.Interaction, tag: str = None):
        
        await interaction.response.defer()

        clan_tag = await self.get_clan_tag_from_user_or_arg(interaction, tag)

        if not clan_tag:
            await interaction.followup.send("⚠️ Tu dois lier ton compte Discord à un compte Clash Royale avec un clan, ou fournir le tag du clan.", ephemeral=True)
            return

        clan_name = None 
        current_status = None
        standings = []
        participants = []
        clan: Dict[str, Any] = {}

        try:
            async with CRClient() as cr:
                clan = await cr.get_clan(clan_tag)
                clan_name = clan.get('name', clan_tag)
                
                try:
                    # 1. Tente d'obtenir la Course Fluviale ACTUELLE
                    war_data = await cr.get_current_river_race(clan_tag)
                    current_status = "Course Fluviale Actuelle"
                    standings = war_data.get('clans', [])
                    our_clan_data = next((c for c in standings if c['tag'].strip('#').upper() == clan_tag), None)
                    participants = our_clan_data.get('participants', []) if our_clan_data else []
                    
                except CRApiError as e_current:
                    # 2. Si échec (Not found), vérifie le log des guerres terminées
                    if "Not found" in str(e_current) or e_current.args[0].endswith("404: Not found: /clans/%23..."):
                        war_log_list = await cr.get_clan_war_log(clan_tag)
                        latest_war = war_log_list[0] if war_log_list else None
                        current_status = "Dernière Course Fluviale Terminée"
                        if latest_war and latest_war.get('standings'):
                            standings = latest_war['standings']
                            participants = latest_war.get('participants', [])
                        else:
                            # Ne lève plus l'erreur, mais envoie un message d'information
                            await interaction.followup.send(
                                f"ℹ️ Aucune donnée de Course Fluviale actuelle ou passée trouvée pour le clan {clan_name} (`#{clan_tag}`).",
                                ephemeral=True
                            )
                            return
                    else:
                        raise e_current

        except CRApiError as e:
            error_message = str(e)
            await interaction.followup.send(
                f"❌ **Erreur : Données de Guerre Introuvables**\n"
                f"Une erreur s'est produite lors de la connexion à l'API : `{error_message}`.",
                ephemeral=True
            )
            return

        if not standings:
            await interaction.followup.send(f"ℹ️ Le classement n'est pas disponible pour `{clan_name}`. Réessayez plus tard.", ephemeral=True)
            return

        # 1. CLASSEMENT
        try:
            sorted_standings = sorted(standings, key=itemgetter("fame"), reverse=True)
        except KeyError:
            sorted_standings = standings
        ranking_lines = []
        for i, rank_data in enumerate(sorted_standings, 1):
            rank = i; clan_name_standing = rank_data.get('name', 'Inconnu'); fame = rank_data.get('fame', 0) 
            name_display = f"**{clan_name_standing}**" if rank_data.get('tag', '').strip('#').upper() == clan_tag else clan_name_standing
            ranking_lines.append(f"{rank}. {name_display} : **{fame}** Points 🏅")
        
        # 2. PARTICIPATION
        FAME_PER_DECK = 750; MAX_DECK_SLOTS = 4
        clan_members_list: List[Dict[str, Any]] = clan.get('memberList', [])
        participants_stats: Dict[str, Any] = {p['tag'].strip("#").upper(): p for p in participants} 
        remaining_decks_list_raw = []
        for member_data in clan_members_list:
            tag_normalized = member_data['tag'].strip("#").upper(); name = member_data['name']
            stats = participants_stats.get(tag_normalized); fame_gained = 0; decks_remaining = MAX_DECK_SLOTS
            if stats:
                fame_gained = stats.get('fame', 0); decks_used_api = stats.get('decksUsed')
                if decks_used_api is not None:
                    decks_remaining = MAX_DECK_SLOTS - decks_used_api
                else:
                    estimated_decks_played = min(MAX_DECK_SLOTS, fame_gained // FAME_PER_DECK)
                    decks_remaining = MAX_DECK_SLOTS - estimated_decks_played
                decks_remaining = max(0, min(MAX_DECK_SLOTS, decks_remaining))
            if decks_remaining > 0:
                warning_emoji = " ⚠️" if fame_gained == 0 else "" 
                remaining_decks_list_raw.append(
                    f"**{name}** : {decks_remaining} deck(s) restant(s) (Points : {fame_gained} 🏅){warning_emoji}"
                )
        def robust_sort_key(x: str) -> int:
            try:
                start_index = x.find(':') + 1; end_index = x.find(' deck')
                if start_index != -1 and end_index != -1 and start_index < end_index:
                    return int(x[start_index:end_index].strip())
                return 0 
            except ValueError: return 0 
        remaining_decks_list_raw.sort(key=robust_sort_key, reverse=True)

        # GESTION MULTI-CHAMPS (Liste longue)
        MAX_SEGMENT_LENGTH = 1000; segments = []; current_segment_lines = []; current_length = 0
        total_players_in_list = len(remaining_decks_list_raw)
        for line in remaining_decks_list_raw:
            line_length = len(line) + 1
            if current_length + line_length > MAX_SEGMENT_LENGTH:
                segments.append("\n".join(current_segment_lines)); current_segment_lines = [line]; current_length = line_length
            else:
                current_segment_lines.append(line); current_length += line_length
        if current_segment_lines: segments.append("\n".join(current_segment_lines))

        # --- Construction de l'Embed ---
        embed = discord.Embed(
            title=f"⚔️ {current_status} - {clan_name}",
            description=f"**Trophées de Guerre :** {clan.get('clanWarTrophies', '—')} 🏆",
            color=0xDC143C 
        )
        embed.add_field(name="🏆 Classement des Clans (Points)", value="\n".join(ranking_lines), inline=False)
        if not segments:
            embed.add_field(name=f"⏳ Joueurs avec Decks Restants (0 membre)", value="✅ Tous les membres actifs ont joué tous leurs decks quotidiens !", inline=False)
        else:
            embed.add_field(name=f"⏳ Joueurs avec Decks Restants (1/{len(segments)} - Total : {total_players_in_list} membres)", value=segments[0], inline=False)
            for i, segment in enumerate(segments[1:], 2):
                embed.add_field(name=f"⏳ Partie ({i}/{len(segments)})", value=segment, inline=False)
        embed.set_footer(text=f"Données de l'API Clash Royale pour {current_status}. (Estimation basée sur decksUsed).")
        
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Clan(bot))