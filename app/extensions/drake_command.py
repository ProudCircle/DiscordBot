import os
import math
import discord
import logging

from util import local
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont


class DrakeMeme(commands.Cog):
	def __init__(self, bot: commands.Bot, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.bot = bot
		self.local_data: local.LocalDataSingleton = local.LOCAL_DATA
		self.template_url = os.path.join(local.IMAGES_FOLDER, 'drake_template.png')
		self.font_path = os.path.join(local.FONTS_FOLDER, 'arial.ttf')

	@app_commands.command(name="drake", description="Make drake meme")
	@app_commands.describe(lesser="Text that goes on top")
	@app_commands.describe(lesser="Text that goes on bottom")
	async def drake_meme_command(self, interaction: discord.Interaction, lesser: str, greater: str):
		template = Image.open(self.template_url)
		font = ImageFont.truetype(self.font_path, 28)

		text_image = Image.new('RGBA', (template.width, template.height), (0, 0, 0, 0))

		# Draw the "lesser" text on the top half of the image
		draw = ImageDraw.Draw(text_image)
		text_size = draw.textsize(lesser, font=font)
		x_center = (text_image.width - text_size[0]) // 2
		x = x_center + (text_image.width / 4)
		y = (text_image.height - text_size[1]) // 4
		draw.text((x, y), lesser, font=font, fill=(0, 0, 0, 255))

		# Calculate the maximum characters per line based on the template width and font size
		max_chars_per_line = 30

		# Split the "greater" text into two lines if it exceeds the maximum characters per line
		if len(greater) > max_chars_per_line:
			# Find the index of the last space character within the limit
			split_index = max_chars_per_line - greater[max_chars_per_line::-1].find(' ')

			# Split the text into two lines
			greater_line1 = greater[:split_index].strip()
			greater_line2 = greater[split_index:].strip()

			# Draw the first line of "greater" text
			await self.draw_text(draw, font, greater, text_image)

			# Draw the second line of "greater" text
			text_size = draw.textsize(greater_line2, font=font)
			x_center = (text_image.width - text_size[0]) // 2
			x = x_center + (text_image.width / 4)
			y = (text_image.height * 3 // 4) + text_size[1] // 2
			draw.text((x, y), greater_line2, font=font, fill=(0, 0, 0, 255))
		else:
			# Draw the "greater" text on the bottom half of the image (single line)
			await self.draw_text(draw, font, greater, text_image)

		# Merge the template and text images
		template.paste(text_image, (0, 0), text_image)

		# Save the generated meme image
		meme_file_path = os.path.join(local.IMAGES_FOLDER, "tmp/meme.png")
		template.save(meme_file_path, format='PNG')

		# Send the meme image as a message in the Discord channel
		await interaction.response.send_message(file=discord.File(meme_file_path, 'meme.png'))

	async def draw_text(self, draw, font, greater, text_image):
		text_size = draw.textsize(greater, font=font)
		x_center = (text_image.width - text_size[0]) // 2
		x = x_center + (text_image.width / 4)
		y = (text_image.height * 3 // 4) - text_size[1] // 2
		draw.text((x, y), greater, font=font, fill=(0, 0, 0, 255))


async def setup(bot: commands.Bot):
	logging.debug("Adding cog: DrakeMeme")
	await bot.add_cog(DrakeMeme(bot))
