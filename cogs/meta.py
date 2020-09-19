import asyncio

import discord
from discord.ext import commands
from jishaku.paginators import PaginatorEmbedInterface, PaginatorInterface

from .utils.config import read
from .utils.entry_helper import Case, Converters
import typing


class DynamicGuild(commands.Converter):
	async def convert(self, ctx, argument):
		try:
			argument = int(argument)
		except:
			pass
		bot = ctx.bot
		if isinstance(argument, int):
			# check if its an ID first, else check enumerator
			guild = bot.get_guild(argument)
			if guild is not None:  # YAY
				return guild
			else:  # AWW
				for number, guild in enumerate(bot.guilds, start=1):
					if number == argument:
						return guild
				else:
					if guild is None:
						raise commands.BadArgument(f"Could not convert '{argument}' to 'Guild' with reason 'type None'")
					else:
						raise commands.BadArgument(f"Could not convert '{argument}' to 'Guild' as loop left.")
		elif isinstance(argument, str):  # assume its a name
			for guild in bot.guilds:
				if guild.name.lower() == argument.lower():
					return guild
			else:
				raise commands.BadArgument(f"Could not convert '{argument}' to 'Guild' with reason 'type None' at 1")
		else:
			raise commands.BadArgument(f"Could not convert argument of type '{type(argument)}' to 'Guild'")


class Meta(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command(name="stats", hidden=True)
	@commands.bot_has_permissions(embed_links=True)
	async def statistics(self, ctx: commands.Context):
		"""Shows the bot's statistics. Pretty simple."""
		from datetime import datetime, timedelta
		def p(n):
			return f'+{n}' if n > 0 else str(n)

		def s(n, n2):
			if n > n2:
				return "\U00002b06"
			elif n < n2:
				return "\U00002b07"
			else:
				return ""

		no = datetime.utcnow()
		yesterday = no - timedelta(-1)
		tya = no - timedelta(-2)
		guilds_two_days = len([
			n for n in self.bot.guilds if n.me.joined_at.day == tya.day and n.me.joined_at.month == tya.month \
			                              and n.me.joined_at.year == tya.year
		])
		guilds_yesterday = len([
			n for n in self.bot.guilds if
			n.me.joined_at.day == yesterday.day and n.me.joined_at.month == yesterday.month \
			and n.me.joined_at.year == yesterday.year
		])
		guilds_today = len([
			n for n in self.bot.guilds if
			n.me.joined_at.day == no.day and n.me.joined_at.month == no.month and n.me.joined_at.year == no.year
		])
		guilds_tomorrow = guilds_today + (guilds_two_days + guilds_yesterday)
		guilds_ind = guilds_tomorrow + (guilds_yesterday + guilds_today)

		gtd = guilds_two_days
		await ctx.send(
			f"**Guilds:**\nTotal: {len(self.bot.guilds)}\n\nTwo Days Ago: {p(gtd)}\n"
			f"Yesterday: {p(guilds_yesterday)} {s(guilds_yesterday, gtd)}\n"
			f"Today: {p(guilds_today)} {s(guilds_today, guilds_yesterday)}\n"
			f"*Predicted Futures:*\n"
			f"Tomorrow: {p(guilds_tomorrow)}\n"
			f"In Two Days: {p(guilds_ind)}"
		)

	@commands.Cog.listener()
	async def on_command_error(self, ctx, error):
		ignored = commands.CommandNotFound
		if isinstance(error, ignored):
			return  # we don't really care

		if isinstance(error, commands.NotOwner):
			return await ctx.send("You're not my owner!")
		elif isinstance(error, commands.BotMissingPermissions):
			mperms = [str(x).replace('_', ' ') for x in error.missing_perms]
			asd = "'"
			e = discord.Embed(
				title="Im missing permissions!",
				description=f"Give me '{f'{asd}, {asd}'.join(mperms)}' first!",
				color=discord.Color.dark_orange()
			)
			if ctx.channel.permissions_for(ctx.me).send_messages and ctx.channel.permissions_for(ctx.me).embed_links:
				return await ctx.send(embed=e)
			else:
				if ctx.channel.permissions_for(ctx.me).send_messages:
					return await ctx.send("Im missing core permissions, like embed links. provide this and try again.")
		elif isinstance(error, commands.MissingPermissions):
			mperms = [str(x).replace('_', ' ') for x in error.missing_perms]
			asd = "'"
			e = discord.Embed(
				title="You are missing permissions!",
				description=f"You need '{f'{asd}, {asd}'.join(mperms)}' first!",
				color=discord.Color.dark_orange()
			)
			if ctx.channel.permissions_for(ctx.me).send_messages and ctx.channel.permissions_for(ctx.me).embed_links:
				return await ctx.send(embed=e)
			else:
				if ctx.channel.permissions_for(ctx.me).send_messages:
					return await ctx.send("Im missing core permissions, like embed links. provide this and try again.")

		elif "has been disabled by a server admin." in str(error):
			return await ctx.send(str(error))
		elif isinstance(error, commands.CommandOnCooldown):
			try_again = Converters.fix_time(error.retry_after)
			return await ctx.send(f"{ctx.command.qualified_name} is on cooldown! Try again in {try_again}")
		elif isinstance(error, discord.Forbidden):
			return await ctx.send(f"I can not do that action because '{error.text}'.")
		elif isinstance(error, asyncio.TimeoutError):
			return await ctx.send(f"Timed out when waiting for a response.")
		elif isinstance(error, discord.NotFound):
			return await ctx.send(f"A requested item could not be found: '{error.text}'")
		else:
			e = discord.Embed(
				title="oops!",
				description=f"an error occured: `{str(error)}`. Please inform my developer in the [support server]"
							f"(https://beta.dragdev.xyz/r/server.html).\n\nIf this is a common error, please tell my "
							f"dev that this error is common.",
				color=discord.Color.dark_red(),
				url='https://dragdev.xyz/redirects/server.html'
			)
			await ctx.send(embed=e)
			raise error

	@commands.group(invoke_without_command=True)
	@commands.is_owner()
	async def servers(self, ctx):
		"""Lists servers."""
		paginator = PaginatorEmbedInterface(self.bot, commands.Paginator(prefix="```md", max_size=500))
		for number, guild in enumerate(ctx.bot.guilds, start=1):
			dot = '\u200B.'
			backtick = '\u200B`'
			await paginator.add_line(
				discord.utils.escape_markdown(f'{number}.  {guild.name.replace(".", dot).replace("`", backtick)}\n'))
		await paginator.send_to(ctx.channel)

	@servers.command(aliases=['join'])
	@commands.is_owner()
	async def invite(self, ctx, *, guild: DynamicGuild()):
		"""get an invite to a guild

		you can pass a name, id or enumerator number. ID is better."""
		if guild.me.guild_permissions.manage_guild:
			m = await ctx.send("Attempting to find an invite.")
			invites = await guild.invites()
			for invite in invites:
				if invite.max_age == 0:
					return await m.edit(content=f"Infinite Invite: {invite}")
			else:
				await m.edit(content="No Infinite Invites found - creating.")
				for channel in guild.text_channels:
					try:
						invite = await channel.create_invite(max_age=60, max_uses=1, unique=True,
															 reason=f"Invite requested"
																	f" by {ctx.author} via official management command. do not be alarmed, this is usually just"
																	f" to check something.")
						break
					except:
						continue
				else:
					return await m.edit(content=f"Unable to create an invite - missing permissions.")
				await m.edit(content=f"Temp invite: {invite.url} -> max age: 60s, max uses: 1")
		else:
			m = await ctx.send("Attempting to create an invite.")
			for channel in guild.text_channels:
				try:
					invite = await channel.create_invite(max_age=60, max_uses=1, unique=True,
														 reason=f"Invite requested"
																f" by {ctx.author} via official management command. do not be alarmed, this is usually just"
																f" to check something.")
					break
				except:
					continue
			else:
				return await m.edit(content=f"Unable to create an invite - missing permissions.")
			await m.edit(content=f"Temp invite: {invite.url} -> max age: 60s, max uses: 1")

	@servers.command(name='leave')
	@commands.is_owner()
	async def _leave(self, ctx, guild: DynamicGuild(), *, reason: str = None):
		"""Leave a guild. if ::reason:: is provided, then an embed is sent to the guild owner/system channel
		stating who made the bot leave (you), the reason and when.

		supply no reason to do a 'silent' leave"""
		if reason:
			e = discord.Embed(color=discord.Color.orange(), description=reason, timestamp=ctx.message.created_at)
			e.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url_as(static_format='png'))
			if guild.system_channel is not None:
				if guild.system_channel.permissions_for(guild.me).send_messages:
					if guild.system_channel.permissions_for(guild.me).embed_links:
						await guild.system_channel.send(embed=e)
			else:
				try:
					await guild.owner.send(embed=e)
				except discord.Forbidden:
					pass

		await guild.leave()
		await ctx.send(f"Left {guild.name} ({guild.id}) {f'for: {reason}' if reason else ''}")

	@servers.command()
	@commands.is_owner()
	async def info(self, ctx, *, guild: DynamicGuild()):
		"""Force get information on a guild. this includes debug information."""
		owner, mention = guild.owner, guild.owner.mention
		text_channels = len(guild.text_channels)
		voice_channels = len(guild.text_channels)
		roles, totalroles = [(role.name, role.permissions) for role in reversed(guild.roles)], len(guild.roles)
		bots, humans = len([u for u in guild.members if u.bot]), len([u for u in guild.members if not u.bot])

		def get_siplified_ratio():
			x = bots
			y = humans

			def get_hcf():
				if x > y:
					smaller = y
				else:
					smaller = x
				for i in range(smaller, 0, -1):
					if (x % i == 0) and (y % i == 0):
						hcf = i
						break
				else:
					raise ArithmeticError(f"Unable to find HCF for {x} and {y} (smallest {smaller})")
				return hcf

			hcf = get_hcf()
			return f"{x / hcf}:{y / hcf}"

		bot_to_human_ratio = '{}:{} ({})'.format(bots, humans, get_siplified_ratio())
		default_perms = guild.default_role.permissions.value
		invites = len(await guild.invites()) if guild.me.guild_permissions.manage_guild else 'Not Available'
		fmt = f"Owner: {owner} ({owner.mention})\nText channels: {text_channels}\nVoice Channels: {voice_channels}\n" \
			  f"Roles: {totalroles}\nBTHR: {bot_to_human_ratio}\n`@everyone` role permissions: {default_perms}\nInvites: " \
			  f"{invites}"
		await ctx.send(fmt)

		paginator = PaginatorEmbedInterface(self.bot, commands.Paginator(max_size=500))
		for name, value in roles:
			await paginator.add_line(f"@{name}: {value}")
		await paginator.send_to(ctx.channel)
		return await ctx.message.add_reaction('\U00002705')

	@servers.command(name="ban", aliases=['unban'])
	@commands.is_owner()
	async def server_ban(self, ctx, guild: typing.Union[DynamicGuild, int], *, reason: str = None):
		import json
		guild: int = guild.id if isinstance(guild, discord.Guild) else guild
		oldguild = self.bot.get_guild(guild)
		with open("./banned_servers.json", "r+") as bs:
			try:
				data = json.load(bs)
			except json.JSONDecodeError:
				data = dict()
			if data.get(str(guild)):
				del data[guild]
				await ctx.send(f"Unbanned guild with ID `{guild}`.")
			else:
				data[guild] = {
					"reason": reason,
					"banned at": str(ctx.message.created_at),  # trying not to import too many things here so i can
					# just paste it across bots
					"banned by": ctx.author.id
				}
				reason = reason or "No Reason Provided"
				try:
					await oldguild.owner.send(f"Your server \"**{discord.utils.escape_markdown(oldguild.name)}**\""
											  f" has been banned from using me with the following reason: {reason}."
											  f" To appeal this, please join my support server at"
											  f" <https://beta.dragdev.xyz/r/server.html> and ask a developer"
											  f" for an appeal.")
				except:
					pass
				await ctx.send(f"Banned guild with ID `{guild}` with reason {discord.utils.escape_mentions(str(reason))}.")
		with open("./banned_servers.json", "w+") as ab:
			json.dump(data, ab, indent=2)
		return

	@commands.group(aliases=['modboards', 'modlb', 'lbmod'], )
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(embed_links=True, manage_messages=True, add_reactions=True)
	async def modboard(self, ctx, *, sort_by_action: str = 'warns'):
		"""Shows the moderation leaderboard"""
		types = ['warns', 'mutes', 'unmutes', 'kicks', 'bans', 'unbans', 'all']
		sort_by_action = sort_by_action.lower()
		if sort_by_action not in types:
			esc = '\n• '
			return await ctx.send(f"No valid type to sort by. Please use one of the following:\n• {esc.join(types)}")
		else:
			async with ctx.channel.typing():  # aesthetics don't complain
				data = read('./data/core.json')
				guild = data.get(str(ctx.guild.id))
				paginator = PaginatorEmbedInterface(self.bot, commands.Paginator(max_size=1000, prefix='', suffix=''))
				# paginator = commands.Paginator(max_size=2000)
				key = guild.get(sort_by_action)
				authors = {}
				if key:
					# print(key)
					for _case in key.keys():
						# print(_case)
						_case = key[_case]
						_case['type'] = sort_by_action
						_case['ctx'] = ctx
						try:
							case = await Case.from_dict(_case)
						except (KeyError, Exception):
							await ctx.send(f"Error while creating case - skipping...", delete_after=10)
							await asyncio.sleep(2)
						if authors.get(case.author):
							authors[case.author] += 1
						else:
							authors[case.author] = 1
					keys = sorted(authors.keys(), key=lambda a: authors[a])
					# print("sorted", keys)
					for rank, user in enumerate(keys, start=1):
						if not isinstance(user, (discord.Member, discord.User)):
							name = f'Unknown (ID: {user})'
						else:
							name = user.display_name
						await paginator.add_line(f"**{rank}. {name}** with __{authors[user]}__ {sort_by_action}")
						# print("adding line")
			if len(paginator.pages) == 0:
				return await ctx.send("No events under that type found.")
			else:
				await paginator.send_to(ctx.channel)


def setup(bot):
	bot.add_cog(Meta(bot))
