import asyncio
import copy
import json
from datetime import datetime
from typing import Union

import discord
from discord.ext import commands, tasks
from jishaku.paginators import PaginatorEmbedInterface as Paginator

from .utils.config import read, write


def is_banned(ctx):
	data = read("./data/globalban.json")
	return str(ctx.author.id) in data.keys()


class AntiRaid(commands.Cog):
	"""Anti-raid related stuff"""
	def __init__(self, bot):
		self.bot = bot
		self.guild = self.bot.get_guild(606866057998762023)
		bot.guild = self.guild
		bot.modrole = bot.guild.get_role(606990179642900540)
		self.do_bans.start()

	def cog_unload(self):
		self.do_bans.stop()

	@commands.group(name="banlist", aliases=['globalbans', 'globalban', 'gb', "gban"], invoke_without_command=True)
	@commands.bot_has_permissions(manage_messages=True, add_reactions=True, use_external_emojis=True, read_message_history=True)
	async def bans(self, ctx):
		"""Displays the global ban list."""
		paginator = Paginator(self.bot, commands.Paginator(prefix="", suffix="", max_size=1950),
							  send_kwargs={"content": f"to submit a global ban request, run `{ctx.prefix}gb request`."})
		msg = await ctx.send(f"Loading...")

		async def cmd():
			bans = read("./data/globalban.json")
			for user_id, data in bans.items():
				if not user_id.isdigit():
					continue
				_user = None
				try:
					user = self.bot.get_user(int(user_id)) or f"<@{user_id}>"
				except discord.NotFound:
					user = f"<@{user_id}>"
				else:
					user = str(user)
				bantime = datetime.fromisoformat(data["banned at"]).strftime("%c UTC")
				await paginator.add_line(f"• {user} (`{user_id}`): Banned by {data.get('modname')} on "
										 f"{bantime} for: {str(data.get('reason'))[:500]}", empty=True)
			await paginator.send_to(ctx.channel)
			await msg.delete()
		try:
			async with ctx.channel.typing():
				await asyncio.wait_for(cmd(), 300)
		except asyncio.TimeoutError:
			return await msg.edit(content=f"\U000023f1 Loading timed out. This command is none-functional (until a better fix"
								  f" is implimented). Please use `{ctx.prefix}{ctx.command.qualified_name} lookup <user>`"
								  f" instead.")

	@bans.command(name="request")
	@commands.cooldown(3, 3600, commands.BucketType.user)
	async def request_ban(self, ctx, user: Union[discord.User, int], *, reason: str):
		"""Request someone be banned.

		If proof is not in "reason", your request will automatically be denied."""
		if isinstance(user, int):
			try:
				user = await self.bot.fetch_user(user)
			except discord.NotFound:
				return await ctx.send(f"The ID \"{user}\" Is not a valid ID or that account no-longer exists.", delete_after=10)
		data = read("./data/globalban.json")
		data["requests"][str(user.id)] = {
			"modname": ctx.author.name,
			"reason": reason,
			"banned at": str(datetime.utcnow()),
			"author id": ctx.author.id
		}
		write("./data/globalban.json", data=data)
		channel = discord.utils.get(list(self.bot.get_all_channels()), name="ban-requests", guild=self.guild)
		if channel:
			e = discord.Embed(
				title=f"New global ban request from: {ctx.author} for: {user}",
				description=f"Reason: {reason}",
				color=discord.Color.dark_green(),
				timestamp=datetime.utcnow(),
				url=ctx.message.jump_url
			)
			e.set_footer(text=f"Author ID: {ctx.author.id} | User ID: {user.id}")
			await channel.send(ctx.bot.modrole.mention, embed=e)
		await ctx.send(f"Your request has been sent. __If you would like to receive a response, please enable DMs.__",
					   delete_after=10)

	@bans.command(name="approve", aliases=['ban', 'gban'])
	@commands.check(lambda ctx: ctx.author in ctx.bot.guild.members and ctx.bot.modrole in ctx.bot.guild.get_member(ctx.author.id).roles)
	async def ban_approve(self, ctx, *, user_id: Union[discord.User, int]):
		"""approves a ban and adds it to the approved list"""
		if isinstance(user_id, discord.User):
			user_id = user_id.id
		data = read("./data/globalban.json")
		if str(user_id) not in data["requests"].keys():
			return await ctx.send(f"There are no pending requests with that user's ID." + " They are already banned."
																						  "" if str(user_id) in data.keys() else "")
		else:
			entry = data["requests"][str(user_id)]
			if entry["modname"].lower() == ctx.author.name.lower():
				await ctx.send(f"Approving your own requests is forbidden, however due to my obvious lack of a brain,"
							   f" I can't determine if this situation is one of those where you need to urgently"
							   f" ban {user_id} or not. Thus, I will continue this command, however this action has"
							   f" been logged and will be reviewed by a developer.", delete_after=10)
				channel = discord.utils.get(self.bot.get_all_channels(), name="gban-logs", topic="573240252177580032",
											slowmode_delay=3)
				members = discord.utils.get(self.bot.get_guild(606866057998762023).roles, name="Developer").members
				past_5 = [f"{x.author.name} {x.created_at.strftime('%x %X')}:\n{x.content}" for x in await ctx.channel.history(limit=5).flatten()]
				nl = '\n\n'
				await channel.send(
					' '.join([m.mention for m in members]),
					embed=discord.Embed(
						title=f"Self-approved ban request from {ctx.author}:",
						description=f"Entry data:\n```json\n{json.dumps(entry, indent=2)}\n```\n\nPrevious 5 messages"
									f" for proof (in case the message (title) gets deleted):\n```md\n{nl.join(past_5)}\n```"[:2048],
						color=discord.Color.blue(),
						url=ctx.message.jump_url
					)
				)
			new_entry = copy.copy(entry)
			new_entry["banned at"] = str(datetime.utcnow())
			new_entry["modname"] = entry["modname"] + f" (approved by {ctx.author.name})"
			data[str(user_id)] = new_entry
			del entry
			write("./data/globalban.json", data=data)
			user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
			await ctx.send(f"Successfully banned {user}.")
			try:
				await user.send(f"You have been globally banned by {new_entry['modname']} for: "
								f"{new_entry['reason'][:1500]}.\nTo appeal, please run `g!gban appeal`.")
				await self.bot.get_user(new_entry["author id"]).send(f"Your ban request for {user} has been approved.")
			except (discord.Forbidden, AttributeError):
				pass

	@bans.command(name="appeal")
	@commands.check(is_banned)
	async def ban_appeal(self, ctx, *, reason: str):
		"""Appeal a global ban"""
		data = read("./data/globalban.json")
		data["appeals"][str(ctx.author.id)] = {
			"reason": reason[:1300],
			"at": str(datetime.utcnow())
		}
		write("./data/globalban.json", data=data)
		channel = discord.utils.get(list(self.bot.get_all_channels()), name="ban-requests", guild=self.guild)
		if channel:
			e = discord.Embed(
				title=f"New global ban appeal from: {ctx.author}",
				description=f"Reason: {reason}",
				color=discord.Color.dark_green(),
				timestamp=datetime.utcnow(),
				url=ctx.message.jump_url
			)
			e.set_footer(text=f"Author ID: {ctx.author.id}")
			await channel.send(embed=e)
		await ctx.send(f"Your request has been sent. __If you would like to receive a response, please enable DMs.__",
					   delete_after=10)

	@bans.command(name="reject", aliases=['unban'])
	@commands.check(lambda ctx: ctx.author in ctx.bot.guild.members and ctx.bot.modrole in ctx.bot.guild.get_member(ctx.author.id).roles)
	async def bans_appeal_reject_or_smthn(self, ctx, *, user_id: Union[discord.User, int]):
		"""Approves an appeal or rejects a ban request"""
		if isinstance(user_id, discord.User):
			user_id = user_id.id
		data = read("./data/globalban.json")
		if str(user_id) not in data["requests"].keys():
			if str(user_id) in data["appeals"].keys():
				del data["appeals"][str(user_id)]
				del data[str(user_id)]
				write("./data/globalban.json", data=data)
			elif str(user_id) in data.keys():
				del data[str(user_id)]
			else:
				return await ctx.send(f"There are no pending requests with that user's ID, and they aren't banned.")
		else:
			try:
				del data[str(user_id)]
				del data["requests"][str(user_id)]
				del data["appeals"][str(user_id)]
			except KeyError:
				pass
			write("./data/globalban.json", data=data)
		user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
		await ctx.send(f"Successfully unbanned {user}.")
		try:
			await user.send(f"You have been globally unbanned. However, you will not be unbanned from servers you were "
							f"banned in. For this, please run `g!appeal <server id/name>` to appeal a ban on a server.")
		except:
			pass

	@bans.command(name="lookup")
	async def ban_lookup(self, ctx, user: Union[discord.User, int]):
		"""Checks if someone is banned"""
		if isinstance(user, int):
			user = self.bot.get_user(user) or await self.bot.fetch_user(user)
		_ctx = copy.copy(ctx)
		_ctx.author = user
		banned = is_banned(_ctx)
		data = read("./data/globalban.json")
		reported = str(user.id) in data["requests"].keys()
		appealed = str(user.id) in data["appeals"].keys()
		msg = ""
		if banned:
			msg += f"{user} is currently banned."
			if appealed:
				msg += f" {user} has appealed."
		else:
			msg += f"{user} is not currently banned."
			if reported:
				msg += f" {user} has, however, been reported at " \
					   f"{datetime.fromisoformat(data['requests'][str(user.id)]['banned at']).strftime('%c UTC')}."
		return await ctx.send(msg)

	@tasks.loop(minutes=5)
	async def do_bans(self):
		data = read("./data/globalban.json")
		if data.get("banwaves") is None:
			data["banwaves"] = 0
		banned = []
		servers = []
		for guild in self.bot.guilds:
			guild: discord.Guild  # for linting
			if "nogban" in [x.name.lower() for x in guild.roles] or not guild.me.guild_permissions.ban_members:
				continue
			servers.append(guild)
			for user_id, entry in data.items():
				if not user_id.isdigit():
					continue
				try:
					await guild.ban(discord.Object(int(user_id)), reason=f"Global Ban by {entry['modname']} with "
																	 f"reason: {entry['reason']}")
					banned.append(user_id)
				except (discord.Forbidden, discord.NotFound):
					continue
				except (discord.HTTPException, Exception) as error:
					if guild.system_channel:
						if guild.system_channel.permissions_for(guild.me).send_messages:
							try:
								await guild.system_channel.send(f"Error while attempting to preform a global ban."
																f" Please resolve the error `"
																f"{discord.utils.escape_mentions(error)}`, or contact"
																f" our support team.\n\n*you can disable global bans"
																f" by revoking my \"ban members\" permission, or"
																f" creating a role called `nogban`.*")
							except:
								pass
							finally:
								break
		data["banwaves"] += 1
		write("./data/globalban.json", data=data)
		msg = f"Banwave #{data['banwaves']}: Banned {len(list(set(banned)))} people in {len(servers)} servers."
		channel = discord.utils.get(list(self.bot.get_all_channels()), name="ban-requests", guild=self.guild)
		if channel:
			await channel.send(msg, delete_after=60*5)

	@commands.Cog.listener()
	async def on_message(self, msg):
		if msg.guild and not msg.author.bot and not msg.content.startswith("! "):
			if msg.channel.name in ["gban-logs", "ban-requests"] and msg.guild.id in [606866057998762023,
																					  573240252177580032]:
				await msg.delete(delay=0.4)


def setup(bot):
	bot.add_cog(AntiRaid(bot))
