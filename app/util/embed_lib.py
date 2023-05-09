import discord
import datetime


class ApiErrorEmbed(discord.Embed):
	def __init__(self, error_message=None):
		super().__init__()
		self.colour = discord.Colour(0xf00c27)
		self.title = "Error Report: "
		if error_message is None:
			error_message = "Unknown Error, please refer to the latest `discord.log` for more details."
		self.add_field(name="An API error has occurred:", value=error_message)


class InsufficientPermissionsEmbed(discord.Embed):
	def __init__(self):
		super().__init__()
		self.colour = discord.Colour(0xbf061c)
		self.description = ":x:  You do not have permission to use this command!"


class InvalidArgumentEmbed(discord.Embed):
	def __init__(self):
		super().__init__()
		self.colour = discord.Colour(0xf00c27)
		self.description = "Please specify a player!"


class InvalidMojangUserEmbed(discord.Embed):
	def __init__(self, is_invalid_uuid=False, is_invalid_name=True, player=None):
		super().__init__()
		self.colour = discord.Colour(0xdb1f29)
		description = "Invalid "
		if is_invalid_uuid:
			description = description + "uuid"
		elif is_invalid_name:
			description = description + "name"

		if player is None:
			description = description + "!"
		else:
			description = description + ": `" + player + "`!"

		self.description = description


class GexpLoggerStartEmbed(discord.Embed):
	def __init__(self, task_id, start_time):
		super().__init__()
		self.colour = discord.Colour(0x326e32)
		self.title = f"GexpLogger Report ({task_id})"
		self.add_field(name="Start Time: ", value=f"{start_time}")


class GexpLoggerFinishEmbed(discord.Embed):
	def __init__(self, task_id, start_time, end_time, members_synced):
		super().__init__()
		self.colour = discord.Colour(0x009900)
		self.title = f"GexpLogger Report ({task_id})"
		self.add_field(name="Start Time: ", value=f"{start_time}")
		self.add_field(name="Finish Time: ", value=f"{end_time}")
		elapsed_time = end_time - start_time
		self.add_field(name="Elapsed Time: ", value=f"Elapsed time: {elapsed_time:.4f} seconds")
		self.add_field(name="Members Synced: ", value=f"{members_synced}")


class PlayerGexpDataNotFoundEmbed(discord.Embed):
	def __init__(self, player: str = None):
		super().__init__()
		self.colour = discord.Colour(0x66112e)
		self.description = "Guild player data not found"
		if player is not None:
			self.description = self.description + " for `" + player + "`!"
		else:
			self.description = self.description + "!"


class DailyGexpEmbed(discord.Embed):
	def __init__(self, player_name: str, player_uuid: str, gexp: int, date: str):
		super().__init__()
		self.player_name = player_name.replace("_", "\\_")
		self.player_uuid = player_uuid
		self.gexp = gexp
		self.colour = discord.Colour(0xe80560)
		self.title = self.player_name + "'s GEXP " + date
		self.set_thumbnail(url=f"https://mc-heads.net/avatar/{player_uuid}/64")
		self.description = f"**{player_name}** has earned a grand total of {gexp:,} gexp today!"


class WeeklyGexpEmbed(discord.Embed):
	def __init__(self, player_name: str, player_uuid: str, gexp: dict, todays_date: datetime.datetime):
		super().__init__()
		player_name = player_name.replace("_", "\\_")
		self.colour = discord.Colour(0xe80560)
		self.title = f"{player_name}'s Weekly Gexp for {(todays_date - datetime.timedelta(days=7)).strftime('%B %d, %Y')}"
		gexp_history = []
		weekly_gexp = 0
		for day_gexp_date, day_gexp_amount in gexp.items():
			date = datetime.datetime.strptime(day_gexp_date, "%Y-%m-%d")
			formatted_date = date.strftime("%B %d, %Y")
			gexp_history.append(f"`{formatted_date}`: {day_gexp_amount:,}")
			weekly_gexp = weekly_gexp + day_gexp_amount
		self.add_field(name=f"7 Day Gexp History", value='\n'.join(gexp_history))
		self.set_thumbnail(url=f"https://mc-heads.net/avatar/{player_uuid}/64")
		self.description = f"That's a total of {weekly_gexp:,} gexp this week!"


class MonthlyGexpEmbed(discord.Embed):
	def __init__(self, player_name: str, player_uuid: str, gexp: dict, todays_date: datetime.datetime):
		super().__init__()
		player_name = player_name.replace("_", "\\_")
		self.colour = discord.Colour(0xe80560)
		month_name = todays_date.strftime('%B')
		self.title = f"{player_name}'s Monthly Gexp for {month_name}"
		gexp_history = []
		monthly_gexp = 0
		for day_gexp_date, day_gexp_amount in gexp.items():
			date = datetime.datetime.strptime(day_gexp_date, "%Y-%m-%d")
			formatted_date = date.strftime("%B %d, %Y")
			gexp_history.append(f"`{formatted_date}`: {day_gexp_amount:,}")
			monthly_gexp = monthly_gexp + day_gexp_amount
		self.add_field(name=f"{month_name}'s Gexp History", value='\n'.join(gexp_history))
		self.set_thumbnail(url=f"https://mc-heads.net/avatar/{player_uuid}/64")
		self.description = f"That's a total of {monthly_gexp:,} gexp this month!"


class YearlyGexpEmbed(discord.Embed):
	def __init__(self, player_name: str, player_uuid: str, player_head, gexp: int):
		super().__init__()
		player_name = player_name.replace("_", "\\_")
		player_uuid = player_uuid
		player_head = player_head
		gexp = gexp
		self.colour = discord.Colour(0xe80560)
		self.title = player_name + "'s GEXP 2023"
		self.set_thumbnail(url=f"https://mc-heads.net/avatar/{player_uuid}/64")
		self.description = f"**{player_name}** has earned a grand total of {gexp:,} gexp this year!"


class SuccessfullyLinkedEmbed(discord.Embed):
	def __init__(self, username, member: discord.Member):
		super().__init__()
		self.colour = discord.Colour(0x0c70f2)
		username = username.replace("_", "\\_")
		self.description = f"Successfully linked {username} to {member.mention}"


class SuccessfullyForceLinkedEmbed(discord.Embed):
	def __init__(self, username, member: discord.Member):
		super().__init__()
		self.colour = discord.Colour(0x0c70f2)
		username = username.replace("_", "\\_")
		self.description = f"Successfully linked {username} to `{member.name}#{member.discriminator}`"


class DivisionUpdateFinishWebhookEmbed(discord.Embed):
	def __init__(self, members_updated_count: int, errors: int):
		super().__init__()
		self.colour = discord.Colour(0x13a83a)
		self.title = "Division Update Complete!"
		self.add_field(name=f"Members Updated:", value=f"{members_updated_count}")
		self.add_field(name=f"Handled Errors:", value=f"{errors}")


class UnknownErrorEmbed(discord.Embed):
	def __init__(self):
		super().__init__()
		self.title = "Unknown Error"
		self.description = "Please refer to latest log file for more information"
