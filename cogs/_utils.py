import asyncio
import copy
import datetime
import json
import os
import random
import string
import time
import typing
import urllib.parse

import discord
import matplotlib.pyplot as plt
import psutil
from discord.ext import commands, menus
from jishaku.paginators import PaginatorEmbedInterface
import niceweb

class RedditMenu(menus.Menu):
	def __init__(self, embeds, **kwargs):
		super().__init__(**kwargs)
		self.embeds = embeds
		self.index = 0

	def calculate_index(self, back: bool = False):
		if back:
			self.index -=  1
			if self.index < 0:
				self.index = len(self.embeds)-1
		else:
			self.index += 1
			self.index = min(len(self.embeds)-1, self.index)

	@menus.button("\U00002b05")
	async def back(self, payload: discord.RawReactionActionEvent):
		if payload.event_type != "REACTION_ADD": return
		await self.message.remove_reaction(payload.emoji, self.ctx.author)
		self.calculate_index(True)
		embed = self.embeds[self.index]
		embed.set_footer(text=f"Post {self.index+1}/{len(self.embeds)}")
		await self.message.edit(embed=embed)

	@menus.button("\U000023f9")
	async def _stop(self, _):
		self.stop()

	@menus.button("\U000027a1")
	async def next(self, payload: discord.RawReactionActionEvent):
		if payload.event_type != "REACTION_ADD": return
		await self.message.remove_reaction(payload.emoji, self.ctx.author)
		self.calculate_index(False)
		embed = self.embeds[self.index]
		embed.set_footer(text=f"Post {self.index+1}/{len(self.embeds)}")
		await self.message.edit(embed=embed)

	async def send_initial_message(self, ctx, channel):
		e = self.embeds[0]
		e.set_footer(text=f"Post 1/{len(self.embeds)}")
		return await ctx.send(embed=e)


class OneLinePaginator(PaginatorEmbedInterface):
	"""A paginator that only displays one add_line per page."""

	async def add_line(self, *args, **kwargs):
		display_page = self.display_page
		page_count = self.page_count

		self.paginator.add_line(*args, **kwargs)

		new_page_count = self.page_count

		if display_page + 1 == page_count:
			# To keep position fixed on the end, update position to new last page and update message.
			self._display_page = new_page_count
			self.bot.loop.create_task(self.update())
		self.paginator.close_page()


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


def ago_time(time):
	"""Convert a time (datetime) to a human readable format.
	"""
	date_join = datetime.datetime.strptime(str(time), "%Y-%m-%d %H:%M:%S.%f")
	date_now = datetime.datetime.now(datetime.timezone.utc)
	date_now = date_now.replace(tzinfo=None)
	since_join = date_now - date_join

	m, s = divmod(int(since_join.total_seconds()), 60)
	h, m = divmod(m, 60)
	d, h = divmod(h, 24)
	y = 0
	while d >= 365:
		d -= 365
		y += 1

	if y > 0:
		msg = "{4}y, {0}d {1}h {2}m {3}s ago"
	elif d > 0 and y == 0:
		msg = "{0}d {1}h {2}m {3}s ago"
	elif d == 0 and h > 0:
		msg = "{1}h {2}m {3}s ago"
	elif d == 0 and h == 0 and m > 0:
		msg = "{2}m {3}s ago"
	elif d == 0 and h == 0 and m == 0 and s > 0:
		msg = "{3}s ago"
	else:
		msg = ""
	return msg.format(d, h, m, s, y)


def fix_time(value: float, round_to: int = 0) -> str:
	"""Shortcut for make_time"""
	return make_time(value, round_to)


def make_time(value: float, round_to: int = 0) -> str:
	seconds = round(value, round_to)
	minutes = 0
	hours = 0
	days = 0
	weeks = 0

	while seconds >= 60:
		minutes += 1
		seconds -= 60

	while minutes >= 60:
		minutes -= 60
		hours += 1

	while hours >= 24:
		days += 1
		hours -= 24

	while days >= 7:
		weeks += 1
		days -= 7

	w = f"{weeks} week{'s' if weeks != 1 else ''}, " if weeks > 0 else ""
	d = f"{days} day{'s' if days != 1 else ''}, " if days > 0 else ""
	h = f"{hours} hour{'s' if hours != 1 else ''}, " if hours > 0 else ""
	m = f"{minutes} minute{'s' if minutes != 1 else ''}, " if minutes > 0 else ""
	s = f"{seconds} second{'s' if seconds != 1 else ''}" if seconds > 0 else ""  # no leading comma since its the
	# last displayed item
	return f"{w}{d}{h}{m}{s}"  # make it easy with the f-strings including punctuation for us.


class Utils(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.bot.winner = self.bot.user
		self.emojis = {
			"toggles": {"on": str(bot.get_emoji(616068601476022283)), "off": ' <:off:616068601375358987>'},
			"wumpus": '<:dds_wumpus:616073315844358225>',
			'invite': '<:invite_white:616075493082529846>',
			'verified': '<:dds_verified:616073827180478466>',
			'partner': '<:dds_partner:616073613157728276>',
			'search': '<:dds_search:616074439368638475>',
			'animated_icon': '<a:dwumpus:616077357496926209>',
			'lurk': '<:dds_lurk:616075914597498988>',

		}
		self.polls = {}

	def _is_on_mobile(ctx):  # _ prefix to prevent shadowing || CTX claims to be self, but it isnt.
		if not ctx.author.is_on_mobile():
			raise commands.CommandInvokeError("Must be on mobile")
		else:
			return True  # we cant have it as a staticmethod, and command_check doesnt provide self.

	# so we are stuck with this linted mess

	@commands.command(name="meta", aliases=['info', 'uptime', 'invite', 'ping'])
	@commands.bot_has_permissions(embed_links=True)
	async def _bot_meta(self, ctx):
		"""Displays meta information, like invite, uptime and ping."""
		if psutil.LINUX:
			with open("/proc/uptime", "r") as uptimefile:
				raw = str(uptimefile.read())
				total, idle = raw.split(" ")
				total, idle = round(float(total), 2), round(float(idle), 2)
				human_total = make_time(total)
				human_idle = make_time(idle)
		else:
			human_total = "Undefined - Wrong Operating System (linux only)"
			human_idle = "Undefined - Wrong Operating System (linux only)"
		owner = self.bot.get_user(421698654189912064)
		if owner:
			owner = str(owner)
		else:
			owner = "EEKIM10_YT"
		guilds = len(self.bot.guilds)
		comman = len(self.bot.commands)
		ping = time.perf_counter()
		msg = await ctx.send(embed=discord.Embed(title="loading...", color=discord.Color.dark_blue()))
		bot_uptime = make_time(time.time() - self.bot.started) + ' ago'
		bot_reboot = make_time(time.time() - self.bot.last_reboot) + ' ago'
		after = time.perf_counter()
		ping = str(round(after - ping, 2) * 1000) + 'ms'
		latency = str(round(self.bot.latency * 1000, 2)) + 'ms'
		invite = discord.utils.oauth_url(str(self.bot.user.id))
		e = discord.Embed(
			title=f"My information:",
			color=discord.Color.dark_blue()
		)
		e.add_field(name="Ping:", value=f"{ping} delay\n{latency} connection latency")
		e.add_field(name=f"Invite:", value=invite)
		e.add_field(name="Figures:", value=f"Guilds: {guilds}\nCommands: {comman}\nUptime: below\nOwner: {owner}")
		e.add_field(name="Uptime:", value=f"Host uptime: {human_total}\nHost *idle* time: {human_idle}\n"
		                                  f"`runme.py` executed: {bot_uptime}\nlast (re)connect: {bot_reboot}",
		            inline=False)
		await msg.edit(embed=e)

	@commands.command(name="nsfwtoggle", aliases=['nsfwt', 'nt', 'ntoggle'])
	@commands.check(_is_on_mobile)
	@commands.has_permissions(manage_channels=True)
	@commands.bot_has_permissions(manage_channels=True, manage_messages=True)
	async def togglensfw(self, ctx, forcemode: typing.Optional[bool], *, channel: discord.TextChannel = None):
		"""Make a channel (n)sfw. only available on mobile as on IOS, the option is not available. on pc and android
		 you can toggle it with the discord UI"""
		mode = forcemode
		channel = channel if channel else ctx.channel
		if mode is None:
			if channel.nsfw:
				mode = False
			else:
				mode = True
		if channel.permissions_for(ctx.me).manage_channels:
			await channel.edit(nsfw=mode, reason=f"Toggled by {str(ctx.author)} - mobile")
			return await ctx.send(
				embed=discord.Embed(description=f"set {channel.mention} to {'nsfw' if mode else 'sfw'}.",
									color=discord.Color.green()))
		else:
			return await ctx.send(embed=discord.Embed(title="Missing Permissions.", color=discord.Color.dark_red()))

	@staticmethod
	def dictify(content: iter, keys: iter) -> dict:
		"""Returns an ordered dict."""
		_ = {}
		x = 0
		for item in content:
			_[item] = keys[x]
			x += 1
		return _

	@commands.is_owner()
	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	@commands.bot_has_permissions(administrator=True)
	async def stealemoji(self, ctx, emoji: discord.PartialEmoji, *, name = None):
		name = name if name else emoji.name
		x = await ctx.guild.create_custom_emoji(name=name, image=await emoji.url.read())
		return await ctx.send('​`' + str(x) + '​`')

	@commands.command(name="lgmtfy", aliases=['askgoogle', 'google', 'searchit'])
	async def lajanfp(self, ctx, *, text: str):
		""""""
		url = urllib.parse.quote(text, safe="")
		realurl = f"https://lmgtfy.com/?q={url}"
		if len(realurl) > 2000:
			if len(realurl) > 2048:
				await ctx.send(f"URL too long. shortening.", delete_after=5)
				realurl = realurl[:2000]
				e = None
			else:
				e = discord.Embed(
					title=realurl if len(realurl) < 256 else "Click for your link", url=realurl, color=ctx.author.color
				)
				realurl = None
		else:
			e = None
			if len(realurl) <= 1998:
				realurl = f"<{realurl}>"
		await ctx.send(realurl, embed=e, delete_after=60)

	@commands.command(name="userinfo", aliases=['u', 'ui', 'user'])
	@commands.bot_has_permissions(embed_links=True)
	async def userinfo(self, ctx, *, user: typing.Union[discord.Member, discord.User, int] = None):
		"""Gets a user's information. Preferably provide an ID, but mention/name+discrim will work too."""
		user = user if user else ctx.author
		emotes = {
			'boost': '<:eeboost:645601558071083069>',
			'join': '<:add:645602538774855711>',
			'leave': '<a:bye:645602671725641728>',
			'mobile': '\U0001f4de',
			'create': '<:eejoin_arrow:645603094901555231>',
			'activity': '\U0001f3b2'
		}
		e = discord.Embed(color=discord.Color.orange(), description="<a:loading:642876948061618214>"
																	" Loading User Info.")
		message = await ctx.send(embed=e)
		if isinstance(user, int):
			try:
				user = await self.bot.fetch_user(user)
			except (discord.HTTPException, discord.Forbidden, discord.NotFound):
				return await message.edit(embed=discord.Embed(title="User not found.", color=discord.Color.red()))

		rank = None
		sg = self.bot.get_guild(606866057998762023)
		if user not in sg.members:
			rank = None
		else:
			_user = user
			_ctx = ctx
			_ctx.guild = sg
			user = await commands.MemberConverter().convert(_ctx, str(user))
			role = sg.get_role(619296110585970691)  # Bug Catcher
			if user in role.members:
				rank = '\U0001f41b __Bug Hunter__'
			role = sg.get_role(631741181424041984)  # Guardian Support
			if user in role.members:
				rank = '\U0001f4ac __Bot Support__'
			role = sg.get_role(625584831320948737)  # Bot Mod
			if user in role.members:
				rank = '\U0001f528 __Bot Moderator__'
			role = sg.get_role(622077418642866176)  # dev
			if user in role.members:
				rank = '<:eeconsole:645630945059143710> __Developer__'
			user = _user  # return back to normal
		mutual = len([x for x in self.bot.guilds if user in x.members])
		prem = 'N/A'
		joined = 'N/A'
		top = 'N/A'
		self.bot.joinpos = 'N/A'
		warns = 'N/A'
		if isinstance(user, discord.Member):
			smembers = list(sorted(ctx.guild.members, key=lambda a: a.joined_at))
			self.bot.joinpos = None
			found_joined = discord.utils.find(lambda u: u.id == user.id, smembers)
			if found_joined:
				self.bot.joinpos = smembers.index(found_joined)
			else:
				self.bot.joinpos = "unknown"
			top = user.top_role.mention
			if user.premium_since:
				prem = f"{user.premium_since.strftime('%a %d %B %Y, %H:%M UTC')}"
			else:
				prem = 'N/A'
			warns = '__W.I.P__'
			joined = f"{emotes['join']} {user.joined_at.strftime('%a %d %B %Y, %H:%M UTC')}"
		created = f"{emotes['create']} {user.created_at.strftime('%a %d %B %Y, %H:%M UTC')}"
		av = user.avatar_url_as(static_format='png')
		e = discord.Embed(
			title=f"{user}'s information:",
			description=f"**User ID:** `{user.id}`\n**Created at:** {created}\n**Joined At:** {joined}\n**Join"
			            f" Position:** {self.bot.joinpos}\n**Boosted since:** {prem}\n**Avatar URL:** {av} (preview in thumbnail)"
			            f"\n**Top Role:** {top}\n**Warns:** {warns}\n\n**Mutual Guilds:** {mutual}\n"
			            f"{'' if not rank else f'**Rank:** {rank}'}",
			color=user.color if str(user.color) != '#000000' else ctx.me.color,
			timestamp=user.created_at
		)
		e.set_thumbnail(url=str(av))
		return await message.edit(embed=e)

	async def get_response(self, ctx, *, toSend: str = None, del_after: bool = False, y_n: bool = False,
						   timeout: int = None) -> typing.Union[str, bool]:
		"""Gets the response from a wait_for

		Will return boolean if timeout reached with no response."""
		if ctx.author.bot:
			return False
		msg = None
		if toSend:
			msg = await ctx.send(toSend)

		def check(message):
			return ctx.author == message.author and ctx.channel == message.channel

		try:
			waited = await self.bot.wait_for('message', check=check, timeout=timeout)
		except asyncio.TimeoutError:
			if msg:
				await msg.delete()
			return False  # unanswered
		content = str(waited.content)
		if y_n:
			if content.lower().startswith("y"):
				if msg:
					await msg.delete()
				if del_after:
					await waited.delete()
				return True
			else:
				if msg:
					await msg.delete()
				if del_after:
					await waited.delete()
				return False
		else:
			if msg:
				await msg.delete()
			if del_after:
				await waited.delete()
			return content

	def haswon(self, stuff: dict, symbol):
		# horizontal
		if stuff["1"] == stuff["2"] and stuff["2"] == stuff["3"] and stuff['1'] == symbol:
			return True
		elif stuff["4"] == stuff["5"] and stuff["5"] == stuff["6"] and stuff["4"] == symbol:
			return True
		elif stuff["7"] == stuff["8"] and stuff["8"] == stuff["9"] and stuff["7"] == symbol:
			return True

		# diagonal
		elif stuff["1"] == stuff["5"] and stuff["9"] == stuff["5"] and stuff["1"] == symbol:
			return True
		elif stuff['3'] == stuff['5'] and stuff['5'] == stuff['7'] and stuff['3'] == symbol:
			return True

		# vertical
		elif stuff["1"] == stuff["4"] and stuff["4"] == stuff["7"] and stuff["1"] == symbol:
			return True
		elif stuff["2"] == stuff["5"] and stuff['5'] == stuff['8'] and stuff['8'] == symbol:
			return True
		elif stuff["3"] == stuff["6"] and stuff["6"] == stuff['9'] and stuff['3'] == symbol:
			return True

		else:  # no matches
			return False

	@commands.command(aliases=['tic', 'tac', 'toe', 'ttt'])
	@commands.bot_has_permissions(manage_messages=True, )
	@commands.max_concurrency(1, commands.BucketType.channel, wait=True)
	@commands.cooldown(1, 60, commands.BucketType.guild)
	async def tictactoe(self, ctx, otherUser: typing.Optional[discord.Member] = None, player_1_symbol: str = "x",
	                    player_2_symbol: str = "o"):
		"""Play a game of tictactoe!

		Leave "OtherUser" Blank to play against me!"""
		if ctx.author == self.bot.user:
			return await ctx.send("Some fucked up shit just happened and this command just ran away it was that broken."
			                      " Please tell my dev that somehow ctx.author is self.bot.")

		winner = None
		otherUser = otherUser or self.bot.user
		if player_1_symbol[:1] == player_2_symbol[:1]:
			await ctx.send("Symbols can't be the same. Randomising.")
			player_2_symbol = random.choice(list(string.punctuation))
		if (otherUser.bot or otherUser == ctx.author) and otherUser != self.bot.user:
			return await ctx.send("You can't challenge them. Either they are a bot or they are you.")
		default = ' '
		board = {
			"1": default,
			"2": default,
			"3": default,
			"4": default,
			"5": default,
			"6": default,
			"7": default,
			"8": default,
			"9": default
		}
		display = "```\n+---+---+---+\n| {o} | {tw} | {th} |\n| {fo} | {fi} | {si} |\n| {se} | {ei} | {ni} |" \
		          "\n+---+---+---+\n```".format(o=board['1'], tw=board['2'], th=board['3'], fo=board['4'],
		                                        fi=board['5'], si=board['6'],
		                                        se=board['7'], ei=board['8'], ni=board['9'])
		first = random.choice([ctx.author, otherUser])
		second = [ctx.author, otherUser]
		second.remove(first)  # gets the user not chosen to go first.
		second = second[0]
		cctx = ctx.author.mention
		_ctx = copy.copy(ctx)
		_ctx.author = otherUser
		if otherUser != self.bot.user:
			confirmed = await self.get_response(_ctx, toSend=f"{otherUser.mention}: {cctx} has challenged"
			                                                 f" you you to a game of tictactoe!\nDo you accept?\n*reply "
			                                                 f"with yes or no within 2 minutes!*",
			                                    del_after=True, y_n=True, timeout=120)
		else:
			confirmed = True
		if not confirmed:
			return await ctx.send(f"Match cancelled - opponent did not accept, or didn't respond in time.")
		else:
			e = discord.Embed(title="Board:", description=display, color=discord.Color.dark_orange())
			if otherUser == self.bot.user:
				om = False
			else:
				om = otherUser.is_on_mobile()
			if not any([ctx.author.is_on_mobile, om]):
				ind = ''
				e.add_field(name="how to play?", value=f"To play:\n1) Wait until it is your turn\n2) When prompted,"
				                                       f" say the digit of the box you want to change (e.g: if i "
				                                       f"wanted to change top right, it would be `3`. "
				                                       f"Bottom right would be 9, bottom left 7, etc)\n3) wait for "
				                                       f"the dodgey maths to do its magic\n4) other player's turn.",
				            inline=False)
			else:
				ind = '```\n+-+-+-+\n|1|2|3|\n|4|5|6|\n|7|8|9|\n+-+-+-+\n```\n\n'
			player_1_symbol = player_1_symbol[:1]
			player_2_symbol = player_2_symbol[:1]
			players = {
				first: player_1_symbol,
				second: player_2_symbol
			}
			e.add_field(name="index:", value=f"{ind}Player 1's "
											 f"symbol: `{player_1_symbol}`\nPlayer 2's symbol: `{player_2_symbol}`\nPlayer 1: {first}\nPlayer 2: {second}",
						inline=False)

			status = await ctx.send(embed=e)
			turn = await ctx.send(f"{first.mention} is going first!")
			playing = first
			idle = second
			log = f"{first} went first."
			while True:
				await turn.edit(content=f"{playing.mention} is playing.")
				can = [x for x, y in board.items() if y == ' ']
				if len(can) == 0:
					self.bot.winner = None
					break  # finished, no more spots.
				_ctx = ctx
				_ctx.author = playing
				log += f"\n{playing} is now playing"
				if playing.id != self.bot.user.id:
					where = await self.get_response(_ctx, toSend=f"Available spots: {', '.join(can)} ({len(can)})",
													del_after=True, timeout=60)
				else:
					where = str(random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9]))
				if where is False:
					return await turn.edit(content=f"The game timed out. {idle.mention} wins!")
				else:
					if not where.isdigit() and where[:1] not in board.keys():
						await turn.edit(content=f"{playing.mention}: that's not a valid option! try again!")
						await asyncio.sleep(1)
						continue
					else:
						where = where[:1]
						if board[where] != " " and board[where] == players[idle]:
							log += f"\n{playing.mention} tried to claim {where}, but failed."
							await turn.edit(content=f"{playing.mention}: That position is already claimed! Try again")
							await asyncio.sleep(1)
							continue
						elif board[where] != " ":  # you're welcome Minion
							await turn.edit(content="You already claimed that one!")
							continue
						else:
							board[where] = players[playing]
							log += f"\n{playing} claimed {where}."
							display = "```\n+---+---+---+\n| {o} | {tw} | {th} |\n| {fo} | {fi} | {si} |\n| {se} | {ei} | {ni} |" \
									  "\n+---+---+---+\n```".format(o=board['1'], tw=board['2'], th=board['3'],
																	fo=board['4'],
																	fi=board['5'], si=board['6'],
																	se=board['7'], ei=board['8'], ni=board['9'])
							e.description = display
							await status.edit(embed=e)
							await asyncio.sleep(1)
				_p = playing
				if self.haswon(board, players[_p]):
					self.bot.winner = _p
					break
				elif self.haswon(board, players[idle]):
					self.bot.winner = idle
					break
				playing = idle
				idle = _p
		paginator = PaginatorEmbedInterface(self.bot, commands.Paginator(prefix='', suffix=''))
		await paginator.add_line(
			f"Overview:\n{f'**{self.bot.winner.mention} Won!**' if self.bot.winner else '**Draw!**'}\n\nLog:\n")
		for line in log.splitlines(keepends=False):
			await paginator.add_line(line)
		await paginator.add_line(f"**{self.bot.winner.mention} wins!**" if self.bot.winner else '**Draw!**')
		await paginator.send_to(ctx.channel)
		await turn.delete()
		e = discord.Embed(
			title="Game Over. Overview:",
			description="```\n+---+---+---+\n| {o} | {tw} | {th} |\n| {fo} | {fi} | {si} |\n| {se} | {ei} | {ni} |"
						"\n+---+---+---+\n```".format(o=board['1'], tw=board['2'], th=board['3'],
													  fo=board['4'],
													  fi=board['5'], si=board['6'],
													  se=board['7'], ei=board['8'], ni=board['9']),

		)
		await status.edit(embed=e)

	@commands.command()
	@commands.is_owner()
	async def rcd(self, ctx, command: str):
		cmd = self.bot.get_command(command.lower())
		if cmd is None:
			return await ctx.send("Nu huh.")
		else:
			cmd.reset_cooldown(ctx)
			return await ctx.send("mhm fine.")

	async def get_guild_info(self, guild: discord.Guild):
		"""Get a guild's info and return a fully formatted, ready-made embed fields list.
		returns: [{'name': *name*, 'value': *value*}]"""

		member_info = ""
		bots = 0
		humans = 0
		admins = 0
		total_member_count = guild.member_count
		for member in guild.members:
			if member.bot:
				bots += 1
				continue
			else:
				humans += 1
				if member.guild_permissions.administrator:
					admins += 1
		member_info += f"{total_member_count} total, {bots} bots, {humans} humans ({admins} admins)"

		us = '🇺🇸'
		regions = {
			# these look like weird font letters, but they are actually the flag emojis (when sent in discord).
			'amsterdam': '🇳🇱',
			'brazil': '🇧🇷',
			'eu_central': '🇪🇺',
			'eu_west': '🇪🇺',
			'frankfurt': '🇩🇪',
			'hongkong': '🇨🇳',
			'india': '🇮🇳',
			'japan': '🇯🇵',
			'london': '🇬🇧',
			'russia': '🇷🇺',
			'singapore': '🇸🇬',
			'southafrica': '🇿🇦',
			'sydney': '🇦🇺',
			'us_central': us,
			'us_east': us,
			'us_south': us,
			'us_west': us
		}
		features_dict = {
			"VIP_REGIONS": f'\U00002b50{str(guild.region).lower().replace("-", "_")}',
			"COMMERCE": '\U0001f6d2',
			'NEWS': '\U0001f4f0',
			'BANNER': '\U0001f3f3',
			'ANIMATED_ICON': '',
			'DISCOVERABLE': self.emojis['search'],
			'LURKABLE': self.emojis['lurk'],
			'MORE_EMOJI': '\U00002795\U0001f604',
			'PARTNERED': self.emojis['partner'],
			'VERIFIED': self.emojis['verified'],
			'INVITE_SPLASH': f'{self.emojis["invite"]}\U0001f3f3',
			'VANITY_URL': self.emojis['invite']
		}
		features = guild.features
		fs = ""
		for f in features:
			fs += f"{features_dict[str(f)]} {str(f).lower().replace('_', ' ')}\n"
		region = f"{regions.get(str(guild.region).lower().replace('-', '_')) or ':question:'} {str(guild.region)}"
		verif = str(guild.verification_level).replace('_', ' ')
		notif = str(guild.default_notifications).replace('_', ' ').replace('NotificationLevel.', ' ')
		filter = str(guild.explicit_content_filter).replace('_', ' ')

		system_channel = '#' + str(guild.system_channel) if guild.system_channel else None
		system_channel_flags = []
		for flag, value in guild.system_channel_flags:
			system_channel_flags.append(
				(str(flag).replace('_', ' '), self.emojis['toggles']['on'] if value else self.emojis['toggles']['off']))
		system_channel_flags = ' | '.join([f"{x}: {y}" for x, y in system_channel_flags])

		emojis = len(guild.emojis)

		afk_channel = guild.afk_channel
		afk_timeout = fix_time(guild.afk_timeout)

		icon = str(guild.icon_url_as(static_format='png')) if guild.icon_url else None

		nitro_level = f"Nitro Level: {guild.premium_tier}"
		nitro_subs = f"Boosters: {guild.premium_subscription_count}"

		voice = len(guild.voice_channels)
		text = len(guild.text_channels)
		cat = len(guild.categories)
		ci = f"<:category:614652379278606376> {cat} categories\n <:text_channel:614652616403845120>{text} text channels" \
		     f"\n<:voice_channel:614652616437268636> {voice} voice channels"
		created = ago_time(guild.created_at)
		stuff = []
		stuff.append({"name": "member info", "value": member_info})
		stuff.append({"name": "channel info", "value": ci})
		stuff.append({"name": "region", "value": region})
		stuff.append({"name": "verification level", "value": verif})
		stuff.append({"name": "notification level", "value": notif})
		stuff.append({"name": "filter level", "value": filter})
		stuff.append(
			{"name": "system channel", "value": f"{system_channel}\nSystem channel flags: {system_channel_flags}"})
		stuff.append({"name": "emojis", "value": emojis})
		stuff.append({"name": "afk info",
		              "value": f"Channel: {afk_channel.mention if afk_channel else None}\nTimeout: {afk_timeout}"})
		stuff.append({"name": "nitro boost info", "value": f"{nitro_level}\n{nitro_subs}"})
		stuff.append({"name": "created", "value": created})
		stuff.append({"name": "icon url", "value": icon})
		return stuff

	@commands.command(aliases=['si', 'sinfo', 'serveri'])  # ripped from supertool
	async def serverinfo(self, ctx, *, guild: DynamicGuild() = None):  # Commented & partially rewritten by Minion3665
		"""Get a server's information
		Provide a server id/name after the command to get their information."""
		if not guild:  # If the guild wasn't supplied
			guild = ctx.guild  # Get the current guild as the guild instead

		async with ctx.channel.typing():  # Show the typing status until I have sent the serverinfo
			fields_list = await self.get_guild_info(guild)  # Get the guild information
			if len(fields_list) > 25:  # If the embed length is too long
				return await ctx.send(f"Unable to display data with reason: ListTooLong "
				                      f"(data received was larger then the discord embed field limit.)")  # If data
			# is too long, return with an error message (TODO: Make it send anyway later)
			embed = discord.Embed(title=guild.name, description=str(guild.id), color=guild.owner.color,
			                      timestamp=guild.created_at)  # Create an embed
			for field in fields_list:  # Enumerate over the pieces of server information
				embed.add_field(name=field['name'], value=field['value'],
				                inline=False)  # Add a field displaying a piece of server information
				if field['name'] == 'icon url' and field[
					'value']:  # If the current field is the icon URL (and it actually exists (i.e. isn't None))
					embed.set_thumbnail(url=str(field['value']))  # Set the thumbnail to the server icon
		return await ctx.send(embed=embed)  #

	# Send the embed

	@commands.command(name="statuses")
	async def setuspie(self, ctx, *, guild: typing.Union[DynamicGuild, str] = None):
		guild = guild or ctx.guild or self.bot.get_guild(606866057998762023)
		if isinstance(guild, str):
			if guild.lower() == "total":
				it = list(set(self.bot.get_all_members()))
			else:
				return await ctx.send("no")
		else:
			it = guild.members
		if ctx.channel.permissions_for(ctx.me).attach_files:
			labels = ["online", "idle", "dnd", "offline", "streaming"]
			on = 0
			id = 0
			dn = 0
			of = 0
			st = 0
			for member in it:
				member: discord.Member
				if member.activity:
					if "streaming" in str(member.activity.type):
						st += 1
						continue
				if member.status == discord.Status.online:
					on += 1
				elif member.status == discord.Status.idle:
					id += 1
				elif member.status == discord.Status.dnd:
					dn += 1
				elif member.status in [discord.Status.offline, discord.Status.invisible]:
					of += 1
			member: discord.Member = ctx.author
			if member.status == discord.Status.online:
				explode = (0.1, 0, 0, 0, 0)
			elif member.status == discord.Status.idle:
				explode = (0, 0.1, 0, 0, 0)
			elif member.status == discord.Status.dnd:
				explode = (0, 0.1, 0, 0, 0)
			elif member.status == discord.Status.offline:
				explode = (0, 0, 0, 0.1, 0)
			else:
				if member.activity:
					if "streaming" in str(member.activity.type):
						explode = (0, 0, 0, 0, 0.1)
					else:
						explode = (0, 0, 0, 0, 0)
				else:
					explode = (0, 0, 0, 0, 0)
			stuff = []
			for thing in (on, id, dn, of, st):
				if thing >= 1:
					stuff.append(thing)
			labels = labels[:len(stuff)]
			explode = tuple(list(explode)[:len(stuff)])
			fig = plt.figure()
			ax = fig.add_axes([0, 0, 1, 1])
			ax.axis('equal')
			colours = ["green", "yellow", "red", "grey", "purple"]

			ax.pie(stuff, explode=explode, shadow=True, labels=labels, autopct='%1.2f%%', colors=colours)
			ax.legend()
			plt.savefig("./image.png", edgecolor='gray', facecolor=(0.44, 0.47, 0.51, 0.5))
			file = discord.File("./image.png")
		else:
			file = None
		msg = ""
		await ctx.send(msg, file=file)
		if file:
			# cleanup
			os.remove("./image.png")

	@commands.command(name="pretty")
	@commands.is_owner()
	async def beautify(self, ctx, *, thing: str):
		stuff = {"bot": self.bot, "ctx": ctx, "json": json, "discord": discord, "commands": commands,
		         "asyncio": asyncio}
		magic = eval(thing, stuff)
		nice = json.dumps(magic, indent=2)
		paginator = commands.Paginator(prefix="```json")
		for line in nice.splitlines():
			paginator.add_line(line[:1985])
		for page in paginator.pages:
			await ctx.send(page)

	@commands.command()
	@commands.bot_has_permissions(embed_links=True, send_messages=True, external_emojis=True, add_reactions=True, manage_messages=True)
	@commands.has_permissions(manage_messages=True, add_reactions=True, external_emojis=True)
	async def poll(self, ctx, to: typing.Optional[discord.TextChannel] = None,
	               roles_to_ping: commands.Greedy[discord.Role] = None,
	               use_yes_or_no: typing.Optional[bool] = False,
	               *, question: str):
		"""Makes a poll.
		If `to` is provided, it must be a text channel. Otherwise, it defaults to the current channel.
		If `use_yes_or_no` is True, it will use tick or cross instead of just numbering them.

		QUESTION must be a list of options, separated by `;`.
		Example: g!poll __TITLE__;option 1?;option 2; opt.3;four;what;
		This would give you 5 options, with the emojis 1 2 3 4 5

		g!poll true Should I eat crisps?;yes;no
		would add cross and tick emojis."""
		to = to or ctx.channel
		if not roles_to_ping:
			roles_to_ping = []
		else:
			roles_to_ping = [x.mention for x in roles_to_ping if x.mentionable]
		try:
			title, option_1, option_2, *options = question.split(";")
			if use_yes_or_no and len(options) != 0:
				await ctx.send(f"Only 2 options can be provided if `use yes or no` is on. Only the first two options "
				               f"will be used, others will be ignored.", delete_after=10)
				options = []
			elif len(options) + 2 > 20:
				await ctx.send(f"Discord has a limit of 20 reactions. For now, I have limited you to the first 20 options provided.")
				options = options[:18]
		except ValueError:
			things = question.split(";")
			if len(things) == 1:
				return await ctx.send(f"You provided a title, but forgot at least 2 options!")
			elif len(things) == 2:
				return await ctx.send("You must have at least 2 options!")
			else:
				return await ctx.send(f"Only {len(things)} arguments were provided")

		emojislist = [f'{n}\N{combining enclosing keycap}' for n in range(10)] + ["\N{keycap ten}"]
		for i in range(11, 21):
			emojislist.append(discord.utils.get(self.bot.get_guild(606866057998762023).emojis, name=str(i)))
		y_n = ["\N{WHITE HEAVY CHECK MARK}", "\N{CROSS MARK}"]
		used_emojis = [y_n[0] if use_yes_or_no else emojislist[0], y_n[1] if use_yes_or_no else emojislist[1]]
		emojis = {
			option_1: y_n[0] if use_yes_or_no else emojislist[0],
			option_2: y_n[1] if use_yes_or_no else emojislist[1]
		}
		for n, opt in enumerate(options, start=2):
			emojis[opt] = emojislist[n]
			used_emojis.append(emojislist[n])
		if len(title.split("\n")) > 0:
			title, *description = title.split("\n")
		else:
			description = [""]
		nl = "\n"
		content = f"**{title}**\n{nl.join(description)}\n\n"
		for option, emoji in emojis.items():
			content += f"{emoji}: {option}\n"
		content += f"\n\n*Add the corresponding reaction below!*"
		e = discord.Embed(
			title=f"New poll by {ctx.author.display_name}:",
			description=content,
			color=ctx.author.color,
			url=ctx.message.jump_url,
			timestamp=datetime.datetime.utcnow()
		)
		e.set_footer(icon_url=self.bot.user.avatar_url_as(format="png"), text="Polls command by Guardian | g!invite ")
		e.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url_as(static_format="png"))
		cperm = to.permissions_for(ctx.me)
		reqperms = [cperm.send_messages, cperm.embed_links, cperm.add_reactions, cperm.use_external_emojis, cperm.manage_messages]
		if all(reqperms):
			msg = await to.send(', '.join(roles_to_ping), embed=e)
			for emoji in used_emojis:
				asyncio.create_task(msg.add_reaction(emoji))
			if to.id == ctx.channel.id:
				await ctx.message.delete()
		else:
			await ctx.send(f"{emojis[1]} Missing one or more of `send messages`, `embed links`, `add reactions`"
			               f" and `manage messages` permissions in {to.mention}!")

	@commands.command(name="afk")
	async def afk_toggle(self, ctx, *, reason: typing.Union[bool, commands.clean_content] = False):
		"""Toggles AFK mode
		if you're afk, all incoming pings will be sent to your DMs and the person who pinged you will be notified
		that you are afk with :reason:.

		set reason to `off` to disable"""
		if not reason:
			with open("./data/afk.json") as read:
				data = json.load(read)
				entry = data.get(str(ctx.author.id))
				if entry is None:
					return await ctx.send(f"You are not AFK.")
				else:
					start = datetime.datetime.fromisoformat(entry["start"])
					pings = '\n'.join([f"<#{x}>: <{y}>" for x, y in entry["pings"].items()])
					e = discord.Embed(
						title="Your 5 most recent pings",
						color=discord.Color.red(),
						timestamp=start,
						description=pings
					)
					try:
						await ctx.author.send(embed=e, delete_after=3600)
					except discord.Forbidden:
						pass
					e = discord.Embed(
						title="Welcome Back!",
						description=f"You were AFK for: **{ago_time(start).replace('ago', '')}**",
						color=discord.Color.blue()
					)
					e.set_footer(text=f"You received {len(entry['pings'])} mentions in that time.")
					await ctx.send(embed=e)
					del data[str(ctx.author.id)]
					with open("./data/afk.json", "w") as write:
						json.dump(data, write, indent=2)
		else:
			with open("./data/afk.json") as read:
				data = json.load(read)
				entry = data.get(str(ctx.author.id))
				if entry is None:
					await ctx.send(f"Set your AFK reason to `{reason[:256]}`")
					with open("./data/afk.json", "w") as write:
						data[str(ctx.author.id)] = {
							"pings": {},
							"start": str(datetime.datetime.utcnow()),
							"until": None,
							"reason": str(reason[:256])
						}
						json.dump(data, write, indent=2)
				else:
					await ctx.send(f"Updated your AFK reason.")
					data[str(ctx.author.id)]["reason"] = str(reason)[:256]
					with open("./data/afk.json", "w") as write:
						json.dump(data, write, indent=2)

	@commands.Cog.listener()
	async def on_message(self, message: discord.Message):
		if message.author.bot:
			return
		with open("./data/afk.json") as read:
			data = json.load(read)
		afk = []
		for member in list(set(message.mentions)):
			entry = data.get(str(member.id))
			if entry:
				afk.append(discord.Embed(title=f"{member.display_name} is AFK!",
				                         description=f"Reason: {entry['reason'][:256]}",
				                         color=member.color,
				                         timestamp=datetime.datetime.fromisoformat(entry["start"])))
				data[str(member.id)]["pings"][str(message.channel.id)] = message.jump_url
				try:
					await member.send(f"[AFK Notification] You were mentioned in {message.channel.mention} by "
					                  f"{message.author} [<{message.jump_url}>]:\n\n>>> {message.content[:1000]}")
				except discord.Forbidden:
					pass
			else:
				continue
		ctx = await self.bot.get_context(message)
		if len(afk) > 3:
			await ctx.send(f"{len(afk)}/{len(message.mentions)} members you mentioned are currently marked as AFK.",
			               delete_after=30)
		elif len(afk) > 0:
			for embed in afk:
				await ctx.send(embed=embed, delete_after=30)
				await asyncio.sleep(1)
		with open("./data/afk.json", "w") as write:
			json.dump(data, write, indent=2)

	@commands.Cog.listener(name="on_message_edit")
	async def reping(self, old: discord.Message, new: discord.Message):
		"""if len(old.mentions) < len(new.mentions):
			lst = set(old.mentions + new.mentions)
			await new.channel.send(' '.join([x.mention for x in lst]), delete_after=0.000000001)"""
		if old.content == new.content: return
		ctx: commands.Context = await self.bot.get_context(new)
		if ctx.valid:
			await self.bot.invoke(ctx)

	@commands.command(name="reddit")
	@commands.cooldown(1, 5, commands.BucketType.user)
	async def red(self, ctx, sub: str = "memes", *, sort: str = "hot"):
		"""Scowers reddit, you social inlet"""
		sub = sub[2:].lower() if sub.startswith("r/") else sub.lower()
		BASE = "https://www.reddit.com/r/{}/{}.json"
		try:
			response, status, data, error = await niceweb.get(BASE.format(sub, sort.lower()), mode="very strict")
		except Exception as e:
			await ctx.send(f"HTTP Exception: {str(e)} ({type(e).__name__})")
			raise
		else:
			if error:
				return await ctx.send(f"HTTP Exception with complete response, status {status}: {str(error)}")
			elif status == 404:
				return await ctx.send(f"404: Unable to sort by {sort}.", discord.AllowedMentions())
			else:
				e = discord.Embed(
					colour=0xff4500
				)
				embeds = []
				for post in data["data"]["children"]:
					info = post["data"]
					if info["over_18"] and not ctx.channel.is_nsfw(): continue

					text = info["selftext"]
					if len(text) >= 2000:
						b = "https://reddit.com"
						b += info["permalink"]
						shorten_len = len(b) + 15
						text = text[:2000-shorten_len] + f"... [Read More]({b})"
					e = discord.Embed(
						title=info["title"],
						description=text,
						color=0xff4500,
						url=info["url"]
					)
					e.set_author(name=info["author_fullname"])
					e.set_image(url=info["url"] or discord.Embed.Empty)
					embeds.append(e)
				return await RedditMenu(embeds, delete_message_after=True).start(ctx, wait=True)


def setup(bot):
	bot.add_cog(Utils(bot))
