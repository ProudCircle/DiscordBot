import sys
import gzip
import shutil
import os.path
import discord
import logging
import asyncio
import argparse

from util import local
from discord.ext import commands


# The Proud Circle Discord Bot
class ProudCircleDiscordBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        logging.info(f"Logged in as {self.user}")

    async def setup_hook(self) -> None:
        # Load all extensions: commands, events, tasks, etc.
        ext = local.LOCAL_DATA.get_all_extensions()
        for extension in ext:
            try:
                await self.load_extension(extension)
            except Exception as e:
                logging.error(f"There was an error loading extension '{extension}': {e}")
        # Sync app commands
        await self.tree.sync()


# Setup Logger
def setup_logger(stdout_level=logging.INFO):
    discord_log_filename = os.path.join(local.LOGS_FOLDER_PATH, "discord.log")

    # Compress the old log file (if it exists) when the bot starts up
    try:

        if os.path.exists(discord_log_filename):
            log_time_timestamp = int(os.path.getctime(discord_log_filename))

            with open(discord_log_filename, 'rb') as f_in:
                with gzip.open(discord_log_filename + '.' + str(log_time_timestamp) + '.gz', 'wb') as f_out:
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

    # If requests_logger level is DEBUG the API key will be in plain-text in the log file
    # Please do not use the DEBUG level for the requests logger
    requests_logger = logging.getLogger('urllib3')
    requests_logger.setLevel(logging.INFO)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(stdout_level)

    datetime_format = "%H:%M:%S %d-%m-%Y"
    formatter = '[%(name)s] [%(asctime)s %(levelname)s] %(message)s'

    discord_log_handler = logging.FileHandler(discord_log_filename, encoding="utf8")
    discord_log_handler.setLevel(logging.DEBUG)

    logging.basicConfig(
        datefmt=datetime_format,
        format=formatter,
        encoding='utf-8',
        errors='replace',
        handlers=[
            discord_log_handler,
            stdout_handler
        ]
    )

    logging.debug("Logger setup complete")


# Startup discord bot
async def main():
    # Bot Meta-data Setup
    bot_intents = discord.Intents.default()
    bot_intents.message_content = True
    bot_intents.members = True
    bot_intents.guilds = True
    bot_intents.reactions = True
    bot_intents.dm_messages = True
    bot_intents.dm_typing = True
    bot_intents.dm_reactions = True
    bot_intents.invites = True
    bot_intents.messages = True
    bot_pfx = commands.when_mentioned
    bot_description = "A Discord Bot for the Proud Circle Guild!"

    # Start the discord bot
    bot = ProudCircleDiscordBot(intents=bot_intents, command_prefix=bot_pfx, description=bot_description)
    token = local.LOCAL_DATA.config.get_setting("bot_token")
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
    args = parser.parse_args()

    if args.verbose:
        setup_logger(logging.DEBUG)
    else:
        setup_logger()

    if args.token is not None:
        local.LOCAL_DATA.config.set_setting("bot_token", args.token)

    local.LOCAL_DATA = local.LocalData()

    print("Starting Proud Circle Bot...")
    asyncio.run(main())

    logging.info("Script finished")
