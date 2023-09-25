"""
This cog adds 1 commands:
- /say
Use this command to make the bot
say something in whatever channel
you send the command in.

Author: illyum
"""

import discord
import logging

from discord import app_commands
from discord.ext import commands


class SayCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="say", description="Make the bot say something")
    @app_commands.describe(message="The message for the bot to repeat")
    async def ping(self, interaction: discord.Interaction, message: str):
        alive_embed = discord.Embed(description="Sending Message...", colour=discord.Colour(0xeb07a6))
        await interaction.response.send_message(embed=alive_embed, ephemeral=True)
        await interaction.channel.send(content=message)


async def setup(bot: commands.Bot):
    logging.debug("Adding cog: SayCommand")
    await bot.add_cog(SayCommand(bot))
