import asyncio
import datetime
import random
import time

import discord
from discord.ext.commands import Cog, bot_has_permissions, command
from discord.utils import escape_mentions
from discord.ext import commands  # i give up
import typing
from .utils import entry_helper
from jishaku.paginators import PaginatorEmbedInterface

from .utils import config
import matplotlib.pyplot as mpl
import os


class QuitInEmbeddedFunction(Exception):
	pass


class EventsTest(Cog):
	def __init__(self, bot):
		self.bot = bot
		self.stats = config.read("./data/meta.json")  # for command tracking

	def cog_unload(self):
		# we need to dep the stored stats for commands. Hopefully it gets reloaded, not *un*loaded.
		data = config.read("./data/meta.json")
		data.update(self.stats)
		config.write("./data/meta.json", data)

	@staticmethod
	def getValue(ctx_like_obj, thing: str):
		data = config.read("./data/core.json")
		if data.get(str(ctx_like_obj.guild.id)):
			d = data[str(ctx_like_obj.id)]
			if d.get(thing) is not None:
				return d.get(thing)
			else:
				raise KeyError(f"thing {thing} not found in keys. is it the right name?")
		else:
			return None

	@command(hidden=True)
	@bot_has_permissions(embed_links=True, attach_files=True)
	async def cmdstats(self, ctx):
		"""Gets command statistics."""
		x_pos = [i for i, _ in enumerate(self.stats.keys())]
		x = list(self.stats.keys())
		y_pos = list(self.stats.values())
		mpl.bar(x_pos, y_pos, 0.5, None)
		mpl.xlabel("Event")
		mpl.ylabel("Occurred")
		mpl.title("Command Statistics")
		mpl.xticks(x_pos, x)
		mpl.savefig("./data/stats.png")
		e = discord.Embed(color=discord.Color.orange())
		e.set_image(url="attachment://stats.png")
		await ctx.send(file=discord.File("./data/stats.png"), embed=e)
		# clear and remove file
		os.remove('./data/stats.png')

	async def get_log_channel(self, ctx_like_obj):
		"""
		gets the guilds modlog channel
		:param ctx_like_obj: must have `.guild`.
		:return:  discord.TextChannel or None
		"""
		data = config.read("./data/core.json")
		if data.get(str(ctx_like_obj.guild.id)):
			log = self.bot.get_channel(int(data[str(ctx_like_obj.guild.id)]["log channel"]))
			return log
		else:
			return None

	@staticmethod
	def check_if_enabled(ctx_like_obj, *, event: str):
		data = config.read("./data/core.json")
		if data.get(str(ctx_like_obj.guild.id)) is not None:
			d = data[str(ctx_like_obj.guild.id)]
			if d.get(event) is not None:
				return d[event]  # True/False
			else:
				return False
		else:
			return None

	@Cog.listener()
	async def on_message_delete(self, message):
		if not self.check_if_enabled(message, event='message_delete'):
			return
		log = await self.get_log_channel(message)
		at = message.created_at.strftime("%a %B %Y at %H:%Y UTC")
		author = f"{str(message.author)} ({message.author.id})"
		content = message.content.replace("[", "[\u200B").replace("|", "|\u200b")  # escapes hyperlinks and spoilers
		channel = f"{message.channel.mention} `#{message.channel.name}`"
		if log:
			embed = discord.Embed(
				title="Message Deleted!",
				description=f"**At**: {at}\n**In:** {channel}\n**Content:** {content}",
				color=message.author.color,
				timestamp=message.created_at
			)
			embed.set_author(name=author, icon_url=message.author.avatar_url_as(static_format='png'))
			await log.send(embed=embed)

	@Cog.listener()
	async def on_message_edit(self, old_message, new_message):
		if not self.check_if_enabled(new_message, event="message_edit"):
			return
		message = new_message
		log = await self.get_log_channel(message)
		at = message.created_at.strftime("%a %B %Y at %H:%Y UTC")
		author = f"{str(message.author)} ({message.author.id})"
		channel = f"{message.channel.mention} `#{message.channel.name}`"
		if log:
			embed = discord.Embed(
				title="Message Edited!",
				description=f"**At**: {at}\n**In:** {channel}",
				color=message.author.color,
				timestamp=message.edited_at,
				url=message.jump_url
			)

			content = old_message.content.replace("[", "[\u200B").replace("|",
																		  "|\u200b") if old_message.content >= 550 else old_message.content.replace(
				"[", "[\u200B").replace("|", "|\u200b")[:550] + '...'
			embed.add_field(name="Old message:", value=content, inline=False)
			content = new_message.content.replace("[", "[\u200B").replace("|", "|\u200b")
			content = content if content <= 550 else content[:550] + '...'
			embed.add_field(name="New Message:", value=content, inline=False)
			embed.set_author(name=author, icon_url=message.author.avatar_url_as(static_format='png'))
			await log.send(embed=embed)

	@Cog.listener()
	async def on_member_join(self, member):
		joined: datetime.datetime = member.created_at
		sday = datetime.datetime.utcnow() - datetime.timedelta(days=5)
		if sday <= joined:
			channel: discord.TextChannel = await self.get_log_channel(member)
			if channel:
				e = discord.Embed(
					title="Raid Prevention alert - Alt/Suspicious account alert!",
					description=f"{member.mention} (`{member.id}`) was created 5 or less days ago!",
					color=discord.Color.orange(),
					timestamp=joined
				)
				e.set_footer(text="Severity: medium | Account created: ")
				await channel.send(embed=e)
			return

	@commands.command(name="eConfig", aliases=['EC', 'configevents', 'configlog'])
	@commands.has_permissions(manage_channels=True, manage_guild=True)
	@commands.bot_has_permissions(embed_links=True, manage_messages=True, add_reactions=True)
	async def econfig(self, ctx):
		"""Configure and toggle what events are logged."""
		reactions = {
			"0": "0\N{combining enclosing keycap}",
			"1": "1\N{combining enclosing keycap}",
			"2": "2\N{combining enclosing keycap}",
			"3": "3\N{combining enclosing keycap}",
			"4": "4\N{combining enclosing keycap}",
			"5": "5\N{combining enclosing keycap}",
			"6": "6\N{combining enclosing keycap}",
			"7": "7\N{combining enclosing keycap}",
			"8": "8\N{combining enclosing keycap}",
			"9": "9\N{combining enclosing keycap}",
			"10": "\N{keycap ten}"
		}
		data = config.read("./data/core.json")[str(ctx.guild.id)]
		try:
			meta = config.read("./data/meta.json")['events']
		except KeyError:
			return await ctx.send(f"Error loading meta.json: key 'events' not found.")

		async def add_reactions():
			for re in list(reactions.values())[:len(data['events'].keys())]:
				await msg.add_reaction(re)

		async def wait_for_response() -> (str, bool):
			def c(r, u):
				return r.message == msg and str(r.emoji) in reactions.values()

			try:
				r, u = await self.bot.wait_for('reaction_add', check=c, timeout=60)
			except asyncio.TimeoutError:
				await msg.clear_reactions()
				raise QuitInEmbeddedFunction()
			else:
				for num, reaction in reactions.items():
					if reaction == str(r.emoji):
						return num, data[meta[num]['name']]
					else:
						continue
				else:
					raise OverflowError(
						"LogicError - ran out of iterations in econfig\\name, toggle = wait_for"
						"_response()\\wait_for_response()\\else\\for num, reaction in reactions.items()"
					)

		e = discord.Embed(title="Current configuration:", description='\n'.join([f'{x}: {y}' for x, y in data['events'].items()]), color=discord.Colour.blue())
		msg = await ctx.send(embed=e)
		await add_reactions()
		name, value = await wait_for_response()
		await ctx.send(f"{name} {value} `{name} {value}`")

	@Cog.listener()
	async def on_message(self, message):
		"""Edward Integration"""
		if message.author.id == 647930077132357675:
			ctx = await self.bot.get_context(message)
			try:
				await self.bot.invoke(ctx)
			except Exception as error:
				await ctx.send(f"Error while invoking: `{escape_mentions(str(error))}`")

	@Cog.listener()
	async def on_command(self, ctx):
		self.stats['run'] += 1

	@Cog.listener()
	async def on_command_error(self, ctx, error):
		self.stats["errors"] += 1

	@Cog.listener()
	async def on_command_completion(self, ctx):
		self.stats['successful'] += 1

	@Cog.listener()
	async def on_mod_action(self, ctx, event: str, *, punished: typing.Union[discord.Member, discord.User]):
		if event in ['warn', 'unmute']:
			return
		else:
			data = config.read("./data/appeals.json")
			if data.get(str(ctx.guild.id)):
				guild = data[str(ctx.guild.id)]
				msg = f"You may appeal this action in the following methods:\n**DMAppeal:** `g!appeal " \
					  f"{ctx.guild.id} <above case ID>`"
				methods = list(guild.items())
				for method, value in methods:
					msg += f"**{method}:** __{value}__\n"
				try:
					msg += "\n\n*All of the above data is user-provided and we do not claim responsibility for it.*"
					await punished.send(msg)
				except (discord.Forbidden, discord.NotFound, Exception):
					return

	def resolve(self, thing):
		if isinstance(thing, list):
			return ', '.join(thing)
		elif isinstance(thing, bool):
			return str(thing)

	@commands.group(name="appeals", invoke_without_command=True)
	@commands.has_permissions(manage_roles=True, ban_members=True)
	async def seeappeals(self, ctx):
		"""Goes through and lists appeals sent through the bot."""
		data = config.read("./data/appeals.json")
		guild = data.get(str(ctx.guild.id))
		if guild is None:
			return await ctx.send(f"Appeals has not been set up. did you mean `{ctx.prefix}appeals setup`?")
		else:
			msg = await ctx.send(f"Loading")

			async def add_reactions():
				r = [
					'\U00002714',  # approve
					'\U000026a0',  # approve and caution
					'\U0000274c',  # deny
					'\U000027a1',  # skip
					'\U0001f6d1'   # block
				]
				for reaction in r:
					await msg.add_reaction(reaction)
					await asyncio.sleep(0.25)

			async def reject(reason: str = False):
				__content = content
				myembed = discord.Embed(
					title=f"Appeal denied.",
					description=f"Your appeal for {ctx.guild.name} (appeal ID {__content['appeal id']})"
								f" has been rejected.",
					color=discord.Color.red(),
					timestamp=datetime.datetime.utcnow()
				)
				if reason is False:
					mm = await ctx.send(f"Reason for rejection: ")
					reason = await self.bot.wait_for("message", check=lambda
						a: a.channel == ctx.channel and a.author == ctx.author)
					await mm.delete()
					try:
						await reason.delete()
					except:
						pass
				elif reason is not None:
					myembed.description += reason
				__user = self.bot.get_user(content["author id"])
				if __user:
					try:
						await __user.send(embed=myembed)
					except discord.Forbidden:
						pass
				data[str(ctx.guild.id)]["denied appeals"][appeal_id] = content
				del data[str(ctx.guild.id)]["appeals"][appeal_id]
				config.write('./data/appeals.json', data)

			async def block(author_id: int):
				data[str(ctx.guild.id)]["blocked members"].append(author_id)
				config.write('./data/appeals.json', data)
				await reject("\n\nBlocked from appealing. No further contact with this server through me is possible.")

			async def accept_with_reason():
				mm = await ctx.send(f"Reason for approval: ")
				reason = await self.bot.wait_for("message", check=lambda a: a.channel == ctx.channel and a.author == ctx.author)
				await mm.delete()
				try:
					await reason.delete()
				except:
					pass
				await approve(reason.content)

			async def approve(reason: str = None):
				_u = self.bot.get_user(content["author id"])
				if _u:
					try:
						tosend = f"\U0001f389 Your appeal #{appeal_id} in {ctx.guild.name} has been approved!"
						if content["type"] == 'ban':
							invite = await ctx.guild.create_invite(
								reason=f"Appeal {content['appeal id']} accepted by {ctx.author}")
							invite = invite.url
							tosend += f" You can re-join via the invite {invite}."
						else:
							tosend += f" You will be un-muted shortly."
						await _u.send(tosend)
						if reason:
							await _u.send(f"You have, however, received a caution: {reason}")
					except discord.Forbidden:
						pass
				_u = _u if _u else discord.Object(content["author id"])
				if content["type"] == 'ban':
					await ctx.guild.unban(_u, reason=f"Appeal #{appeal_id} accepted by {ctx.author}")
				else:
					_ctx = ctx
					_ctx.command = self.bot.get_command("unmute")
					await _ctx.invoke(_ctx.command, _u, reason=f"Appeal #{appeal_id} accepted bu {ctx.author}.")
				del data[str(ctx.guild.id)]["appeals"][str(appeal_id)]
				config.write('./data/appeals.json', data)

			_dict = guild
			for appeal_id, content in _dict['appeals'].items():
				await msg.clear_reactions()
				user = self.bot.get_user(content["author id"])
				user = str(user) if user else content["author id"]
				e = discord.Embed(
					title=f"Appeal for: {user}",
					color=discord.Color.blue()
				)
				e.add_field(name=f"case ID:", value=content['case id'], inline=False)
				casereason = content["reason"] if len(content["reason"]) <= 32 else content["reason"][:32] + '...'
				e.add_field(name="case details:", value=f"Type: {content['type']} | reason: {casereason}", inline=False)
				e.add_field(name="reason for appeal:", value=content["reason"][:1020], inline=False)
				e.add_field(name="\u200b", value="\u200b", inline=False)
				e.add_field(name="appeal ID:", value=content["appeal id"], inline=False)
				e.add_field(name="Total Appeals:", value=content["appeal no"], inline=False)
				await msg.edit(content=None, embed=e)
				await add_reactions()
				logic = {
					'\U00002714': approve,  # approve
					'\U000026a0': accept_with_reason,  # approve and caution
					'\U0000274c': reject,  # deny
					'\U000027a1': "continue",  # skip
					'\U0001f6d1': block  # block
				}
				r, u = await self.bot.wait_for("reaction_add",
											   check=lambda r, u: str(r.emoji) in logic.keys() and u == ctx.author and r.message.id == msg.id)
				emoji = str(r.emoji)
				if logic.get(str(r.emoji)):
					if callable(logic[str(r.emoji)]):
						await logic[emoji]()
					else:
						if str(logic[emoji]) == 'continue':
							continue
						else:
							await ctx.send(f"Alright buddy. Gonna be totally honest here, but I'm not sure what's "
										   f"happened here. Upon reading through my logic dict, I saw "
										   f"`logic[str(reaction.emoji)]` wasn't a function I could call!"
										   f" So, I've entered an unknown state. Please, tell my developer the"
										   f" following information:\n```{emoji} {r} {logic} {logic.get(emoji)}```")
							return

	@commands.command(name="appeal")
	@commands.dm_only()
	async def appeal(self, ctx):
		"""Appeals a punishment?."""
		msg = await ctx.send(f"What is the ID/name of the guild you are appealing?")

		def check(m):
			return m.author == ctx.author and m.guild is None
		guild = await self.bot.wait_for("message", check=check)
		guild = guild.content
		if guild.isdigit():
			guild = self.bot.get_guild(int(guild))
		else:
			for name in self.bot.guilds:
				_name = name.name
				if guild.lower() in _name.lower():
					guild = name
					break
			else:
				guild = None
		if guild is None:
			return await msg.edit(content=f"Guild not found.")
		await msg.edit(content=f"What was the case ID?")
		case_id = await self.bot.wait_for("message", check=check)
		cases = config.read("./data/core.json")
		valid = ["mutes", "bans"]

		async def get_value():  # this is so we can escape the double for easily
			for option in valid:
				for some_id, some_case in cases[str(guild.id)][option].items():
					if str(some_id) != case_id.content[:len(str(some_id))]:
						continue
					some_case["ctx"] = ctx
					some_case["case_id"] = some_id
					my_case = await entry_helper.Case.from_dict(some_case)
					if isinstance(my_case.target, (discord.User, discord.Member)):
						if my_case.target == ctx.author:
							return my_case.type.rstrip("s")
					else:
						if my_case.tartget == ctx.author.id:
							return my_case.type.rstrip("s")
		ttype = await get_value()
		await msg.edit(content=f"Why should you be un-punished?")
		reason = await self.bot.wait_for("message", check=check)
		data = config.read("./data/appeals.json")
		gdata = data.get(str(guild.id))
		if gdata is None:
			return await msg.edit(content="Guild has not set appeals up yet. Sorry :/")
		else:
			if ctx.author.id in gdata["blocked members"]:
				return await ctx.send(f"You have been blocked from appealing by this guild.")
			appeal_count = 0
			for _, content in gdata["appeals"]:
				if content["author id"] == ctx.author.id:
					return await ctx.send(f"You already have an appeal open (#{content['appeal id']}).")
			else:
				for _, content in gdata['denied appeals'].items():
					if content["author id"] == ctx.author.id:
						appeal_count += 1
		_data = {
			"case id": case_id.content,
			"reason": reason.content,
			"appeal id": random.randint(1, 999999),
			"appeal no": appeal_count + 1,
			"author id": ctx.author.id,
			"type": ttype
		}
		data[str(guild.id)]["appeals"][str(_data["appeal id"])] = _data
		config.write('./data/appeals.json', data)
		await msg.edit(content=f"Appeal sent.")

	@seeappeals.command(name="setup")
	@commands.has_permissions(manage_roles=True, manage_guild=True, ban_members=True)
	async def appeals_setup(self, ctx):
		"""Interactive setup for appeals system"""
		_format = {
			"methods": {
				"server": None,
				"website": None,
				"email": None,
				"phone": None},
			"appeals": {},
			"denied appeals": {},
			"appeal log": None,
			"blocked members": []
		}
		data = config.read("./data/appeals.json")
		methods = list(_format["methods"].keys())

		def c(m):
			return m.channel == ctx.channel and m.author == ctx.author
		msg = await ctx.send(f"Welcome to appeals setup! First, pick from a list of the following appeal methods:"
							 f"{', '.join(_format['methods'].keys())}")
		while True:
			await msg.edit(content="pick from a list of the following appeal methods, or say 'finish' to quit method config:"
							 f"{', '.join(_format['methods'].keys())})")

			meth = await self.bot.wait_for("message", check=c)
			await meth.delete(delay=0.25)
			if meth.content.lower() == 'finish':
				break
			if len(meth.content.split(" ")) <= 1:
				await msg.edit(content=f"Please format your response in `<option> <new value>`\n\n"
									   f"pick from a list of the following appeal methods, or say 'finish' to quit method config:"
							 f"{', '.join(_format['methods'].keys())})")
				continue
			if meth.content.lower() in methods:
				_format[meth.content.lower()] = meth.content.lower().split(" ")[1:]
		while True:
			await msg.edit(content=f"What is your appeal log channel? Provide the __ID__ of the channel.")
			def c(m):
				return m.channel == ctx.channel and m.author == ctx.author and m.content.isdigit()
			try:
				log = await self.bot.wait_for("message", check=c, timeout=30)
				_format["appeal log"] = int(log.content)
			except asyncio.TimeoutError:
				pass
			break
		data[str(ctx.guild.id)] = _format
		config.write('./data/appeals.json', data)
		return await msg.edit(content=f"Set up!")

	@commands.group(name="reactionrole", aliases=['rr', 'reaction', 'rrole'], invoke_without_command=True)
	@commands.has_permissions(manage_roles=True, manage_messages=True, add_reactions=True, external_emojis=True)
	@commands.bot_has_permissions(add_reactions=True, manage_messages=True, external_emojis=True)
	async def reactionroles(self, ctx, *, message: int = None):
		"""Lists reaction roles.

		To create/remove reaction roles, run `g!help rr` to get the subcommands"""
		data = config.read("./data/reactions.json")
		if str(ctx.guild.id) not in data.keys():
			return await ctx.send(embed=discord.Embed(
				title="Reaction Roles:",
				description="This guild has no reaction roles set up! Try `{0.prefix}{0.command.qualified_name} create`.".format(ctx),
				color=0xfdae55,
				timestamp=datetime.datetime.utcnow()
			))
		else:
			roles = []
			for message_id in data[str(ctx.guild.id)].keys():
				if int(message.id) == message or message is None:
					for role, emoji in message_id.items():
						if role == "channelid":
							continue

						_role = ctx.guild.get_role(int(role))
						if _role:
							_role = _role.mention
						else:
							_role = role
						roles.append((_role, discord.utils.get(self.bot.emojis, id=emoji)))
			content = PaginatorEmbedInterface(self.bot, commands.Paginator(max_size=1900, prefix="", suffix=""))
			count = 0
			for role, emote in roles:
				await content.add_line(f"{count}. {role}L {str(emote)}")
				count += 1
			await content.send_to(ctx.channel)


	@staticmethod
	def fuzzy_get_role(ctx, name, ID=0, color=discord.Color(0x917491)):
		for role in ctx.guild.roles:
			if role.name.lower() in name or name in role.name.lower() or name == role.name:
				return role
			elif role.id == ID:
				return role
			elif role.color == color:
				return role
			else:
				continue
		else:
			return None

	@staticmethod
	def fuzzy_get_message(ctx, ID, *, channel=None):
		"""Finds a message by ID.

		If it is already registered, returns in about .1 seconds."""
		if len(str(ID).split("-")) >= 2:
			if isinstance(ID, str):
				channel, ID = ID.split("-")
		loop = ctx.bot.loop

		if channel:
			try:
				message = asyncio.run_coroutine_threadsafe(channel.fetch_message(ID), loop=loop).result()
			except (discord.NotFound, discord.Forbidden):
				return None
			else:
				return message
		else:
			for channel in ctx.guild.text_channels:
				if channel.permissions_for(ctx.me).read_message_history:
					try:
						message = asyncio.run_coroutine_threadsafe(channel.fetch_message(ID), loop=loop).result()
					except (discord.NotFound, discord.Forbidden):
						continue
					else:
						return message

	@reactionroles.command(name="create", aliases=['add'], enabled=False)
	async def rr_add(self, ctx, role: discord.Role = None, message: typing.Union[discord.Message, int] = None, *,
					 emoji: typing.Union[discord.Emoji, str] = None):
		"""Creates a reaction role

		By default this command is interactive. Providing arguments does the quick setup.
		If you go with quick setup, __all arguments must be provided__
		If you provide :message: as just a message ID (and it's not already registered, it will search every channel in the guild, which gets a little slow.
		To avoid this, make message either the message URL, or chanelID-messageID"""
		_role = role
		_message:discord.Message = message
		_emoji = emoji
		_channel = None

		async def get_response(content, check=None, *, ret: str = "str"):
			msg = await ctx.send(content)
			try:
				resp = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=120)
			except asyncio.TimeoutError:
				return await msg.edit(content="Timed out.")
			else:
				await msg.delete()
				await resp.delete()
				if ret == "message":
					return resp
				return resp.content

		if role is None:
			__role__ = await get_response("Please tell me a role. This can be a role ID, name or mention")
			if isinstance(__role__, discord.Message):
				return
			_role = self.fuzzy_get_role(ctx, __role__, __role__, __role__)
			if _role:
				role = _role
			else:
				return await ctx.send(f"That role was not found.")
		if message is None:
			resp = await get_response("Please tell me the message you want to use as a reaction role. This can be the message "
							   "URL, ID or channeldID-messageID. Note that if the message ID is already in use, this "
							   "*appends* to that message's roles. If the ID is not already registered it will take"
							   " a while to find it. URL and cid-mid don't take a while.\n\nDont have one? Reply \"create\"")
			if isinstance(resp, discord.Message):
				return
			async with ctx.channel.typing():
				if resp.lower() == "create":
					channel = get_response("What channel shsould this be sent to?", lambda m: m.channel_mentions >= 0 and m.author == ctx.channel, ret="message")
					if isinstance(channel, discord.Message):
						return
					else:
						channel = resp.channel_mentions[0]
						_channel = channel
						message = await channel.send("Placeholder message.")
				_message = self.fuzzy_get_message(ctx, resp)
				if _message is None:
					return await ctx.send("Message Not Found.")
				else:
					message = _message
		if emoji is None:  # emojis are a little harder, so we're just going to .convert() it.
			resp = await get_response(f"What emoji should give {role.name} when reacted to? **Note: Unicode emojis are not yet supported (soon:tm:)**. "
			"I must be able to see the emoji (be in the emoji's server)")
			if isinstance(resp, discord.Message):
				return
			else:
				try:
					_emoji = await commands.EmojiConverter().convert(ctx, resp)
				except commands.BadArgument:
					return await ctx.send("Emoji Not Found.")
				else:
					emoji = _emoji
		status = await ctx.send("Updating data")
		fmt = {str(message.id): {"channelid": message.channel.id, str(role.id): emoji.id}}
		data = config.read("./data/reactions.json")
		if data.get(str(ctx.guild.id)) is None:
			data[str(ctx.guild.id)] = fmt
		else:
			if data[str(ctx.guild.id)].get(str(message.id)):
				data[str(ctx.guild.id)][str(message.id)][str(role.id)] == emoji.id
			else:
				data[str(ctx.guild.id)][str(message.id)] = fmt[str(message.id)]
		config.write("./data/reactions.json", data)
		await status.edit(content="Saved! Verifying reaction message integrity...")
		only_reactions = [x for x in data[str(ctx.guild.id)][str(message.id)]]
		for reaction in message.reactions:
			if isinstance(reaction.emoji, (discord.Emoji, discord.PartialEmoji)):
				if reaction.emoji.id not in only_reactions:
					async for user in reaction.users():
						await reaction.remove(user)
		for id in only_reactions:
			if id not in [x.id for x in message.reactions]:
				await message.add_reaction(self.bot.get_emoji(id))
		if message.author == self.bot.user:
			await status.edit(content="Updating message to reflect changes...")
			content = ""
			for name, role in data[str(ctx.guild.id)][str(message.id)].items():
				if name == "channelID":
					continue
				else:
					content += f"{str(self.bot.get_emoji(data[str(ctx.guild.id)][str(message.id)][str(role.id)]))}: {role.mention}\n"
			await message.edit(content=content)
			await status.edit(content="All done!")
		else:
			await status.edit(content="All done! Please edit the message to reflect changes.")


def setup(bot):
	bot.add_cog(EventsTest(bot))
