import discord
import typing

from discord.ext import commands, tasks
from .utils.config import read, write


class Configuration(commands.Cog):
	"""Configuration management."""
	def __init__(self, bot):
		self.bot = bot

	@commands.group(name="modlog", aliases=['ml'], case_insensitive=True, invoke_without_command=True)
	@commands.bot_has_permissions(embed_links=True)
	@commands.guild_only()
	async def modlogs(self, ctx, *, new: discord.TextChannel = None):
		"""Views (or sets) the guild's new modlog!

		To set a channel, you must have `manage server` and `manage channels` permissions."""
		data = read("./data/core.json")

		def a():
			return ctx.author.guild_permissions.manage_channels and ctx.author.guild_permissions.manage_guild
		if not a() or new is None:
			channel = self.bot.get_channel(data[str(ctx.guild.id)]["log channel"])
			if channel is None:
				data[str(ctx.guild.id)]["log channel"] = None
				write("./data/core.json", data)
				return await ctx.send(embed=discord.Embed(description="You don't have a modlog channel set."))
			else:
				e = discord.Embed(description=f"**Modlog Channel:** {channel.mention} ({channel.name})")
				return await ctx.send(embed=e)
		else:
			perms = new.permissions_for(ctx.me)
			if not perms.read_message_history or not perms.read_messages or not perms.embed_links or not perms.send_messages:
				return await ctx.send(embed=discord.Embed(title="That channel can't be used for modlog:",
														  description="Not enough permissions",
														  color=discord.Color.red()))
			data[str(ctx.guild.id)]["log channel"] = new.id
			write("./data/core.json", data)
			return await ctx.send(embed=discord.Embed(description=f"Set your modlog to {new.mention}.",
													  color=discord.Color.dark_green()))

	@commands.group(name="toggle", aliases=['enable', 'disable'], invoke_without_command=True)
	@commands.bot_has_permissions(embed_links=True)
	async def toggles(self, ctx):
		"""Toggle commands on/off. to enable/disable a command/module, run
		 `g!toggle command/module <command name/module name> <on/off>`. if a command name is provided, it must be the
		  full one. example: `g!toggle command foo off`, `g!toggle command "foo bar" off` (bar is a subcommand of foo)"""
		data = read("./data/core.json")
		cmds = data[str(ctx.guild.id)]["toggles"]["commands"]
		cogs = data[str(ctx.guild.id)]["toggles"]["modules"]
		if len(cmds) + len(cogs) == 0:
			return await ctx.send(embed=discord.Embed(title="You haven't disabled anything yet!", color=discord.Color.dark_green()))
		if len(cmds) == 0:
			pass
		else:
			e = discord.Embed(
				title="Disabled commands:",
				description=', '.join(cmds),
				color=discord.Color.orange()
			)
			await ctx.send(embed=e)
		if len(cogs) != 0:
			e = discord.Embed(
				title="Disabled Modules:",
				description=', '.join(cogs),
				color=discord.Color.orange()
			)
			await ctx.send(embed=e)

	@toggles.command(name="command")
	@commands.has_permissions(manage_guild=True)
	@commands.bot_has_permissions(embed_links=True)
	async def toggle_command(self, ctx, command: str, on_or_off: typing.Union[bool]):
		"""toggles a command on/off."""
		opp = {
			True: False,
			False: True
			# May seem odd, but when you think about it, =>toggle command help off would only disable it if like this.
		}
		on_or_off = opp[on_or_off]
		command = command.lower()
		cmd = self.bot.get_command(command)
		if cmd is None:
			return await ctx.send(embed=discord.Embed(title="Command not found!", color=discord.Color.dark_red()))
		else:
			data = read("./data/core.json")
			if on_or_off:  # on
				data[str(ctx.guild.id)]["toggles"]["commands"].append(cmd.name)
			else:
				if cmd.name in data[str(ctx.guild.id)]["toggles"]["commands"]:
					data[str(ctx.guild.id)]["toggles"]["commands"].remove(cmd.name)
			write("./data/core.json", data)
			return await ctx.send(embed=discord.Embed(description="Command toggled.", color=discord.Color.dark_green()))

	@staticmethod
	async def set_up_muted_role(ctx, role: discord.Role):
		await role.edit(position=ctx.guild.me.top_role.position - 1, reason="Muted Role Setup - Positioning")
		async with ctx.channel.typing():
			for channel in ctx.guild.channels:
				if channel.permissions_for(ctx.me).manage_roles:
					x = discord.Permissions().all_channel()
					y = discord.Permissions(0)
					z = discord.PermissionOverwrite().from_pair(y, x)
					await channel.set_permissions(role, overwrite=z, reason="Muted Role Setup - Channel Overrides")
		return True

	@commands.group(name="mutedrole", aliases=['muterole', 'mr'], invoke_without_command=True)
	@commands.bot_has_permissions(embed_links=True, manage_channels=True, manage_roles=True)
	@commands.has_permissions(manage_roles=True)
	async def muterole(self, ctx, new: discord.Role = None):
		"""View/set the server's muted role."""
		if new:
			data = read("./data/core.json")
			data[str(ctx.guild.id)]["muted role"] = new.id
			await self.set_up_muted_role(ctx, new)
			write("./data/core.json", data)
			return await ctx.send(embed=discord.Embed(description=f"Muted role set to {new.mention}.", color=discord.Color.green()))
		else:
			data = read("./data/core.json")
			role = data[str(ctx.guild.id)]["muted role"]
			role = ctx.guild.get_role(role)
			if role is None:
				return await ctx.send(embed=discord.Embed(description="Muted role was not found. you should set a new one.",
														  color=discord.Color.red()))
			else:
				return await ctx.send(embed=discord.Embed(description=f"Muted role is set to **{role.mention}**. run "
																	  f"`{ctx.prefix}{ctx.command.qualified_name} "
																	  f"resetup` fix permissions errors.",
														  color=discord.Color.green()))

	@muterole.command(name="resetup", aliases=['reconfig', 'fix'])
	@commands.has_permissions(manage_roles=True)
	@commands.bot_has_permissions(manage_roles=True, manage_guild=True)
	async def reconfig(self, ctx):
		"""reworks muted role"""
		data = read("./data/core.json")
		role = data[str(ctx.guild.id)]["muted role"]
		role = ctx.guild.get_role(role)
		if role is None:
			return await ctx.send(embed=discord.Embed(description="Muted role was not found. you should set a new one.",
													  color=discord.Color.red()))
		else:
			await self.set_up_muted_role(ctx, role)
			await ctx.send("done.")
			
	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def update(self, ctx):
		"""Updates your configuration to the newest one. use this if you get "KeyError"s."""
		data = read("./data/core.json")
		a = data[str(ctx.guild.id)]
		_format = {
				"warns": {},
				"mutes": {},
				"unmutes:": {},
				"bans": {},
				"kicks": {},
				"unbans": {},
				"next id": 1,
				"log channel": None,
				"toggles": {"commands": [], "modules": []},
				"muted role": None,
				"appeal server": None
			}
		for thing in _format.keys():
			if a.get(thing) is None:
				await ctx.send("added key {}".format(thing))
				a[thing] = _format[thing]
		write("./data/core.json", data)
		return await ctx.send("complete.")

	@commands.command(name="reset")
	@commands.check(lambda ctx: ctx.author == ctx.guild.owner)
	@commands.bot_has_permissions(embed_links=True)
	async def resetconfig(self, ctx):
		"""resets configuration."""
		data = read("./data/core.json")
		del data[str(ctx.guild.id)]
		write("./data/core.json", data)
		return await ctx.send(embed=discord.Embed(title="Reset your data.", color=discord.Color.dark_orange()))


def setup(bot):
	bot.add_cog(Configuration(bot))
