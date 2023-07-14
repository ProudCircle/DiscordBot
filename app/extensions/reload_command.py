"""
This cog handles all the logic and functionality
for the test command and subcommands.

Commands:
- /reload config (Admin Only)
This command reloads the config

Author: illyum
"""
import datetime

import discord
import logging

from util import local
from discord.ext import commands
from discord import app_commands
from util.command_helper import ensure_bot_perms


class ReloadCommandCog(commands.GroupCog, name="reload"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.local_data: local.LocalDataSingleton = local.LOCAL_DATA

    @app_commands.command(name="config", description="Reload the configuration file (Admin Only)")
    async def ping(self, interaction: discord.Interaction):
        """
        Handle the 'config' command to reload the configuration file.

        This command is only accessible to users with sufficient permissions.
        It defers the interaction response and checks if the user has the required permissions.
        If the user has sufficient permissions, the configuration file is reloaded,
        and an embed response is sent to indicate that the config has been reloaded.

        Parameters:
            interaction (discord.Interaction): The interaction from the command.

        Returns:
            None
        """
        await interaction.response.defer(ephemeral=True)
        is_allowed = await ensure_bot_perms(interaction, send_denied_response=True)
        if not is_allowed:
            return
        self.local_data.config.load_config()
        response_embed = discord.Embed(
            colour=discord.Colour.gold(),
            timestamp=datetime.datetime.now(),
            title="Config Reloaded!"
        )
        await interaction.edit_original_response(embed=response_embed)


async def setup(bot: commands.Bot):
    logging.debug("Adding cog: ReloadCommand")
    await bot.add_cog(ReloadCommandCog(bot))
