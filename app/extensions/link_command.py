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
from util.embed_lib import SuccessfullyUnlinkedEmbed, InsufficientPermissionsEmbed


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


# Add link and unlink commands to bot
async def setup(bot: commands.Bot):
    logging.debug("Adding cog: LinkCommand")
    await bot.add_cog(LinkCommand(bot))
    logging.debug("Adding Cog: UnlinkCommand")
    await bot.add_cog(UnlinkCommand(bot))
