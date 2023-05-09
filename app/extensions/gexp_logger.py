import uuid
import time
import logging
import aiohttp
import discord
import util.command_helper

from util import local
from util import embed_lib
from datetime import datetime
from discord import app_commands
from discord.ext import tasks, commands


class GexpLogger(commands.Cog):
	def __init__(self, bot: commands.Bot, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.bot = bot
		self.local_data = local.LOCAL_DATA
		self.server_id = int(local.LOCAL_DATA.config.get_setting("server_id"))
		self.has_run = False
		self.start_message = None
		self.start_time = None
		self.log_channel = int(local.LOCAL_DATA.config.get_setting("log_channel"))
		self.log_gexp.start()
		self.is_running = False

	def check_table_structure(self) -> None:
		logging.debug("Checking expHistory table structure")
		sqlite_cur = self.local_data.cursor
		sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='expHistory';")
		if not sqlite_cur.fetchone():
			# Table does not exist, create it
			logging.debug("Creating table expHistory")
			sqlite_cur.execute('''CREATE TABLE expHistory (timestamp text, date text, uuid text, amount int, rank text)''')
		else:
			# Table exists, check that it has the correct columns
			sqlite_cur.execute("PRAGMA table_info(expHistory);")
			column_info = sqlite_cur.fetchall()
			column_names = [column[1] for column in column_info]
			if "timestamp" not in column_names:
				logging.debug("Adding column: 'timestamp'")
				sqlite_cur.execute("ALTER TABLE expHistory ADD COLUMN timestamp text;")
			if "date" not in column_names:
				logging.debug("Adding column: 'date'")
				sqlite_cur.execute("ALTER TABLE expHistory ADD COLUMN date text;")
			if "uuid" not in column_names:
				logging.debug("Adding column: 'uuid'")
				sqlite_cur.execute("ALTER TABLE expHistory ADD COLUMN uuid text;")
			if "amount" not in column_names:
				logging.debug("Adding column: 'amount'")
				sqlite_cur.execute("ALTER TABLE expHistory ADD COLUMN amount int;")
			if "rank" not in column_names:
				logging.debug("Adding column: 'rank'")
				sqlite_cur.execute("ALTER TABLE expHistory ADD COLUMN rank text;")
		sqlite_cur.connection.commit()
		logging.debug("Table structure check complete!")

	async def fetch_guild_data(self):
		key = self.local_data.config.get_setting("api_key")
		guild_id = self.local_data.config.get_setting("guild_id")
		url = f"https://api.hypixel.net/guild?key={key}&id={guild_id}"
		async with aiohttp.ClientSession() as session:
			async with session.get(url) as response:
				# ratelimit_remaining = response.headers["RateLimit-Remaining"]
				guild_data = await response.json()
				if not guild_data["success"]:
					logging.fatal(f"Unsuccessful in scraping api data: {response.headers} | {guild_data}")
					return None
				return guild_data

	def sync_exp_history(self, member) -> None:
		sqlite_cur = self.local_data.cursor
		uuid = member["uuid"].replace('-', '')
		rank = member["rank"]
		xp_history = member["expHistory"]
		# logging.debug(f"Syncing Member: {member['uuid']}")

		for date, amount in xp_history.items():
			if str(date).startswith("2022"):
				logging.debug(f"Skipping date: {date}")
				continue

			sqlite_cur.execute("SELECT * FROM expHistory WHERE uuid=? AND date=?", (uuid, date))
			result = sqlite_cur.fetchone()
			if result:
				recorded_amount = result[3]
				if recorded_amount != amount:
					logging.debug(f"Updating unsynced data: {recorded_amount} -> {amount} | {uuid} {date}")
					sqlite_cur.execute("UPDATE expHistory SET timestamp=?, amount=? WHERE uuid=? AND date=?", (
						datetime.now().timestamp(), amount, uuid, date))
			else:
				# logging.debug(f"Syncing data: {uuid} {date}")
				sqlite_cur.execute(
					"INSERT INTO expHistory (timestamp, date, uuid, amount, rank) VALUES (?, ?, ?, ?, ?)", (
						datetime.now().timestamp(), date, uuid, amount, rank))
		sqlite_cur.connection.commit()

	def sync_division(self, member) -> None:
		sqlite_cur = self.local_data.cursor
		uuid = member["uuid"].replace('-', '')
		rank = member["rank"]

	@tasks.loop(minutes=15)
	async def log_gexp(self) -> None:
		if self.is_running:
			return

		if not self.has_run:
			self.has_run = True
			logging.debug("GexpLogger: Skipping first run")
			return

		self.is_running = True
		try:
			await self.run_sync()
		except Exception as e:
			logging.critical(f"GexpLogger: Could not complete task -> {e}")
		self.is_running = False

	@log_gexp.before_loop
	async def before_exp_logger_init(self):
		await self.bot.wait_until_ready()
		self.check_table_structure()

	async def run_sync(self, interaction: discord.Interaction = None):
		start_time = time.perf_counter()
		task_id = uuid.uuid4()
		await self.send_starting_message(start_time, task_id)
		if interaction is not None:
			try:
				await interaction.response.send_message(embed=embed_lib.GexpLoggerStartEmbed(
					task_id=task_id,
					start_time=start_time
				))
			except Exception as e:
				logging.error(f"GexpLogger: Could not send start message to log channel -> {e}")

		data = await self.fetch_guild_data()
		members_synced = 0

		bot_server_id = int(local.LOCAL_DATA.config.get_setting("server_id"))
		bot_admin = int(local.LOCAL_DATA.config.get_setting("bot_admin_role_id"))
		if data is None:
			logging.critical("Unknown error fetching guild data")
			await self.bot.get_guild(bot_server_id).get_channel(bot_admin).send(
				f"Unknown Error occurred with task id: {task_id} "
				f"{self.bot.get_guild(bot_server_id).get_role(bot_admin).mention}")
		else:
			guild_members = data.get("guild", {}).get("members", {})
			for member in guild_members:
				self.sync_exp_history(member)
				self.sync_division(member)
				members_synced += 1
		end_time = time.perf_counter()
		await self.send_finish_message(task_id, start_time, end_time, members_synced)
		if interaction is not None:
			try:
				await interaction.edit_original_response(embed=embed_lib.GexpLoggerFinishEmbed(
					task_id=task_id,
					start_time=start_time,
					end_time=end_time,
					members_synced=members_synced
				))
			except Exception as e:
				logging.error(f"GexpLogger: Could not send finish message to log channel -> {e}")
		logging.debug(f"GexpLogger Complete (id: {task_id})")

	async def send_starting_message(self, start_time, task_id):
		logging.info(f"Running GexpLogger (id: {task_id})")
		try:
			self.start_message = await self.bot.get_guild(self.server_id).get_channel(1061815307473268827)\
				.send(
				embed=embed_lib.GexpLoggerStartEmbed(
					task_id=task_id,
					start_time=start_time
				))
		except Exception as e:
			logging.warning(e)

	async def send_finish_message(self, task_id, start_time, end_time, members_synced):
		try:
			await self.start_message.delete()
			await self.bot.get_guild(self.server_id).get_channel(self.log_channel).send(
				embed=embed_lib.GexpLoggerFinishEmbed(
					task_id=task_id,
					start_time=start_time,
					end_time=end_time,
					members_synced=members_synced
				))
		except Exception as e:
			logging.warning(e)

	@app_commands.command(name="sync-gexp", description="Sync's the gexp with hypixel's data (Admins Only")
	async def sync_gexp_command(self, interaction: discord.Interaction):
		is_bot_admin = util.command_helper.ensure_bot_permissions(interaction, send_deny_response=True)
		if not is_bot_admin:
			return

		if self.is_running:
			is_running_embed = discord.Embed(description="Syncing is already happening, please wait before running this command again")
			await interaction.response.send_message(embed=is_running_embed)
			return

		self.is_running = True
		try:
			await self.run_sync(interaction)
		except Exception as e:
			logging.critical(f"GexpLogger: Could not complete command task -> {e}")
		self.is_running = False

	def check_permission(self, user: discord.Interaction.user):
		request = local.LOCAL_DATA.cursor.execute("SELECT bot_admin_role_id FROM config").fetchone()[0]
		if request is None:
			return False
		if user.get_role(int(request)):
			return True
		return False


async def setup(bot: commands.Bot):
	logging.debug("Adding cog: GexpLogger")
	await bot.add_cog(GexpLogger(bot))
