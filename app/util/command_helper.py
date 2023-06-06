import discord
import logging

from util.local import LOCAL_DATA
from util.embed_lib import InsufficientPermissionsEmbed


async def ensure_bot_perms(interaction: discord.Interaction, send_denied_response: bool = False) -> bool:
	"""
	Checks weather a user has sufficient permissions to execute an admin command.
	This checks the admin level within the config file for admin role id, or if the
	user has 'Administrator' permission in the same guild as the bot.

	Parameters:
		interaction (discord.interaction): the interaction from a command or event
		send_denied_response (bool): weather to send an embed response if user has insufficient perms

	Returns:
		A boolean for if user has sufficient permissions.
	"""
	user = interaction.user
	logging.debug(f"Checking bot permissions for {user}")

	if user.guild_permissions.administrator:
		return True

	admin_role_id = LOCAL_DATA.local_data.config.get("role_ids", "bot_admin")
	if admin_role_id is None:
		if send_denied_response:
			await interaction.response.send_message(embed=InsufficientPermissionsEmbed())
		return False

	user_role_ids = [role.id for role in user.roles]
	if admin_role_id in user_role_ids:
		return True

	else:
		if send_denied_response:
			await interaction.response.send_message(embed=InsufficientPermissionsEmbed())
		return False



