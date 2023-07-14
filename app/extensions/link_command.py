"""
These 2 cogs handle all the logic and functionality
to link/unlink discord and hypixel players.

Commands:
- /link <username/uuid>
This command will attempt to create a link between
a discord member and a player on hypixel.
- /unlink
This command will attempt to unlink an existing link

Author: illyum
"""

import discord
import logging
import requests

from typing import Union
from util.mcign import MCIGN
from discord import app_commands
from discord.ext import commands
from util import local, embed_lib
from util.command_helper import ensure_bot_perms
from util.embed_lib import SuccessfullyUnlinkedEmbed, InsufficientPermissionsEmbed, InvalidArgumentEmbed, \
    SuccessfullyForceUnlinkedEmbed

how_to_link = discord.Embed(colour=discord.Colour(0xfa1195))
how_to_link.add_field(
    name="How to link your discord account on hypixel:",
    value="`#1` Go to any game lobby and right click on your head in your hotbar.\n"
          "`#2` In the GUI, select 'Social Media'. It looks like a twitter head.\n"
          "`#3` Left click the discord head in the new popup.\n"
          "`#4` Copy your discord username#number and paste in game chat!"
          "`#5` Come back and run `/link` again!")


class LinkCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.local_data: local.LocalDataSingleton = local.LOCAL_DATA

    def get_player(self, player_id) -> Union[local._CacheEntry | None]:
        player = self.local_data.uuid_cache.get_entry(player_id)
        if player is None:
            player = MCIGN(player_id)
            self.local_data.uuid_cache.add_entry(player.uuid, player.name)
        return player

    @app_commands.command(name="link", description="Link your discord and minecraft account")
    @app_commands.describe(username="Your minecraft username to link!")
    async def link(self, interaction: discord.Interaction, username: str):
        await interaction.response.defer()

        # Make sure their account isn't already linked
        link = self.local_data.discord_link.get_link(interaction.user.id)
        if link is not None:  # AKA Their account IS linked
            already_linked_embed = discord.Embed(colour=discord.Colour(0x820529))
            already_linked_embed.description = "You've already linked your account! If you need to unlink your discord " \
                                               "and minecraft account, use `/unlink`"
            await interaction.edit_original_response(embed=already_linked_embed)
            return

        # Get hypixel player data
        key = self.local_data.config.get("bot", "api_key")
        uuid = MCIGN(player_id=username).uuid
        player_data = requests.get("https://api.hypixel.net/player?key={}&uuid={}".format(key, uuid)).json()
        hypixel_discord_record = player_data.get('player', {}).get("socialMedia", {}).get("links", {})\
            .get("DISCORD", None)
        if hypixel_discord_record is None:
            logging.error(f"[linking] Player {username} does not contain hypixel discord record")
            await interaction.edit_original_response(embed=how_to_link)
            return

        # Check if the interaction user matches hypixel's records
        senders_discord_username = f"{interaction.user.name}#{interaction.user.discriminator}"
        if senders_discord_username != hypixel_discord_record:
            await interaction.edit_original_response(embed=how_to_link)
            return

        # Everything worked out! Add the link
        discord_id = interaction.user.id
        self.local_data.discord_link.register_link(uuid, discord_id, senders_discord_username)
        successful_embed = embed_lib.SuccessfullyLinkedEmbed(username, interaction.user)
        await interaction.edit_original_response(embed=successful_embed)


class UnlinkCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.local_data: local.LocalDataSingleton = local.LOCAL_DATA

    @app_commands.command(name="unlink", description="Unlink your discord and minecraft account")
    async def unlink(self, interaction: discord.Interaction):
        await interaction.response.defer()

        link = self.local_data.discord_link.get_link(interaction.user.id)
        if link is None:  # AKA Their account IS linked
            response_embed = discord.Embed(colour=discord.Colour(embed_lib.to_hex("#eb4034")))
            response_embed.description = "Your account is not linked!"
            await interaction.edit_original_response(embed=response_embed)
            return

        if not link.discord_id == interaction.user.id:
            await interaction.edit_original_response(embed=InsufficientPermissionsEmbed())
            return

        self.local_data.discord_link.remove_link(link.row_id, link.uuid)
        await interaction.edit_original_response(embed=SuccessfullyUnlinkedEmbed(interaction.user.mention))


class ForceLinkCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.local_data: local.LocalDataSingleton = local.LOCAL_DATA

    def get_player(self, player_id):
        player = self.local_data.uuid_cache.get_entry(player_id)
        if player is None:
            player = MCIGN(player_id)
            local.LOCAL_DATA.uuid_cache.add_entry(player.uuid, player.name)
        return player

    @app_commands.command(name="forcelink", description="Force Link a discord user and ign/uuid")
    @app_commands.describe(discord_id="Discord ID associated with minecraft username")
    @app_commands.describe(player="Uuid/Name of player to force link")
    async def force_link_command(self, interaction: discord.Interaction, discord_id: str, player: str):
        await interaction.response.defer()
        is_allowed = await ensure_bot_perms(interaction, send_denied_response=True)
        if not is_allowed:
            return

        try:
            discord_id = int(discord_id)
        except Exception as e:
            await interaction.edit_original_response(embed=embed_lib.InvalidArgumentEmbed())

        mojang_player = MCIGN(player)

        # Make sure their account isn't already linked
        server_id = int(local.LOCAL_DATA.config.get("bot", "server_id"))
        force_linked_discord_user = self.bot.get_guild(server_id).get_member(discord_id)
        if force_linked_discord_user is None:
            await interaction.edit_original_response(embed=embed_lib.InvalidArgumentEmbed())
        link = local.LOCAL_DATA.discord_link.get_link(discord_id)
        if link is not None:  # AKA Their account IS linked
            already_linked_embed = discord.Embed(colour=discord.Colour(0x820529))
            already_linked_embed.description = "This account is already linked"
            await interaction.edit_original_response(embed=already_linked_embed)
            return

        # Make API call to make sure username is linked to a valid Mojang account
        if mojang_player.uuid is None or mojang_player.name is None:
            await interaction.edit_original_response(embed=embed_lib.InvalidMojangUserEmbed(player=player))
            return

        # Bypass api security check
        forced_discord_user_discrim = f"{force_linked_discord_user.name}#{force_linked_discord_user.discriminator}"
        local.LOCAL_DATA.discord_link.register_link(mojang_player.uuid, discord_id, forced_discord_user_discrim)
        successful_embed = embed_lib.SuccessfullyForceLinkedEmbed(mojang_player.name, force_linked_discord_user)
        await interaction.edit_original_response(embed=successful_embed)


class ForceUnlinkCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.local_data: local.LocalDataSingleton = local.LOCAL_DATA

    def get_player(self, player_id):
        player = self.local_data.uuid_cache.get_entry(player_id)
        if player is None:
            player = MCIGN(player_id)
            local.LOCAL_DATA.uuid_cache.add_entry(player.uuid, player.name)
        return player

    @app_commands.command(name="forceunlink", description="Force Unlink a discord user and ign/uuid")
    @app_commands.describe(id="Discord ID or UUID of a player to remove")
    async def force_unlink(self, interaction: discord.Interaction, id: str):
        await interaction.response.defer()
        is_allowed = await ensure_bot_perms(interaction, send_denied_response=True)
        if not is_allowed:
            return

        link = self.local_data.discord_link.get_link(id)
        if link is None:
            await interaction.edit_original_response(embed=InvalidArgumentEmbed())
            return

        self.local_data.discord_link.remove_link(link.uuid)
        await interaction.edit_original_response(embed=SuccessfullyForceUnlinkedEmbed(link.discord_username))


# Add link and unlink commands to bot
async def setup(bot: commands.Bot):
    logging.debug("Adding Cog: LinkCommand")
    await bot.add_cog(LinkCommand(bot))
    logging.debug("Adding Cog: UnlinkCommand")
    await bot.add_cog(UnlinkCommand(bot))
    logging.debug("Adding Cog: ForceLinkCommand")
    await bot.add_cog(ForceLinkCommand(bot))
    logging.debug("Adding Cog: ForceUnlinkCommand")
    await bot.add_cog(ForceUnlinkCommand(bot))
