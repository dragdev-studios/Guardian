from discord.ext import commands


class Disabled(commands.CommandInvokeError):
	pass


class CommandDisabled(Disabled):
	def __str__(self):
		return "This command has been disabled by a server admin."


class ModuleDisabled(Disabled):
	def __str__(self):
		return "This entire module has been disabled by a server admin."
