"""
This cog handles all the logic and functionality
to log and sync member GEXP.

Commands:
- /sync-gexp (Admin Only)
This command will trigger the gexp sync/logger

Tasks:
- sync_gexp_task
This task will automatically trigger
the gexp sync/logger every 15 minutes.
By default, the sync/logger will only
trigger after the 15-minute mark as to
not run on startup.

Author: illyum
"""

import time
import uuid
import aiohttp
import asyncio
import discord
import logging

from typing import Union, Dict

from discord import app_commands

import util.command_helper
from util.local import LOCAL_DATA
from discord.ext import tasks, commands
from util.uuider import add_hyphens_to_uuid
from util.embed_lib import GexpLoggerStartEmbed, GexpLoggerFinishEmbed


class GexpLogger(commands.Cog):
    """
    Cog class for logging Gexp tasks.
    """

    def __init__(self, bot: commands.Bot, *args, **kwargs):
        """
        Initialize the GexpLogger cog.

        Parameters:
            bot (commands.Bot): The instance of the bot.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.local_data = LOCAL_DATA.local_data
        self.has_run: bool = False
        self.start_message = None
        self.start_time = None
        self.end_time = None
        self.task_id = None
        self.is_running: bool = False
        self.server_id: int = int(self.local_data.config.get("bot", "server_id"))
        self.log_channel: int = int(self.local_data.config.get("channel_ids", "log_channel"))
        self.cursor = self.local_data.gexp_db.cursor
        self.sync_gexp_task.start()

    async def fetch_guild_data(self) -> Union[Dict, None]:
        """
        Fetches guild data from the Hypixel API.

        Parameters:
            self

        Returns:
            Union[Dict, None]: The guild data if successful, None otherwise. AKA response.json()
        """
        logging.debug("Fetching guild data")
        key = self.local_data.config.get("bot", "api_key")
        guild_id = self.local_data.config.get("bot", "guild_id")
        url = f"https://api.hypixel.net/guild?key={key}&id={guild_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logging.warning(f"Unknown status code: {response.status} (GexpLogger)")
                if int(response.headers.get('ratelimit-remaining', 0)) <= 0:
                    logging.warning("Key is being rate-limited. Check log file for more details")
                    logging.debug(f"Response Headers: {response.headers}")
                    time_to_sleep = int(response.headers.get('ratelimit-reset', 0)) + 2
                    await asyncio.sleep(time_to_sleep)

                guild_data = await response.json()
                if not guild_data["success"]:
                    logging.fatal(f"Unsuccessful in scraping API data: {response.headers} | {guild_data}")
                    return None
                return guild_data

    async def send_starting_message(self) -> None:
        """
        Sends the starting message for the GexpLogger task.

        The starting message includes the task ID and start time in an embed.

        Logs a warning if an exception occurs during message sending.

        Parameters:
            self

        Returns: None
        """
        logging.info(f"Running GexpLogger (id: {self.task_id})")
        try:
            self.start_message = await self.bot.get_guild(self.server_id).get_channel(self.log_channel).send(
                embed=GexpLoggerStartEmbed(
                    task_id=self.task_id,
                    start_time=self.start_time
                ))
        except Exception as e:
            logging.warning(e)

    async def send_finish_message(self, members_synced) -> None:
        """
        Sends the finishing message for the GexpLogger task.

        The finishing message includes the task ID, start time, end time, and number of members synced in an embed.

        Deletes the starting message and sends the finishing message to the log channel.

        Logs a warning if an exception occurs during message sending.

        Parameters:
            self
            members_synced (int): The number of members synced during the task.

        Returns:
            None
        """
        try:
            await self.start_message.delete()
            await self.bot.get_guild(self.server_id).get_channel(self.log_channel).send(
                embed=GexpLoggerFinishEmbed(
                    task_id=self.task_id,
                    start_time=self.start_time,
                    end_time=self.end_time,
                    members_synced=members_synced
                ))
        except Exception as e:
            logging.warning(e)

    def sync_member_exp_history(self, member) -> bool:
        """
        Synchronizes the experience history of a guild member.

        Retrieves the UUID and experience history of the member.
        Updates the database with the member's experience history, checking for any changes.

        Parameters:
            self
            member (dict): guild member info from guild endpoint


        Returns:
            bool: True if synchronization is successful, False otherwise.
        """
        try:
            _uuid = add_hyphens_to_uuid(member["uuid"])
            xp_history = member["expHistory"]

            for date, amount in xp_history.items():
                self.cursor.execute("SELECT * FROM expHistory WHERE uuid=? AND date=?", (_uuid, date))
                result = self.cursor.fetchone()
                # Result Example:
                # (293237, 1686528186, '2023-06-11', '5328930e-d411-49cb-90ad-4e5c7b27dd86', 0)
                # If result does not exist, result will be None
                time_now = int(time.time())
                if result is None:
                    # Create Data
                    self.cursor.execute("INSERT INTO expHistory (timestamp, date, uuid, amount) VALUES (?, ?, ?, ?)", (
                            time_now, date, _uuid, amount))
                else:
                    # Ensure data is correct
                    recorded_amount = result[4]
                    if recorded_amount != amount:
                        # Fix un-synced data
                        self.cursor.execute("UPDATE expHistory SET timestamp=?, amount=? WHERE uuid=? AND date=?", (
                            time_now, amount, _uuid, date))
                    else:
                        # Do nothing because data is correct
                        pass
        except Exception as e:
            logging.fatal(f"Encountered fatal exception syncing exp history for {member}: {e}")
            return False
        return True

    async def run_sync(self, interaction: discord.Interaction = None) -> None:
        """
        Runs the synchronization process. (Syncs ALL guild members)

        Performs the synchronization of guild members' experience history.
        Sends starting and finishing messages, updates the database, and sends responses.

        Parameters:
            self
            interaction (discord.Interaction, optional): The interaction associated with the command (if available).

        Returns:
            None
        """
        if self.is_running:
            logging.debug("Blocking sync due to duplicate instances")
            return
        logging.debug("Running GEXP Sync")

        self.is_running = True
        self.start_time = time.perf_counter()
        self.task_id = uuid.uuid4()
        if interaction is None:
            await self.send_starting_message()
        else:
            await interaction.response.send_message(embed=GexpLoggerStartEmbed(self.task_id, self.start_time))

        guild_data = await self.fetch_guild_data()
        logging.debug("Guild data retrieved")
        if guild_data is None:
            logging.critical("Unknown error fetching guild data")
            await self.send_finish_message(0)
            await self.alert_staff_of_error()
            return
        members_synced = 0
        logging.debug("Syncing members")
        guild_members = guild_data.get("guild").get("members")
        for member in guild_members:
            successful = self.sync_member_exp_history(member)
            if successful:
                members_synced += 1
            else:
                logging.error(f"Unknown error syncing member: '{member}'")
        logging.debug("Finished syncing members")
        self.cursor.connection.commit()
        self.end_time = time.perf_counter()
        await self.send_finish_message(members_synced)
        if interaction is not None:
            await interaction.edit_original_response(embed=GexpLoggerFinishEmbed(
                task_id=self.task_id,
                start_time=self.start_time,
                end_time=self.end_time,
                members_synced=members_synced
            ))

    async def alert_staff_of_error(self) -> None:
        """
        Alerts the staff of an error during the synchronization process.

        Retrieves the necessary role ID, server ID, and log channel ID from the configuration.
        Sends an alert message to the log channel mentioning the staff role.

        Logs a warning if an exception occurs during the alerting process.

        Parameters:
            self

        Returns:
            None
        """
        staff_role_id = int(self.local_data.config.get("role_ids", "bot_admin"))
        server_id = int(self.local_data.config.get("bot", "server_id"))
        log_channel_id = int(self.local_data.config.get("channel_ids", "log_channel"))
        try:
            admin_role = self.bot.get_guild(server_id).get_role(staff_role_id)
            alert_message = f"{admin_role.mention} ALERT:\nTHERE WAS AN ERROR SYNCING GEXP"
            await self.bot.get_guild(server_id).get_channel(log_channel_id).send(alert_message)
        except Exception as e:
            logging.warning(f"Unable to alert staff of an error: {e}")
            return

    @tasks.loop(minutes=15)
    async def sync_gexp_task(self) -> None:
        """
        Background task for periodically running the synchronization process.

        Skips the first run to avoid immediate execution upon starting the task.
        Runs the synchronization process, handling any exceptions that may occur.
        Sets the `is_running` flag accordingly.

        Parameters:
            self

        Returns:
            None
        """
        if self.is_running:
            return

        if not self.has_run:
            self.has_run = True
            logging.debug("GexpLogger: Skipping first run")
            return

        try:
            await self.run_sync()
        except Exception as e:
            logging.critical(f"GexpLogger: Could not complete task -> {e}")
            await self.alert_staff_of_error()
        self.is_running = False

    @sync_gexp_task.before_loop
    async def sync_gexp_task_setup(self) -> None:
        """
        Setup function for the sync_gexp_task loop.

        Waits until the bot is ready before starting the task.

        Parameters:
            self

        Returns:
            None
        """
        await self.bot.wait_until_ready()

    @app_commands.command(name="sync-gexp", description="Runs sync gexp task (Admin Only)")
    async def sync_gexp_command(self, interaction: discord.Interaction) -> None:
        """
        Command function for running the synchronization process.

        Checks if the user is an admin and if the task is already running.
        Runs the synchronization process, handling any exceptions that may occur.
        Sets the `is_running` flag accordingly.

        Parameters:
            interaction (discord.Interaction): The interaction associated with the command.

        Returns:
            None
        """
        is_admin = await util.command_helper.ensure_bot_perms(interaction, send_denied_response=True)
        if not is_admin:
            return

        if self.is_running:
            logging.debug("Blocking sync due to duplicate instances")
            _description = "Syncing is already happening, please wait before running this command again"
            is_running_embed = discord.Embed(description=_description)
            await interaction.response.send_message(embed=is_running_embed)
            return

        try:
            await self.run_sync(interaction)
        except Exception as e:
            logging.critical(f"GexpLogger: Could not complete command task -> {e}")
            await self.alert_staff_of_error()
        self.is_running = False


async def setup(bot: commands.Bot):
    logging.debug("Adding cog: GexpLogger")
    await bot.add_cog(GexpLogger(bot))
