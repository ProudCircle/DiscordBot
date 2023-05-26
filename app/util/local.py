import os
import toml
import time
import json
import sqlite3
import logging

from os import path
from typing import List, Dict, Any, Tuple, Union
from datetime import datetime

# Variables located at the bottom of this file
DATA_FOLDER: str = "../data"
LOGS_FOLDER: str = path.join(DATA_FOLDER, "logs")
IMAGES_FOLDER: str = path.join(DATA_FOLDER, "images")
FONTS_FOLDER: str = path.join(DATA_FOLDER, "fonts")
DATABASE_FOLDER: str = path.join(DATA_FOLDER, "db")
DATABASE_PATH: str = path.join(DATABASE_FOLDER, "proudcircle.db")
CONFIG_PATH: str = path.join(DATA_FOLDER, "settings.conf")
CACHE_PATH: str = path.join(DATA_FOLDER, "uuid.cache")
CACHE_LIFETIME_SECONDS: int = 300
DIVISION_DATA: str = path.join(DATA_FOLDER, "xp_divisions_reqs.json")
WEEKLY_POINTS_DATA: str = path.join(DATA_FOLDER, "weekly_points_reqs.json")

PROGRAM_VARS = {}


def setup():
	if not path.exists(DATA_FOLDER):
		os.mkdir(DATA_FOLDER)

	if not path.exists(LOGS_FOLDER):
		os.mkdir(LOGS_FOLDER)


class GexpDatabase:
	def __init__(self):
		logging.info("Loading GEXP Database...")
		self.connection = sqlite3.connect(DATABASE_PATH)
		self.cursor = self.connection.cursor()
		self.tables: List[str] = []
		self.update_tables()
		logging.debug("Complete!")

	def update_tables(self):
		logging.debug("Updating tables")
		command = "SELECT name FROM sqlite_master WHERE type='table';"
		self.tables = self.cursor.execute(command).fetchall()


class TomlConfig:
	def __init__(self, config_path: str, default_config: Dict[Any] = None):
		logging.info("Loading Config...")
		if default_config is None:
			default_config = {'bot': ['token']}
		self.path: str = config_path
		self.default_config: Dict[Any] = default_config
		if os.path.exists(config_path):
			self.config = toml.load(config_path)
		else:
			self.config = {}
			self._generate_default_config()
			self._save_config()
		logging.debug("Complete!")

	def set(self, section, key, value):
		if section not in self.config:
			self.config[section] = {}
		if value is None:
			value = "null"
		self.config[section][key] = value
		self._save_config()

	def get(self, section, key):
		if section in self.config and key in self.config[section]:
			value = self.config[section][key]
			if value == "null":
				return None
			return value
		return None

	def _save_config(self):
		with open(self.path, 'w') as f:
			toml.dump(self.config, f)

	def _generate_default_config(self):
		for section, keys in self.default_config.items():
			if section not in self.config:
				self.config[section] = {}
			for key in keys:
				if key not in self.config[section]:
					self.set(section, key, None)
		self._save_config()


class _CacheEntry:
	def __init__(
			self,
			raw_result: Union[Tuple[str, str, int], tuple] = (),
			lifetime_seconds: int = CACHE_LIFETIME_SECONDS):
		self._raw_result = raw_result
		self.is_alive: bool = False
		self.uuid: str | None = None
		self.name: str | None = None
		self.born: int | None = None

		if raw_result is None:
			return

		self.uuid = raw_result[0]
		self.name = raw_result[1]
		self.born = int(raw_result[2])

		if (int(time.time()) - self.born) > lifetime_seconds:
			self.is_alive = False
		else:
			self.is_alive = True


thing = _CacheEntry(())


class CacheDatabase:
	def __init__(self, cache_path):
		logging.info("Loading Cache Database")
		self.path = cache_path
		if not os.path.exists(self.path):
			logging.warning("UUID Cache not found")
			self._create_cache_table()

		self.connection = sqlite3.connect(self.path)
		self.cursor = self.connection.cursor()
		logging.debug("Complete!")

	def _create_cache_table(self) -> None:
		logging.debug("Creating UUID Cache")
		create_table_command = """
		CREATE TABLE IF NOT EXISTS cache (
		    uuid TEXT PRIMARY KEY NOT NULL,
		    name TEXT NOT NULL,
		    born INTEGER
		);
		"""
		connection = sqlite3.connect(self.path)
		cursor = connection.cursor()
		cursor.execute(create_table_command)

		create_trigger_command_uuid = """
		CREATE TRIGGER IF NOT EXISTS format_uuid_trigger
		AFTER INSERT ON cache
		BEGIN
		    UPDATE cache SET uuid =
		        substr(uuid, 1, 8) || '-' ||
		        substr(uuid, 9, 4) || '-' ||
		        substr(uuid, 13, 4) || '-' ||
		        substr(uuid, 17, 4) || '-' ||
		        substr(uuid, 21)
		    WHERE rowid = new.rowid;
		END;
		"""
		cursor.execute(create_trigger_command_uuid)

		create_trigger_command_born = """
		CREATE TRIGGER set_born_trigger AFTER INSERT ON cache
		BEGIN
		    UPDATE cache SET born = strftime('%s', 'now')
		    WHERE rowid = new.rowid;
		END;
		"""
		cursor.execute(create_trigger_command_born)

	def add_entry(self, uuid: str, name: str) -> None:
		command = "INSERT INTO cache (uuid, name) VALUES (?, ?)"
		self.cursor.execute(command, (uuid, name))
		self.connection.commit()

	def delete_entry(self, key: str) -> None:
		command = "DELETE FROM cache WHERE uuid IS ? OR name IS ?"
		self.cursor.execute(command, (key, key))
		self.connection.commit()

	def get_entry(self, key: str, lifetime_seconds: int = CACHE_LIFETIME_SECONDS) -> _CacheEntry:
		command = "SELECT uuid, name, born FROM cache WHERE uuid is ? OR name = ?"
		query = self.cursor.execute(command, (key, key))
		result = query.fetchone()
		return _CacheEntry(result, lifetime_seconds=lifetime_seconds)

	def clear_cache(self) -> None:
		command = "DELETE FROM cache;"
		self.cursor.execute(command)


class DiscordLink:
	def __init__(self, cursor: sqlite3.Cursor):
		logging.info("Loading Discord Link...")
		self.cursor = cursor
		self.conn = cursor.connection
		self.check_integrity()
		logging.debug("Load Complete!")

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
			timestamp_now = int(time.time())
			timestamp_now_formatted = str(timestamp_now).split('.')[0]
		cmd = "INSERT INTO discordLink (uuid, discordId, discordUsername, linkedAt) VALUES (?, ?, ?, ?)"
		self.cursor.execute(cmd, (player_uuid, discord_id, discord_username, timestamp_now_formatted))
		self.conn.commit()


class _DiscordLink:
	def __init__(self, row_id: int, uuid: str, discord_id: str, discord_username: int, linked_at: int):
		self.row_id = row_id
		self.uuid = uuid
		self.discord_id = int(discord_id)
		self.discord_username = discord_username
		self.linked_at = datetime.fromtimestamp(linked_at)


class XpDivisionData:
	def __init__(self):
		if not os.path.exists(DIVISION_DATA):
			logging.warning("No XP Division found!")
			self.xp_data = None
		with open(DIVISION_DATA, 'r') as division_data:
			self.xp_data = json.load(division_data)


class LocalData:
	def __init__(self):
		self.gexp_db: GexpDatabase = GexpDatabase()
		self.bot_extensions = []
		self.config: TomlConfig = TomlConfig(CONFIG_PATH)
		self.uuid_cache: CacheDatabase = CacheDatabase(CACHE_PATH)
		self.discord_link: DiscordLink = DiscordLink(self.gexp_db.cursor)
		self.xp_division_data: XpDivisionData = XpDivisionData()

	def get_all_extensions(self) -> List[str]:
		self.bot_extensions = []
		for file in os.listdir('./extensions'):
			if file.endswith('.py'):
				self.bot_extensions.append(f"extensions.{file.replace('.py', '')}")
		logging.debug(f"Found {len(self.bot_extensions)} extension(s): {[f for f in self.bot_extensions]}")
		return self.bot_extensions


LOCAL_DATA: LocalData | None = None
