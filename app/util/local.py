import os
import json
import logging
import sqlite3
import datetime

DATA_FOLDER_PATH = "../data"
LOGS_FOLDER_PATH = os.path.join(DATA_FOLDER_PATH, "logs")
IMAGES_FOLDER_PATH = os.path.join(DATA_FOLDER_PATH, "images")
FONTS_FOLDER_PATH = os.path.join(DATA_FOLDER_PATH, "fonts")
DATABASE_FOLDER_PATH = os.path.join(DATA_FOLDER_PATH, "db")
DATABASE_PATH = os.path.join(DATABASE_FOLDER_PATH, "proudcircle.db")
CONFIG_PATH = os.path.join(DATA_FOLDER_PATH, "config")
XP_DIVISION_DATA_PATH = os.path.join(DATA_FOLDER_PATH, "xp_divisions.json")
LOCAL_DATA = None


def setup():
	if not os.path.exists(DATA_FOLDER_PATH):
		os.mkdir(DATA_FOLDER_PATH)
	if not os.path.exists(LOGS_FOLDER_PATH):
		os.mkdir(LOGS_FOLDER_PATH)


class LocalData:
	def __init__(self):
		self.connection = sqlite3.connect(DATABASE_PATH)
		self.cursor = self.connection.cursor()
		self.tables = []
		self.update_tables()
		self.config = ConfigHandler(self.cursor)
		self.extensions = []
		self.uuid_cache = UuidCache(self.cursor)
		self.discord_link = DiscordLink(self.cursor)

	# self.xp_division_data = XpDivisionData()

	def update_tables(self):
		logging.debug("Updating tables")
		cmd = "SELECT name FROM sqlite_master WHERE type='table';"
		self.tables = self.cursor.execute(cmd).fetchall()

	def reload(self):
		logging.debug("Reloading database...")
		logging.debug("Closing connections (Step 1/2)")
		self.connection.close()
		self.cursor.close()
		self.connection = None
		self.cursor = None
		self.tables = None
		self.extensions = []

		logging.debug("Reopening connections (Step 2/2)")
		self.connection = sqlite3.connect(DATABASE_PATH)
		self.cursor = self.connection.cursor()
		self.update_tables()
		self.config = ConfigHandler(self.cursor)
		self.extensions = self.get_all_extensions()
		logging.debug("Database reload complete")

	def get_all_extensions(self):
		self.extensions = []
		for file in os.listdir('./extensions'):
			if file.endswith('.py'):
				self.extensions.append(f"extensions.{file.replace('.py', '')}")
		logging.debug(f"Found {len(self.extensions)} extension(s): {[f for f in self.extensions]}")
		return self.extensions


class ConfigHandler:
	def __init__(self, cursor: sqlite3.Cursor):
		self.cursor = cursor
		self.conn = cursor.connection
		self.check_integrity()

	def add_setting(self, setting_name: str):
		"""Adds a new setting to the config table"""
		self.cursor.execute(f"ALTER TABLE config ADD COLUMN {setting_name} TEXT")
		self.conn.commit()

	def remove_setting(self, setting_name: str):
		"""Removes a setting from the config table"""
		self.cursor.execute(f"ALTER TABLE config DROP COLUMN {setting_name}")
		self.conn.commit()

	def get_setting(self, key: str) -> str:
		"""Retrieves the value of a setting from the config table"""
		self.cursor.execute(f"SELECT {key} FROM config")
		result = self.cursor.fetchone()
		if result is None:
			return None
		return result[0]

	def set_setting(self, key: str, value: str):
		"""Sets the value of a setting in the config table"""
		self.cursor.execute(f"UPDATE config SET {key} = '{value}'")
		self.conn.commit()

	def check_integrity(self):
		"""
		Checks the config table, just so the basics are there
		"""
		cmd = "CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY AUTOINCREMENT)"
		self.cursor.execute(cmd)
		self.conn.commit()

		self.cursor.execute("PRAGMA table_info(config)")
		columns = [column[1] for column in self.cursor.fetchall()]

		settings = []
		settings.append("bot_token")
		settings.append("api_key")
		settings.append("guild_id")
		settings.append("bot_admin_role_id")
		settings.append("server_id")
		settings.append("log_channel")
		settings.append("leaderboard_channel")
		settings.append("lb_division_id")
		settings.append("lb_lifetime_gexp_id")
		settings.append("lb_yearly_gexp_id")
		settings.append("lb_monthly_gexp_id")
		settings.append("lb_weekly_gexp_id")
		settings.append("lb_daily_gexp_id")

		for setting in settings:
			if setting not in columns:
				self.add_setting(setting)

		cmd = "SELECT * FROM config"
		result = self.cursor.execute(cmd).fetchall()
		if len(result) < 1:
			columns = ', '.join(settings)
			values = ', '.join(['null'] * len(settings))
			cmd = f"INSERT INTO config ({columns}) VALUES ({values})"
			self.cursor.execute(cmd)
			self.conn.commit()


class UuidCache:
	def __init__(self, cursor: sqlite3.Cursor):
		self.cursor = cursor
		self.conn = cursor.connection
		self.THRESHOLD_MINUTES = 120
		self.check_integrity()

	def check_integrity(self):
		"""
		Checks the cache table to make sure it's setup properly since this table often gets dropped
		"""
		cmd = "CREATE TABLE IF NOT EXISTS uuidCache (id INTEGER PRIMARY KEY AUTOINCREMENT)"
		self.cursor.execute(cmd)
		self.conn.commit()

		self.cursor.execute("PRAGMA table_info(uuidCache)")
		columns = [column[1] for column in self.cursor.fetchall()]

		if "uuid" not in columns:
			self.cursor.execute(f"ALTER TABLE uuidCache ADD COLUMN uuid TEXT")
		if "name" not in columns:
			self.cursor.execute(f"ALTER TABLE uuidCache ADD COLUMN name TEXT")
		if "requestedAt" not in columns:
			self.cursor.execute(f"ALTER TABLE uuidCache ADD COLUMN requestedAt TEXT")

		self.conn.commit()

	def get_player(self, player_id):
		logging.debug(f"Retrieving player with id: {player_id}")
		cmd = "SELECT id, uuid, name, requestedAt FROM uuidCache WHERE (uuid is ?) OR (name is ?)"
		query = self.cursor.execute(cmd, (player_id, player_id))
		cache_result = query.fetchall()
		if len(cache_result) > 1:
			logging.error(f"Duplicate players found! THIS SHOULDN'T HAPPEN : {cache_result}")
			return None
		elif len(cache_result) == 0:
			return None
		else:
			result = cache_result[0]

		if result is None:
			logging.debug("No valid entry found")
			return None

		row_id = result[0]
		uuid = result[1]
		name = result[2]
		requested = result[3]

		time_now = datetime.datetime.now().timestamp()
		string_time_now = str(time_now).split('.')[0]
		fmt_time_now = int(string_time_now)
		time_delta = datetime.datetime.fromtimestamp(int(requested)) - datetime.datetime.fromtimestamp(fmt_time_now)

		if (time_delta.seconds / 60) > self.THRESHOLD_MINUTES:
			logging.debug("Located valid cached player")
			return _MojangData(uuid=uuid, name=name)

		logging.debug("Clearing invalid player")
		cmd = "DELETE FROM uuidCache WHERE id = ?"
		execution = self.cursor.execute(cmd, (row_id,))
		self.conn.commit()
		return None

	def add_player(self, uuid, name, timestamp):
		logging.debug(f"Adding player {uuid} to cache")
		timestamp_string = str(timestamp).split('.')[0]
		if name is None or uuid is None or timestamp is None:
			logging.warning("Could not add invalid player to uuid cache!")
			return
		cmd = "INSERT INTO uuidCache (uuid, name, requestedAt) VALUES (?, ?, ?)"
		execution = self.cursor.execute(cmd, (uuid, name, timestamp_string))
		self.conn.commit()

	def clear_cache(self, confirm=False):
		if not confirm:
			logging.warning("Cache clearing has not been confirmed! The cache will not be deleted")

		logging.debug("Clearing uuid cache")
		self.cursor.execute("DROP TABLE uuidCache")
		self.conn.commit()
		self.check_integrity()


class DiscordLink:
	def __init__(self, cursor: sqlite3.Cursor):
		self.cursor = cursor
		self.conn = cursor.connection
		self.check_integrity()

	def check_integrity(self):
		cmd = "CREATE TABLE IF NOT EXISTS discordLink (id INTEGER PRIMARY KEY AUTOINCREMENT)"
		self.cursor.execute(cmd)
		self.conn.commit()

		self.cursor.execute("PRAGMA table_info(discordLink)")
		columns = [column[1] for column in self.cursor.fetchall()]

		if "uuid" not in columns:
			self.cursor.execute(f"ALTER TABLE discordLink ADD COLUMN uuid TEXT")
			self.cursor.execute(f"CREATE UNIQUE INDEX uuid_unique ON discordLink (uuid)")
		if "discordId" not in columns:
			self.cursor.execute(f"ALTER TABLE discordLink ADD COLUMN discordId TEXT")
			self.cursor.execute(f"CREATE UNIQUE INDEX discordId_unique ON discordLink (discordId)")
		if "discordUsername" not in columns:
			self.cursor.execute(f"ALTER TABLE discordLink ADD COLUMN discordUsername TEXT")
		if "linkedAt" not in columns:
			self.cursor.execute("ALTER TABLE discordLink ADD COLUMN linkedAt TEXT")

		self.cursor.execute(cmd)
		self.conn.commit()

	def get_link(self, identification):
		_id = str(identification)
		cmd = "SELECT id, uuid, discordId, discordUsername, linkedAt FROM discordLink WHERE (uuid is ?) OR (discordId is ?)"
		result = self.cursor.execute(cmd, (_id, _id)).fetchone()
		if result is None:
			return None

		row_id = result[0]
		uuid = result[1]
		discord_id = result[2]
		discord_username = result[3]
		linked_at = int(result[4])
		return _DiscordLink(int(row_id), uuid, discord_id, discord_username, linked_at)

	def remove_link(self, row_id=None, uuid=None):
		assert (row_id is not None) or (uuid is not None)
		cmd = "DELETE FROM discordLink WHERE (rowid is ?) AND (uuid is ?)"
		execution = self.cursor.execute(cmd, (row_id, uuid))
		self.conn.commit()

	def register_link(self, player_uuid, discord_id, discord_username, timestamp_now_formatted=None):
		link = self.get_link(player_uuid)
		if link is not None:
			self.remove_link(link.row_id, link.uuid)
		if timestamp_now_formatted is None:
			timestamp_now = datetime.datetime.now().timestamp()
			timestamp_now_formatted = str(timestamp_now).split('.')[0]
		cmd = "INSERT INTO discordLink (uuid, discordId, discordUsername, linkedAt) VALUES (?, ?, ?, ?)"
		self.cursor.execute(cmd, (player_uuid, discord_id, discord_username, timestamp_now_formatted))
		self.conn.commit()


class XpDivisionData:
	def __init__(self):
		if not os.path.exists(XP_DIVISION_DATA_PATH):
			logging.warning("No XP Division found!")
			self.xp_data = None
		with open(XP_DIVISION_DATA_PATH, 'r') as division_data:
			self.xp_data = json.load(division_data)


class _MojangData:
	def __init__(self, uuid, name):
		self.uuid = uuid
		self.name = name


class _DiscordLink:
	def __init__(self, row_id: int, uuid: str, discord_id: str, discord_username: int, linked_at: int):
		self.row_id = row_id
		self.uuid = uuid
		self.discord_id = int(discord_id)
		self.discord_username = discord_username
		self.linked_at = datetime.datetime.fromtimestamp(linked_at)
