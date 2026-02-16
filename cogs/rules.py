# cogs/rules.py

import discord
import logging
from discord.ext import commands
from discord.utils import get

logger = logging.getLogger("dh2.rules")

# ID du salon de règles spécifié (utilisé pour la vérification de la réaction)
RULES_CHANNEL_ID = 1435686509314441276
# Nom du rôle à attribuer après acceptation des règles
ROLE_VERIFIE_NAME = "MembreDH2" 
# Emoji de vérification
VERIFY_EMOJI = "✅" 

class Rules(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rules_message_sent = False
        self.rules_message_id = None # Pour stocker l'ID du message des règles

    def create_rules_embed(self) -> discord.Embed:
        """Crée l'Embed contenant le contenu des règles."""
        
        # --- Contenu des règles ---
        rules_content = (
            "Bienvenue dans l'arène de **DH²** ! Pour garantir une expérience positive à tous, "
            "veuillez lire et respecter les règles suivantes. Le non-respect peut entraîner des sanctions."
        )

        embed = discord.Embed(
            title="📜 RÈGLES DU CLAN/SERVEUR",
            description=rules_content,
            color=discord.Color.red()
        )
        
        # --- Règles détaillées (GARDÉES IDENTIQUES) ---
        
        embed.add_field(
            name="1. Respect & Conduite",
            value=(
                "**- Respect :** Soyez courtois envers tous les membres et le staff.\n"
                "**- Contenu :** Pas d'insultes, de harcèlement, de discours haineux ou de contenu inapproprié (NSFW, Gore, etc.).\n"
                "**- Identité :** Votre nom d'utilisateur et votre avatar ne doivent pas être offensants."
            ),
            inline=False
        )
        
        embed.add_field(
            name="2. Salons & Thèmes",
            value=(
                "**- Thème :** Les discussions doivent rester centrées sur Clash Royale, la communauté et le clan.\n"
                "**- Bot :** Utilisez les commandes du bot (`/profile`, `/clan`, etc.) uniquement dans le salon dédié (`#commandes-dh™`).\n"
                "**- Spam :** Évitez le spam, les messages répétitifs ou la surutilisation de majuscules."
            ),
            inline=False
        )

        embed.add_field(
            name="3. Règle du Clan",
            value=(
                "**- Participation :** La participation à la **Guerre des Clans (Course Fluviale)** est **obligatoire**.\n"
                "**- Dons :** Contribuez aux dons pour aider le clan (objectif hebdomadaire indicatif : 500+).\n"
                "**- Inactivité :** Tout membre inactif sans prévenir sera exclu après une semaine."
            ),
            inline=False
        )
        
        embed.add_field(
            name="4. Connexion DH²",
            value=(
                "Vous êtes invité à lier votre compte Clash Royale via le salon **#connexion** et la commande `/connexion` "
                "afin de faciliter la gestion et de profiter des commandes personnalisées."
            ),
            inline=False
        )
        
        embed.set_footer(
            text="En restant sur ce serveur, vous acceptez ces règles. Dernière mise à jour au démarrage du bot."
        )
        
        # --- NOUVELLE SECTION D'ACCEPTATION ---
        embed.add_field(
            name="✅ Acceptation et Accès",
            value=(
                f"Pour obtenir l'accès complet au serveur et débloquer tous les salons, "
                f"veuillez **réagir à ce message avec l'émoji {VERIFY_EMOJI}**."
            ),
            inline=False
        )
        
        embed.set_footer(
            text="En cliquant sur l'émoji, vous acceptez ces règles. Dernière mise à jour au démarrage du bot."
        )

        return embed


    @commands.Cog.listener()
    async def on_ready(self):
        # Empêche l'exécution multiple si le bot se reconnecte
        if self.rules_message_sent:
            return

        channel = self.bot.get_channel(RULES_CHANNEL_ID)
        if not channel:
            logger.error(f"❌ [RÈGLES] Salon des règles (ID: {RULES_CHANNEL_ID}) introuvable.")
            return

        try:
            # Tente de récupérer le message existant du bot (limite de 10 messages)
            messages = [msg async for msg in channel.history(limit=10, oldest_first=False)]
            
            # Recherche le message des règles envoyé par le bot (via son titre d'embed)
            bot_message = discord.utils.get(messages, author=self.bot, embed=lambda e: e.title == "📜 RÈGLES DU CLAN/SERVEUR")

            if bot_message:
                # CAS 1 : Message trouvé. On l'utilise et on s'assure qu'il y a la réaction.
                self.rules_message_id = bot_message.id
                # Ajout de la réaction au cas où elle aurait été retirée
                await bot_message.add_reaction(VERIFY_EMOJI) 
                logger.info(f"✅ [RÈGLES] Message trouvé (ID: {self.rules_message_id}).")
            
            elif not messages:
                # CAS 2 : Salon vide (0 message). On envoie le nouveau message.
                embed = self.create_rules_embed()
                message = await channel.send(embed=embed)
                await message.add_reaction(VERIFY_EMOJI)
                self.rules_message_id = message.id
                logger.info(f"✅ [RÈGLES] Nouveau message envoyé et ID stocké : {self.rules_message_id}")
            
            else:
                # CAS 3 : Salon non vide, mais le message n'est pas trouvé (pour respecter votre contrainte)
                logger.warning(f"⚠️ [RÈGLES] Salon non vide et message non trouvé. Veuillez supprimer manuellement les messages pour qu'il soit renvoyé.")
                return

            self.rules_message_sent = True

        except Exception as e:
            logger.error(f"❌ Erreur lors de la gestion du message des règles : {e}")


    # === GESTION DE LA RÉACTION POUR L'AUTO-RÔLE ===
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        
        # 1. Vérification des critères de réaction (INCHANGÉ)
        if payload.message_id != self.rules_message_id:
            return 
        if payload.user_id == self.bot.user.id:
            return 
        if str(payload.emoji) != VERIFY_EMOJI:
            # Supprime la réaction si ce n'est pas le bon émoji (INCHANGÉ)
            channel = self.bot.get_channel(payload.channel_id)
            if channel:
                message = await channel.fetch_message(payload.message_id)
                await message.remove_reaction(payload.emoji, payload.member or self.bot.get_user(payload.user_id))
            return 
        
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return 

        member = payload.member 
        
        # --- FIX : Récupérer le membre si non mis en cache (problème des nouveaux membres) ---
        if member is None:
            try:
                # On utilise fetch_member pour s'assurer d'avoir l'objet complet
                member = await guild.fetch_member(payload.user_id) 
            except discord.NotFound:
                logger.error(f"❌ [RÈGLES] Membre introuvable (ID: {payload.user_id}) malgré la réaction.")
                return
            except discord.Forbidden:
                logger.error(f"❌ [RÈGLES] Permissions insuffisantes pour récupérer le membre.")
                return
            
        if not member:
            return # Sortie si l'objet membre n'a pas pu être récupéré

        role = get(guild.roles, name=ROLE_VERIFIE_NAME)

        if not role:
            logger.error(f"❌ [RÈGLES] Le rôle '{ROLE_VERIFIE_NAME}' est introuvable sur le serveur.")
            return

        # 3. MODIFICATION : RETRAIT du rôle (Reste inchangé)
        try:
            if role in member.roles:
                
                await member.remove_roles(role, reason="Acceptation des règles et vérification.")
                
                logger.info(f"➖ Rôle '{ROLE_VERIFIE_NAME}' RETIRÉ à {member.name} suite à l'acceptation des règles.")
                    
            else:
                logger.debug(f"ℹ️ {member.name} a cliqué mais n'avait plus le rôle '{ROLE_VERIFIE_NAME}'.")
                
        except discord.Forbidden:
            # Vérifiez que le rôle du bot est PLUS HAUT que le rôle '{ROLE_VERIFIE_NAME}' dans la hiérarchie !
            logger.error(f"❌ [RÈGLES] Permissions insuffisantes pour RETIRER le rôle '{ROLE_VERIFIE_NAME}'.")
        except Exception as e:
            logger.error(f"❌ Erreur lors du retrait du rôle: {e}")


async def setup(bot):
    # Les Intents doivent être vérifiés : intents.members doit être activé, et intents.message_content est inutile ici.
    # on_raw_reaction_add fonctionne sans intents.message_content si intents.guilds est activé (default),
    # mais assurez-vous que intents.members est bien là pour que payload.member fonctionne bien !
    await bot.add_cog(Rules(bot))