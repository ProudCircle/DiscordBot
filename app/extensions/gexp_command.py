import logging
from datetime import datetime

import discord

from discord.ext import commands
from discord import app_commands

from util import embed_lib, mcign
from util.mcign import MCIGN
from util.local import LOCAL_DATA, _DiscordLink


class GexpPlayer:
    def __init__(self, displayname: str, uuid: str, gexp_value: int):
        self.displayname = displayname
        self.uuid = uuid
        self.gexp_value = gexp_value


class GexpCommand(commands.GroupCog, name="gexp"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.local_data = LOCAL_DATA.local_data

    @app_commands.command(name="daily", description="GEXP a player has earned in a day")
    @app_commands.describe(player="Player to query data for")
    async def process_daily_command(self, interaction: discord.Interaction, player: str = None) -> None:
        user_id = interaction.user.id
        logging.debug(f"User {user_id} ran command '/gexp daily'")
        await interaction.response.defer()
        uuid = None

        if player is None:
            player = await self.get_default_player(user_id)
            if player is None:
                await self.send_invalid_argument_response(interaction)
                return
            else:
                uuid = player.uuid

        if uuid is None:
            await self.send_invalid_mojang_user_response(interaction, player)
            return

        date_today = datetime.today().strftime("%Y-%m-%d")
        gexp_today = await self.get_gexp_for_player(uuid, date_today)

        if gexp_today is None:
            await self.send_gexp_not_found_response(interaction, uuid)
            return

        await self.send_daily_gexp_response(interaction, uuid, gexp_today, date_today)

    async def get_default_player(self, user_id: int) -> _DiscordLink:
        discord_link: _DiscordLink = self.local_data.discord_link.get_link(user_id)
        if discord_link:
            return discord_link
        return None

    async def get_uuid(self, player: str) -> str:
        cache_player = self.local_data.uuid_cache.get_entry(player)
        if cache_player.is_alive:
            return mcign.dash_uuid(cache_player.uuid)
        else:
            mojang_player = MCIGN(player).uuid
            if mojang_player is None:
                return None
            return mcign.dash_uuid(mojang_player)

    async def get_gexp_for_player(self, uuid: str, date: str) -> int:
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
