import os
import sys
import gzip
import shutil
import asyncio
import discord
import logging
import argparse

from util import local
from discord.ext import commands
from util.local import LOCAL_DATA
from logging.handlers import RotatingFileHandler

default_bot_intents = discord.Intents.default()
default_bot_intents.message_content = True
default_bot_intents.members = True
default_bot_intents.guilds = True
default_bot_intents.reactions = True
default_bot_intents.dm_messages = True
default_bot_intents.dm_typing = True
default_bot_intents.dm_reactions = True
default_bot_intents.invites = True
default_bot_intents.messages = True


class ProudCircleDiscordBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        logging.info(f"Logged in as {self.user}")

    async def setup_hook(self) -> None:
        # Load all extensions: commands, events, tasks, etc.
        ext = LOCAL_DATA.get_all_extensions()
        for extension in ext:
            try:
                await self.load_extension(extension)
            except Exception as e:
                logging.error(f"There was an error loading extension '{extension}': {e}")
        # Sync app commands
        await self.tree.sync()


def setup_logger(stdout_level=logging.INFO):
    discord_log_filename = os.path.join(local.LOGS_FOLDER, "discord.log")
    max_log_size = 1024 * 1024 * 100  # 10 MB

    # Compress and archive the old log file (if it exists) when the bot starts up
    try:
        if os.path.exists(discord_log_filename):
            log_time_timestamp = int(os.path.getctime(discord_log_filename))
            archive_filename = f"{discord_log_filename}.{log_time_timestamp}.gz"

            with open(discord_log_filename, 'rb') as f_in:
                with gzip.open(archive_filename, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            os.remove(discord_log_filename)
    except Exception as e:
        logging.warning(e)

    # Setup filesystem for bot
    local.setup()

    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.DEBUG)

    root_logger = logging.getLogger('root')
    root_logger.setLevel(logging.DEBUG)

    # If requests_logger level is DEBUG, the API key will be in plain-text in the log file
    # Please do not use the DEBUG level for the requests logger
    requests_logger = logging.getLogger('urllib3')
    requests_logger.setLevel(logging.INFO)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(stdout_level)

    datetime_format = "%H:%M:%S %d-%m-%Y"
    formatter = logging.Formatter('[%(name)s] [%(asctime)s %(levelname)s] %(message)s', datetime_format)

    discord_log_handler = RotatingFileHandler(discord_log_filename, maxBytes=max_log_size,
                                              backupCount=0, encoding="utf8")
    discord_log_handler.setLevel(logging.DEBUG)
    discord_log_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.DEBUG,
        datefmt=datetime_format,
        handlers=[
            discord_log_handler,
            stdout_handler
        ]
    )

    logging.debug("Logger setup complete")


def test_config() -> None:
    """
    Test weather the config has the correct setup for all the items
    needed for all the extensions or libraries of the bot.

    Returns:
        None

    """
    list_of_non_null_settings = [
        ["required", "bot.token", "Bot Login Token (Discord Developer Panel)"],
        ["required", "bot.api_key", "Hypixel API Key"],
        ['required', "bot.guild_id", "Proud Circle Hypixel Guild ID"],
        ['required', "bot.server_id", "Proud Circle Discord Guild ID"],
        ["required", "bot.server_id", "Discord Server ID of the Proud Circle Guild Discord"],
        ["required", "role_ids.bot_admin", "Bot Admin Role ID"],
        ["required", "channel_ids.log_channel", "The ID of the text channel where you want the bot's log to be"],
        # ["suggested", "message_ids.daily_gexp_lb", "The message ID of the GEXP Daily Leaderboard"],
        # ["suggested", "message_ids.weekly_gexp_lb", "The message ID of the GEXP Weekly Leaderboard"],
        # ["suggested", "message_ids.monthly_gexp_lb", "The message ID of the GEXP Monthly Leaderboard"],
        # ["suggested", "message_ids.yearly_gexp_lb", "The message ID of the GEXP Yearly Leaderboard"],
        # ["suggested", "message_ids.lifetime_gexp_lb", "The message ID of the GEXP Lifetime Leaderboard"],
        # ["suggested", "channel_ids.lb_channel", "The ID of the text channel where the leaderboards are held"],
    ]
    for item in list_of_non_null_settings:
        if item[0] == "required":
            section = item[1].split('.')[0]
            key = item[1].split('.')[1]
            if LOCAL_DATA.config.get(section, key) is None:
                logging.warning(f"Required config token: '{item[1]}' is invalid")
                setting = input(f"Enter value for {item[1]} ({item[2]}): ")
                LOCAL_DATA.config.set(section, key, setting.strip())


async def main(token: str):
    bot_pfx = commands.when_mentioned
    bot_description = "A Discord Bot for the Proud Circle Guild!"

    bot = ProudCircleDiscordBot(intents=default_bot_intents, command_prefix=bot_pfx, description=bot_description)
    if token is None:
        token = LOCAL_DATA.config.get('bot', 'token')
    if token is None:
        logging.critical("No bot token found")
        return
    logging.debug("Awaiting bot startup...")
    await bot.start(token)


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", help="Discord API token")
    parser.add_argument("--verbose", action="store_true", help="Show all log messages")
    cli_args = parser.parse_args()

    if cli_args.verbose:
        setup_logger(logging.DEBUG)
    else:
        setup_logger()

    # if args.token is not None:
    #     local.LOCAL_DATA.config.set_setting("bot_token", args.token)
    # At this point, localdata has not been initialized and therefore does not exist
    # TODO: Fix this

    LOCAL_DATA = local.LocalData()

    test_config()

    logging.info("Starting Proud Circle Bot...")
    asyncio.run(main(cli_args.token))

    logging.info("Script finished")
