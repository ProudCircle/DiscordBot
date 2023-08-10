import logging
from datetime import datetime

import discord

from discord.ext import commands
from discord import app_commands

from util import embed_lib, mcign
from util.mcign import MCIGN
from util.local import LOCAL_DATA, _DiscordLink


class GexpCommand(commands.GroupCog, name="gexp"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.local_data = LOCAL_DATA.local_data

    @app_commands.command(name="daily", description="GEXP a player has earned in a day")
    @app_commands.describe(player="Player to query data for")
    async def daily_command(self, interaction: discord.Interaction, player: str = None) -> None:
        user_id = interaction.user.id
        logging.debug(f"User {user_id} ran command '/gexp daily'")
        has_finished = False

        # Resolve by discord user ID
        if player is None:
            has_finished = await self.gexp_from_link(user_id, interaction)

        # Check if command has finished
        if has_finished:
            return

        # Resolve by UUID
        has_finished = await self.gexp_from_arg(player, interaction)

    async def gexp_from_link(self, user_id: int, interaction: discord.Interaction) -> bool:
        discord_link: _DiscordLink = self.local_data.discord_link.get_link(user_id)
        if not discord_link:
            await interaction.edit_original_response(embed=embed_lib.InvalidArgumentEmbed())
            return True

        # Actually get the GEXP
        date_today = datetime.today().strftime("%Y-%m-%d")
        gexp_today = self.get_daily_gexp(discord_link.uuid, date_today)

        if gexp_today is None:
            await self.send_gexp_not_found_response(interaction, f"<@{interaction.user.id}>")
            return True

        await self.send_daily_gexp_response(interaction, f"<@{interaction.user.id}>", gexp_today, date_today)
        return True

    async def gexp_from_arg(self, player: str, interaction: discord.Interaction) -> bool:
        cache_player = self.local_data.uuid_cache.get_entry(player)
        if cache_player.is_alive:
            uuid = mcign.dash_uuid(cache_player.uuid)
        else:
            mojang_player = MCIGN(player).uuid
            if mojang_player is None:
                await self.send_invalid_mojang_user_response(interaction, player)
                return True
            uuid = mojang_player

        # Actually get the GEXP
        date_today = datetime.today().strftime("%Y-%m-%d")
        gexp_today = self.get_daily_gexp(uuid, date_today)

        if gexp_today is None:
            await self.send_gexp_not_found_response(interaction, uuid)
            return True

        await self.send_daily_gexp_response(interaction, uuid, gexp_today, date_today)
        return True

    def get_daily_gexp(self, uuid: str, date: str) -> int:
        cursor = self.local_data.gexp_db.cursor
        cmd = "SELECT date, amount FROM expHistory WHERE (uuid = ?) AND (date = ?)"
        query = cursor.execute(cmd, (uuid, date))
        result = query.fetchone()
        if result:
            return result[1]
        return None

    async def send_invalid_argument_response(self, interaction: discord.Interaction):
        await interaction.edit_original_response(embed=embed_lib.InvalidArgumentEmbed())

    async def send_invalid_mojang_user_response(self, interaction: discord.Interaction, player: str):
        await interaction.edit_original_response(embed=embed_lib.InvalidMojangUserEmbed(player=player))

    async def send_gexp_not_found_response(self, interaction: discord.Interaction, uuid: str):
        await interaction.edit_original_response(embed=embed_lib.PlayerGexpDataNotFoundEmbed(player=uuid))

    async def send_daily_gexp_response(self, interaction: discord.Interaction, uuid: str, gexp: int, date: str):
        await interaction.edit_original_response(embed=embed_lib.DailyGexpEmbed(uuid, uuid, gexp, date))


async def setup(bot: commands.Bot):
    logging.debug("Adding Cog: Gexp Command")
    await bot.add_cog(GexpCommand(bot))
