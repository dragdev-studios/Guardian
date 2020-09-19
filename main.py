import time

import discord

from discord.ext import commands
from jishaku.help_command import MinimalEmbedPaginatorHelp
from cogs.utils.config import read, write
from cogs.utils.errors import CommandDisabled, ModuleDisabled

import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(filename='debug.log', encoding='utf-8', mode='a', maxBytes=50000000, backupCount=1)
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


bot = commands.Bot(command_prefix=commands.when_mentioned_or(*["g!", "G!", "Guardian ", "Guard ", "guardian ", "guard "]),
				   help_command=MinimalEmbedPaginatorHelp(), owner_ids={421698654189912064, 317731855317336067},
                                   case_insensitive=True, activity=discord.Game("early development - open alpha."))

bot.started = time.time()

cogs = [
#	"cogs.config",
	"jishaku",
	"cogs.mod",
#	"cogs.meta",
#	"cogs.appeals",
#	"cogs._utils",
#	"cogs.events"
]
@bot.event
async def on_ready():
	bot.last_reboot = time.time()
	print(f"Logged in as {bot.user.name} - {discord.utils.oauth_url(bot.user.id)}")
	for cog in cogs:
		try:
			bot.load_extension(cog)
		except:
			continue
	print(f"{len(bot.guilds)} guilds, {len(bot.cogs)} cogs.")


@bot.before_invoke
async def makesuretheyareregisteredindatabase(ctx):
	d = read("./data/core.json")
	if d.get(str(ctx.guild.id)) is None:
		d[str(ctx.guild.id)] = {
			"warns":    {},
			"mutes":    {},
			"unmutes:": {},
			"bans":     {},
			"kicks":    {},
			"unbans":   {},
			"next id":  1,
			"log channel": None,
			"toggles": {"commands": [], "modules": []},
			"muted role": None,
			"appeal server": None,
			"automod": {
				"enabled": False,
				"upscale": False,
				"spam": {"in": 5, "count": 5, "punishment": None},
				"maxmentions": {"max": 10, "includeroles": True, "punishment": None},
				"ignore": {"roles": [], "channels": [], "users": []}
			}
		}
		write("./data/core.json", d)


@bot.check
async def notdisabled(ctx):
	if ctx.guild:
		data = read("./data/core.json")
		cog = ctx.command.cog_name
		cmdname = ctx.command.name
		i = str(ctx.guild.id)
		if data.get(str(ctx.guild.id)):
			if cmdname in data[i]["toggles"]["commands"]:
				raise CommandDisabled("Command Disabled")
			elif cog in data[i]["toggles"]["modules"]:
				raise ModuleDisabled("Module Disabled")
			else:
				return True
		else:
			return True

@bot.event
async def on_disconnect():
	logging.critical("Disconnected from discord.")

bot.run("INSERT_TOKEN_HERE!")
