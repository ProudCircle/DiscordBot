import os
import discord
import logging

from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont

import util.local


class DrakeMeme(commands.Cog):
	def __init__(self, bot: commands.Bot, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.bot = bot
		self.template_url = os.path.join(util.local.IMAGES_FOLDER_PATH, 'drake_template.png')
		self.font_path = os.path.join(util.local.FONTS_FOLDER_PATH, 'arial.ttf')

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

		# Draw the "greater" text on the bottom half of the image
		text_size = draw.textsize(greater, font=font)
		x_center = (text_image.width - text_size[0]) // 2
		x = x_center + (text_image.width / 4)
		y = (text_image.height * 3 // 4) - text_size[1] // 2
		draw.text((x, y), greater, font=font, fill=(0, 0, 0, 255))

		# Merge the template and text images
		template.paste(text_image, (0, 0), text_image)

		# Save the generated meme image
		meme_file_path = os.path.join(util.local.IMAGES_FOLDER_PATH, "tmp/meme.png")
		template.save(meme_file_path, format='PNG')

		# Send the meme image as a message in the Discord channel
		await interaction.response.send_message(file=discord.File(meme_file_path, 'meme.png'))


async def setup(bot: commands.Bot):
	logging.debug("Adding cog: DrakeMeme")
	await bot.add_cog(DrakeMeme(bot))
