"""
This cog adds 2 commands:
- /alive
- /ping
Both of these commands are used to check the
status of the bot by responding to the command
with a message.

Author: illyum
"""

import discord
import logging

from discord import app_commands
from discord.ext import commands


class PingCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check if the bot is alive")
    async def ping(self, interaction: discord.Interaction):
        alive_embed = discord.Embed(description="Pong", colour=discord.Colour(0xeb07a6))
        await interaction.response.send_message(embed=alive_embed)

    @app_commands.command(name="alive", description="Check if the bot is alive")
    async def ping(self, interaction: discord.Interaction):
        alive_embed = discord.Embed(description="I'm alive!", colour=discord.Colour(0xeb07a6))
        await interaction.response.send_message(embed=alive_embed)


async def setup(bot: commands.Bot):
    logging.debug("Adding cog: PingCommand / AliveCommand")
    await bot.add_cog(PingCommand(bot))
