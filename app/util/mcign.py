import re
import requests


class MCIGN:
    def __init__(self, player_id=None):
        """
        Initialize the MCIGN object with a player ID.

        Parameters:
            player_id (str): The player ID used to identify the Minecraft player.
                             It can be either a username or a UUID.

        Raises:
            AssertionError: If player_id is not provided.
        """
        assert player_id is not None
        self._id = player_id
        self._name = None
        self._uuid = None

    @property
    def uuid(self):
        """
        Get the UUID associated with the player.

        If the UUID is not already loaded, it will be fetched from the Mojang API.

        Parameters:
            self

        Returns:
            str: The UUID of the player.
        """
        if self._uuid is None:
            self._load()
        return self._uuid

    @property
    def name(self):
        """
        Get the name associated with the player.

        If the name is not already loaded, it will be fetched from the Mojang API.

        Parameters:
            self

        Returns:
            str: The name of the player.
        """
        if self._name is None:
            self._load()
        return self._name

    def _load(self):
        """Load player data from the Mojang API based on the player ID."""
        if len(self._id) < 17:
            url = f"https://api.mojang.com/users/profiles/minecraft/{self._id}"
        else:
            url = f"https://sessionserver.mojang.com/session/minecraft/profile/{self._id}"
        r = requests.get(url)
        data = r.json()
        self._name = data.get("name", None)
        self._uuid = cleanup_uuid(data.get("id", None))


def is_valid_minecraft_username(username: str) -> bool:
    """
    https://help.mojang.com/customer/portal/articles/928638-minecraft-usernames
    Check if a Minecraft username is valid.

    Valid Minecraft usernames must satisfy the following criteria:
    - Must consist of alphanumeric characters (a-z, 0-9) and underscores (_).
    - Must be between 2 and 16 characters long (inclusive).

    Parameters:
        username (str): The Minecraft username to be validated.

    Returns:
        bool: True if the username is valid, False otherwise.
    """
    allowed_chars = 'abcdefghijklmnopqrstuvwxyz1234567890_'
    allowed_len = [2, 16]

    username = username.lower()

    if len(username) < allowed_len[0] or len(username) > allowed_len[1]:
        return False

    for char in username:
        if char not in allowed_chars:
            return False

    return True


def is_valid_mojang_uuid(uuid: str) -> bool:
    """
    https://minecraft-de.gamepedia.com/UUID
    Check if a UUID is valid according to the Mojang UUID format.

    Valid Mojang UUIDs must satisfy the following criteria:
    - Must consist of 32 hexadecimal characters (0-9, a-f).
    - Must be in lowercase.
    - Hyphens are optional and will be removed before validation.

    Parameters:
        uuid (str): The UUID to be validated.

    Returns:
        bool: True if the UUID is valid, False otherwise."""
    allowed_chars = '0123456789abcdef'
    allowed_len = 32

    uuid = uuid.lower()
    uuid = cleanup_uuid(uuid)

    if len(uuid) != allowed_len:
        return False

    for char in uuid:
        if char not in allowed_chars:
            return False

    return True


def cleanup_uuid(uuid: str) -> str:
    """
    Clean up a UUID by removing hyphens.

    Parameters:
        uuid (str): The UUID to be cleaned.

    Returns:
        str: The cleaned UUID without hyphens.
    """
    uuid = uuid.replace('-', '')
    return uuid


def dash_uuid(uuid):
    """
    Add dashes to a UUID string if it is in the non-dashed format.

    If the UUID already contains dashes (length of 36), it will be returned as is.
    Otherwise, the function will add dashes at the appropriate positions.

    Parameters:
        uuid (str): The UUID string to be dashed.

    Returns:
        str: The UUID string with dashes.
    """
    if len(uuid) == 36:
        return uuid
    dashed_uuid = re.sub(r"([0-9a-f]{8})([0-9a-f]{4})([0-9a-f]{4})([0-9a-f]{4})([0-9a-f]+)", r"\1-\2-\3-\4-\5", uuid)
    return dashed_uuid
