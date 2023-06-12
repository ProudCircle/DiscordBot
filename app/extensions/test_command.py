"""
This cog handles all the logic and functionality
for the test command and subcommands.

Commands:
- /test api-key (Admin Only)
This command test the api key and
returns an embed full of data

Author: illyum
"""

import time
import discord
import logging
import requests

from util import local

from discord import app_commands
from discord.ext import commands

from util.command_helper import ensure_bot_perms


class TestCommandsCog(commands.GroupCog, name="test"):
    """
    A custom commands cog for testing purposes.
    """

    def __init__(self, bot: commands.Bot) -> None:
        """
        Initializes the TestCommandsCog instance.

        Parameters:
            bot (commands.Bot): The instance of the bot.
        """
        super().__init__()
        self.bot = bot
        self.local_data: local.LocalDataSingleton = local.LOCAL_DATA

    @app_commands.command(name="api-key", description="Tests the API Key and response time (Admin Only)")
    async def my_sub_command_1(self, interaction: discord.Interaction) -> None:
        """
        Tests the API Key and response time.

        Parameters:
            self
            interaction (discord.Interaction): The interaction object representing the user's interaction.

        Returns:
            None
        """
        await interaction.response.defer(ephemeral=True)
        is_allowed = await ensure_bot_perms(interaction, send_denied_response=True)
        if not is_allowed:
            return

        key = self.local_data.config.get("bot", "api_key")
        test_url = f"https://api.hypixel.net/key?key={key}"
        logging.debug("Testing API key...")
        start_time = time.time()
        request = requests.get(test_url)
        elapsed_time = int((time.time() - start_time) * 1000)
        logging.debug("API Test response received")
        headers = request.headers
        content = request.json()
        content_success = content.get('success', False)

        header_details = ""
        skips = ["Set-Cookie", "CF-RAY"]
        for header, value in headers.items():
            if header in skips:
                continue
            header_details = header_details + f"{header}: `{value}` \n"

        header_details = header_details + f"\nGrab Success Status: `{content_success}`"

        headers_embed = discord.Embed()
        headers_embed.colour = discord.Colour.from_str("#ffffff")
        headers_embed.add_field(name="Status Code: ", value=f"`{request.status_code}`", inline=False)
        headers_embed.add_field(name="Elapsed Time: ", value=f"`{elapsed_time}ms`", inline=False)
        headers_embed.add_field(name="Headers: ", value=f"{header_details}", inline=True)

        if not content_success:
            headers_embed.add_field(name="Failed Success", value=f"Cause: `{content.get('cause', None)}`", inline=False)

        await interaction.edit_original_response(embed=headers_embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TestCommandsCog(bot))
