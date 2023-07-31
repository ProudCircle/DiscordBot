import logging
from datetime import datetime

import discord

from discord.ext import commands
from discord import app_commands

from util import embed_lib, mcign
from util.mcign import MCIGN
from util.local import LOCAL_DATA


class GexpCommand(commands.GroupCog, name="gexp"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.local_data = LOCAL_DATA.local_data

    @app_commands.command(name="daily", description="GEXP a player has earned in a day")
    @app_commands.describe(player="Player to query data for")
    async def daily_command(self, interaction: discord.Interaction, player: str = None) -> None:
        logging.debug(f"User {interaction.user.id} ran command '/gexp daily'")
        await interaction.response.defer()

        if player is None:
            discord_link = self.local_data.discord_link.get_link(interaction.user.id)
            player = mcign.dash_uuid(discord_link.uuid)
            if discord_link is None:
                await interaction.edit_original_response(embed=embed_lib.InvalidArgumentEmbed())
                return

        uuid = None
        cache_player = self.local_data.uuid_cache.get_entry(player)
        if cache_player.is_alive:
            uuid = mcign.dash_uuid(cache_player.uuid)
        else:
            mojang_player = MCIGN(player).uuid
            if mojang_player is None:
                await interaction.edit_original_response(embed=embed_lib.InvalidMojangUserEmbed(player=player))
                return
            uuid = mojang_player

        date_today = datetime.today().strftime("%Y-%m-%d")
        cursor = self.local_data.gexp_db.cursor
        cmd = "SELECT date, amount FROM expHistory WHERE (uuid = ?) AND (date = ?)"
        query = cursor.execute(cmd, (uuid, date_today))
        result = query.fetchone()
        if result is None:
            await interaction.edit_original_response(
                embed=embed_lib.PlayerGexpDataNotFoundEmbed(player=uuid))
            return
        gexp_today = result[1]
        await interaction.edit_original_response(
            embed=embed_lib.DailyGexpEmbed(uuid, uuid, result[1], result[0]))


async def setup(bot: commands.Bot):
    logging.debug("Adding Cog: Gexp Command")
    await bot.add_cog(GexpCommand(bot))
