import os
import toml
import time
import json
import sqlite3
import logging

from os import path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Union

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
    """
    Set up the required folders for the program.

    This function checks if the data and logs folders exist in the current directory.
    If the folders do not exist, the function creates them using the `os.mkdir` function.

    Parameters:
    None

    Returns:
    None
    """
    for folder in [DATA_FOLDER, LOGS_FOLDER, IMAGES_FOLDER, FONTS_FOLDER, DATABASE_FOLDER]:
        if not path.exists(folder):
            os.mkdir(folder)


class GexpDatabase:
    """
    Represents a GEXP Database.

    The GexpDatabase class provides functionality to interact with a SQLite database
    for GEXP data. It initializes a connection to the database upon instantiation,
    loads existing tables, and allows updating the list of tables.

    Attributes:
        connection (sqlite3.Connection): The connection object to the SQLite database.
        cursor (sqlite3.Cursor): The cursor object for executing SQL queries.
        tables (List[str]): A list of table names in the database.

    Methods:
        __init__: Initializes the GexpDatabase object.
        update_tables: Updates the list of tables in the database.

    """

    def __init__(self):
        """
        Initialize the GexpDatabase object.

        This method establishes a connection to the GEXP database, initializes the
        cursor, and loads the existing tables into the `tables` attribute.

        Parameters:
            self

        Returns:
            None

        """
        logging.info("Loading GEXP Database...")
        self.path = DATABASE_PATH
        self._create_gexp_table()
        self.connection = sqlite3.connect(self.path)
        self.cursor = self.connection.cursor()
        self.tables: List[str] = []
        self.update_tables()
        logging.debug("Complete!")

    def update_tables(self) -> None:
        """
        Update the list of tables in the database.

        This method queries the database to retrieve the names of all existing tables
        and updates the `tables` attribute with the fetched names.

        Parameters:
            self

        Returns:
            None

        """
        logging.debug("Updating tables")
        command = "SELECT name FROM sqlite_master WHERE type='table';"
        self.tables = self.cursor.execute(command).fetchall()

    def _create_gexp_table(self) -> None:
        """
        Create the GEXP table

        This method create the GEXP table in the GEXP History Database if it doesn't exist.
        It also creates triggers for formatting the UUID.

        Parameters:
            self

        Returns:
            None
        """
        logging.debug("Creating Gexp Table")

        create_table_command = """
        CREATE TABLE IF NOT EXISTS expHistory (
            id INTEGER AUTOINCREMENT PRIMARY KEY NOT NULL,
            timestamp INTEGER NOT NULL,
            date TEXT NOT NULL,
            uuid TEXT NOT NULL,
            amount INTEGER NOT NULL
        );
        """
        connection = sqlite3.connect(self.path)
        cursor = connection.cursor()
        cursor.execute(create_table_command)

        create_trigger_command_uuid = """
        CREATE TRIGGER IF NOT EXISTS format_uuid_trigger
        AFTER INSERT ON expHistory
        BEGIN
            UPDATE expHistory SET uuid =
                CASE
                    WHEN instr(uuid, '-') = 0 THEN
                        substr(uuid, 1, 8) || '-' ||
                        substr(uuid, 9, 4) || '-' ||
                        substr(uuid, 13, 4) || '-' ||
                        substr(uuid, 17, 4) || '-' ||
                        substr(uuid, 21)
                    ELSE
                        uuid
                END
            WHERE id = new.id;
        END;
        """
        cursor.execute(create_trigger_command_uuid)

        connection.commit()
        connection.close()


class TomlConfig:
    """
    Represents a TOML configuration file handler.

    The TomlConfig class provides functionality to manage a TOML configuration file.
    It allows loading an existing configuration file, setting values, getting values,
    and generating a default configuration file if none exists.

    Attributes:
        path (str): The path to the configuration file.
        default_config (Dict[Any]): The default configuration to use if none exists.
        config (Dict[Any]): The current configuration.

    Methods:
        __init__: Initializes the TomlConfig object.
        set: Sets a value in the configuration.
        get: Retrieves a value from the configuration.
        _save_config: Saves the current configuration to the file.
        _generate_default_config: Generates a default configuration file.

    """

    def __init__(self, config_path: str, default_config: Dict[str, Any] = None):
        """
        Initialize the TomlConfig object.

        This method loads an existing configuration file or generates a default one if
        none exists. The path to the configuration file and the default configuration
        dictionary can be provided.

        Parameters:
            config_path (str): The path to the configuration file.
            default_config (Dict[Any], optional): The default configuration dictionary.
                Defaults to None.

        Returns:
            None

        """
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

    def set(self, section, key, value) -> None:
        """
        Set a value in the configuration.

        This method sets the provided value for the given section and key in the
        configuration. If the section or key does not exist, they will be created.

        Parameters:
            section (str): The section in the configuration.
            key (str): The key within the section.
            value (Any): The value to set.

        Returns:
            None

        """
        if section not in self.config:
            self.config[section] = {}
        if value is None:
            value = "null"
        self.config[section][key] = value
        self._save_config()

    def get(self, section, key) -> Union[str, int, bool, None]:
        """
        Get a value from the configuration.

        This method retrieves the value associated with the given section and key from
        the configuration. If the section or key does not exist, None is returned.

        Parameters:
            section (str): The section in the configuration.
            key (str): The key within the section.

        Returns:
            Any: The retrieved value or None if not found.

        """
        if section in self.config and key in self.config[section]:
            value = self.config[section][key]
            if value == "null":
                return None
            return value
        return None

    def _save_config(self) -> None:
        """
        Save the configuration to the file.

        This method saves the current configuration to the TOML file.

        Parameters:
            self

        Returns:
            None

        """
        with open(self.path, 'w') as f:
            toml.dump(self.config, f)

    def _generate_default_config(self) -> None:
        """
        Generate a default configuration.

        This method generates a default configuration by setting the values specified
        in the `default_config` attribute if they don't already exist in the current configuration.

        Parameters:
            self

        Returns:
            None

        """
        for section, keys in self.default_config.items():
            if section not in self.config:
                self.config[section] = {}
            for key in keys:
                if key not in self.config[section]:
                    self.set(section, key, None)
        self._save_config()


class _CacheEntry:
    """
    Represents a cache entry.

    The _CacheEntry class encapsulates information about a cache entry, including its
    raw result, lifetime status, UUID, name, and birth timestamp.

    Attributes:
        _raw_result (Union[Tuple[str, str, int], tuple]): The raw result of the cache
            entry.
        is_alive (bool): Indicates whether the cache entry is still alive.
        uuid (str | None): The UUID associated with the cache entry.
        name (str | None): The name associated with the cache entry.
        born (int | None): The birth timestamp of the cache entry.

    Methods:
        __init__: Initializes the _CacheEntry object.

    """

    def __init__(
            self,
            raw_result: Union[Tuple[str, str, int], tuple] = (),
            lifetime_seconds: int = CACHE_LIFETIME_SECONDS):
        """
        Initialize the _CacheEntry object.

        This method initializes the _CacheEntry object with the provided raw result
        and calculates the lifetime status based on the birth timestamp and the
        specified lifetime duration.

        Parameters:
            raw_result (Union[Tuple[str, str, int], tuple], optional): The raw result of the cache entry. Defaults to ().
            lifetime_seconds (int, optional): The lifetime duration of the cache entry in seconds.
            Defaults to CACHE_LIFETIME_SECONDS.

        Returns:
            None

        """
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


class CacheDatabase:
    """
    Represents the cache database (Meant to be singleton).

    The CacheDatabase class provides functionality to manage a cache database stored
    in an SQLite file. It allows creating the cache table if it doesn't exist and
    provides a connection and cursor for executing SQL queries.

    Attributes:
        path (str): The path to the cache database file.
        connection (sqlite3.Connection): The connection object to the SQLite database.
        cursor (sqlite3.Cursor): The cursor object for executing SQL queries.

    Methods:
        __init__: Initializes the CacheDatabase object.
        _create_cache_table: Creates the cache table if it doesn't exist.

    """

    def __init__(self, cache_path: str):
        """
        Initialize the CacheDatabase object.

        This method initializes the CacheDatabase object by creating the cache table
        if it doesn't exist. It establishes a connection to the cache database and
        initializes the cursor.

        Parameters:
            cache_path (str): The path to the cache database file.

        Returns:
            None

        """
        logging.info("Loading Cache Database")
        self.path = cache_path
        if not os.path.exists(self.path):
            logging.warning("UUID Cache not found")
            self._create_cache_table()

        self.connection = sqlite3.connect(self.path)
        self.cursor = self.connection.cursor()
        logging.debug("Complete!")

    def _create_cache_table(self) -> None:
        """
        Create the cache table.

        This method creates the cache table in the cache database if it doesn't exist.
        It also creates triggers for formatting the UUID and setting the 'born'
        timestamp.

        Parameters:
            self

        Returns:
            None

        """
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

        connection.commit()
        connection.close()

    def add_entry(self, uuid: str, name: str) -> None:
        """
        Add an entry to the cache.

        This method adds a new entry to the cache table with the specified UUID and
        name.

        Parameters:
            uuid (str): The UUID of the entry.
            name (str): The name associated with the entry.

        Returns:
            None

        """
        command = "INSERT INTO cache (uuid, name) VALUES (?, ?)"
        self.cursor.execute(command, (uuid, name))
        self.connection.commit()

    def delete_entry(self, key: str) -> None:
        """
        Delete an entry from the cache.

        This method deletes the entry from the cache table based on the provided key,
        which can be either the UUID or the name of the entry.

        Parameters:
            key (str): The key (UUID or name) of the entry to delete.

        Returns:
            None

        """
        command = "DELETE FROM cache WHERE uuid IS ? OR name IS ?"
        self.cursor.execute(command, (key, key))
        self.connection.commit()

    def get_entry(self, key: str, lifetime_seconds: int = CACHE_LIFETIME_SECONDS) -> _CacheEntry:
        """
        Retrieve an entry from the cache.

        This method retrieves the entry from the cache table based on the provided key,
        which can be either the UUID or the name of the entry. It returns a _CacheEntry
        object representing the retrieved entry.

        Parameters:
            key (str): The key (UUID or name) of the entry to retrieve.
            lifetime_seconds (int, optional): The lifetime duration of the cache entry
            in seconds. Defaults to CACHE_LIFETIME_SECONDS.

        Returns:
            _CacheEntry: The retrieved cache entry.

        """
        command = "SELECT uuid, name, born FROM cache WHERE uuid is ? OR name = ?"
        query = self.cursor.execute(command, (key, key))
        result = query.fetchone()
        return _CacheEntry(result, lifetime_seconds=lifetime_seconds)

    def clear_cache(self) -> None:
        """
        Clear the cache.

        This method clears all entries from the cache table.

        Parameters:
            self

        Returns:
            None

        """
        command = "DELETE FROM cache;"
        self.cursor.execute(command)


class DiscordLink:
    """
    Represents a Discord link.

    The DiscordLink class provides functionality to manage a SQLite table used for
    linking Discord information. It ensures the integrity of the table structure and
    indexes required for linking.

    Attributes:
        cursor (sqlite3.Cursor): The cursor object for executing SQL queries.
        conn (sqlite3.Connection): The connection object to the SQLite database.

    Methods:
        __init__: Initializes the DiscordLink object.
        check_integrity: Checks the integrity of the Discord link table.

    """

    def __init__(self, cursor: sqlite3.Cursor):
        """
        Initialize the DiscordLink object.

        This method initializes the DiscordLink object with the provided cursor and
        connection. It checks the integrity of the Discord link table, ensuring the
        required columns and indexes exist.

        Parameters:
            self,
            cursor (sqlite3.Cursor): The cursor object for executing SQL queries.

        Returns:
            None

        """
        logging.info("Loading Discord Link...")
        self.cursor = cursor
        self.conn = cursor.connection
        self.check_integrity()
        logging.debug("Load Complete!")

    def check_integrity(self) -> None:
        """
        Checks the integrity of the database table 'discordLink' and ensures that all required columns are present.
        If any column is missing, it adds the missing column(s) and creates the necessary indexes.

        Returns:
            None
        """
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
        """
        Retrieves a Discord link from the 'discordLink' table based on the provided identification.
        The identification can be either the 'uuid' or 'discordId'.

        Args:
            identification: The identification (uuid or discordId) of the Discord link to retrieve.

        Returns:
            If a matching Discord link is found, an instance of the _DiscordLink class representing the link.
            If no matching link is found, None is returned.
        """
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
        """
        Removes a Discord link from the 'discordLink' table based on the provided row_id or uuid.
        Either the row_id or uuid must be specified.

        Args:
            row_id: The row ID of the Discord link to remove.
            uuid: The UUID of the Discord link to remove.

        Returns:
            None
        """
        assert (row_id is not None) or (uuid is not None)
        cmd = "DELETE FROM discordLink WHERE (rowid is ?) AND (uuid is ?)"
        execution = self.cursor.execute(cmd, (row_id, uuid))
        self.conn.commit()

    def register_link(self, player_uuid, discord_id, discord_username, timestamp_now_formatted=None):
        """
        Registers a new Discord link in the 'discordLink' table or updates an existing link with the provided information.

        Args:
            player_uuid: The UUID of the player.
            discord_id: The Discord ID to link with the player.
            discord_username: The Discord username associated with the Discord ID.
            timestamp_now_formatted: Optional. A formatted timestamp indicating when the link was registered.
            If not provided, the current time will be used.

        Returns:
            None
        """
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
    """
    Represents a Discord link with the associated information.

    Attributes:
        row_id (int): The row ID of the link in the database.
        uuid (str): The UUID of the player.
        discord_id (int): The Discord ID associated with the player.
        discord_username (str): The Discord username associated with the Discord ID.
        linked_at (datetime): The timestamp when the link was established.
    """

    def __init__(self, row_id: int, uuid: str, discord_id: str, discord_username: int, linked_at: int):
        """
        Initializes a new instance of the _DiscordLink class.

        Args:
            row_id (int): The row ID of the link in the database.
            uuid (str): The UUID of the player.
            discord_id (str): The Discord ID associated with the player.
            discord_username (int): The Discord username associated with the Discord ID.
            linked_at (int): The timestamp when the link was established.
        """
        self.row_id = row_id
        self.uuid = uuid
        self.discord_id = int(discord_id)
        self.discord_username = discord_username
        self.linked_at = datetime.fromtimestamp(linked_at)


class XpDivisionData:
    """
    Represents XP Division data containing information about roles and their requirements.

    Attributes:
        xp_data (dict): The XP Division data loaded from a JSON file.
    """

    def __init__(self):
        """
        Initializes a new instance of the XpDivisionData class.
        If the XP Division data file doesn't exist, it logs a warning and sets xp_data to None.
        Otherwise, it loads the XP Division data from the file.

        Example data format:
        {
          "roles": [
            {
              "id_name": "rookie_one",
              "discord_name": "[ 👾 ] Rookie I (75k)",
              "role_id": 1052291179103928340,
              "required_amount": 7500
            }
        }
        """
        if not os.path.exists(DIVISION_DATA):
            logging.warning("No XP Division found!")
            self.xp_data = None
        with open(DIVISION_DATA, 'r', encoding='utf-8') as division_data:
            self.xp_data = json.load(division_data)


class LocalData:
    """
    Represents local data used by the bot, including databases, configurations, and extension information.

    Attributes:
        gexp_db (GexpDatabase): The GexpDatabase instance for handling GEXP-related data.
        bot_extensions (List[str]): A list of bot extension names.
        config (TomlConfig): The TomlConfig instance for handling configuration data.
        uuid_cache (CacheDatabase): The CacheDatabase instance for caching UUID-related data.
        discord_link (DiscordLink): The DiscordLink instance for handling Discord link data.
        xp_division_data (XpDivisionData): The XpDivisionData instance for XP division data.
    """

    def __init__(self):
        """
        Initializes a new instance of the LocalData class.
        Initializes the various database and configuration instances.

        Example usage:
        local_data = LocalData()
        extensions = local_data.get_all_extensions()
        """
        self.gexp_db: GexpDatabase = GexpDatabase()
        self.bot_extensions = []
        self.config: TomlConfig = TomlConfig(CONFIG_PATH)
        self.uuid_cache: CacheDatabase = CacheDatabase(CACHE_PATH)
        self.discord_link: DiscordLink = DiscordLink(self.gexp_db.cursor)
        self.xp_division_data: XpDivisionData = XpDivisionData()

    def get_all_extensions(self) -> List[str]:
        """
        Retrieves all available bot extension names from the 'extensions' directory.

        Returns:
            A list of bot extension names.

        Example usage:
        local_data = LocalData()
        extensions = local_data.get_all_extensions()
        """
        self.bot_extensions = []
        for file in os.listdir('./extensions'):
            if file.endswith('.py'):
                self.bot_extensions.append(f"extensions.{file.replace('.py', '')}")
        logging.debug(f"Found {len(self.bot_extensions)} extension(s): {[f for f in self.bot_extensions]}")
        return self.bot_extensions


LOCAL_DATA: LocalData | None = None
