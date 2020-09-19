from typing import Union as U

import datetime
import discord

from . import config


class Case:
	def __init__(self, ctx, *, case_id: int = None, case_author: U[discord.User, discord.Member] = None,
				 case_target: U[discord.User,
								discord.Member, int] = None,
				 reason: str = None, data: dict=None, type: str = "warns", color: discord.Color = discord.Color.green(),
				 subtype: str = None, url: str = None):
		self._case_id = case_id
		self._author = case_author
		self._target = case_target
		self.__author = self._author
		self.__target = self._target
		self._reason = reason
		self._raw = data
		self.ctx = ctx
		self._type = type
		if self._case_id is None:
			self._case_id = self.last_case(ctx.guild.id)
		self.color = color
		self._data = data
		if self._data is None:
			self._data = config.read("./data/core.json")
			self._data = self._data[str(ctx.guild.id)]
		self._subtype = subtype

	@classmethod
	async def from_dict(cls, data: dict):
		a = Case(
			data.get("ctx"),
			case_id=data.get('case_id'),
			case_author=data.get("author"),
			case_target=data.get("target"),
			reason=data.get("reason"),
			data=data,
			type=data.get("type"),
			color=data.get("color"),
			subtype=data.get("subtype"),
			url=data.get("url")
		)
		return a

	@property
	def modlog_channel(self) -> U[None, discord.TextChannel]:
		return self.ctx.bot.get_channel(self.raw["log channel"])

	@property
	def id(self) -> int:
		return self._case_id

	@property
	def author(self) -> U[discord.User, discord.Member, int, None]:  # todo: make it so it doesnt return nOne of not found.
		if isinstance(self._author, int):
			self.__author = self._author
			self._author = self.ctx.bot.get_user(self._author)
			if self._author is None:
				try:
					loop = self.ctx.bot.loop
					self._author = self.__author
				except:
					return self.__author
		return self._author

	@property
	def target(self) -> U[discord.User, discord.Member, int]:
		if isinstance(self._target, int):
			self.__target = self._target
			self._target = self.ctx.bot.get_user(self._target)
			if self._target is None:
				try:
					loop = self.ctx.bot.loop
					self._target = self.__target
				except:
					return self.__target
		return self._target

	@property
	def reason(self) -> str:
		return self._reason

	@property
	def raw(self) -> dict:
		return self._data

	@property
	def rawraw(self) -> dict:
		return self._raw

	@property
	def type(self) -> str:
		return self._type

	@property
	def case_id(self) -> int:
		return self._data["next id"] - 1

	@staticmethod
	def last_case(guild_id) -> int:
		data = config.read("./data/core.json")
		if data.get(str(guild_id)) is None:
			return 1  # probably first case
		else:
			return data[str(guild_id)]["next id"] - 1

	@property
	def subtype(self) -> U[None, str]:
		return self._subtype

	async def new(self):
		"""Makes a new modlog case, automagically!"""
		ctx = self.ctx
		data = config.read("./data/core.json")
		if data.get(str(self.ctx.guild.id)) is None:
			data[str(ctx.guild.id)] = {
				"warns": {},
				"mutes": {},
				"unmutes:": {},
				"bans": {},
				"kicks": {},
				"unbans": {},
				"next id": 1,
				"log channel": None,
				"toggles": {"commands": [], "modules": []},
				"muted role": None
			}
		data[str(self.ctx.guild.id)][self.type][str(data[str(self.ctx.guild.id)]["next id"])] = {
			"subtype": self.subtype,
			"author": self.author.id,
			"target": self.target.id,
			"reason": self.reason,
			"created at": str(ctx.message.created_at),
			"mod message url": None
		}
		channel = data[str(self.ctx.guild.id)].get("log channel")
		if channel:
			channel = self.ctx.bot.get_channel(channel)
			if channel:
				if self.subtype:
					title = f"{self.type.rstrip('s')} | {self.subtype}"
				else:
					title = self.type.rstrip("s")
				embed = discord.Embed(
					title=title,
					description=f"**Moderator:** {self._author.mention} (`{str(self._author)}`)\n**Offending User:** "
								f"{self._target.mention} (`{str(self._target)}`)\n**Reason:** {self._reason}",
					color=self.color,
					timestamp=ctx.message.created_at
				)
				embed.set_author(name=self._author.display_name, icon_url=str(self._author.avatar_url_as(static_format='png')))
				embed.set_footer(text=f"case id: {data[str(self.ctx.guild.id)]['next id']}")
				try:
					msg = await channel.send(embed=embed)
					data[str(self.ctx.guild.id)][self.type][str(data[str(self.ctx.guild.id)]["next id"])]["mod message url"] = msg.jump_url
				except Exception as e:
					pass

		data[str(self.ctx.guild.id)]["next id"] += 1
		config.write("./data/core.json", data)
		self._data = data[str(self.ctx.guild.id)]
		return self

	@staticmethod
	def check_height(top: discord.Role, current: discord.Role):
		return top <= current


async def create_modlog_case(ctx, *, author: discord.Member,
							 target: U[discord.Member, discord.User], reason: str, _type: str = 'warns', color: discord.Color,
							 sub: str = None, custom_id: int = None, url: str = None) -> Case:
	return await Case(ctx, case_id=custom_id, case_author=author, case_target=target, reason=reason, type=_type, color=color,
					  subtype=sub, url=url).new()


async def get_modlog(ctx):
	return Case(ctx).modlog_channel


def check_height(top: discord.Role, current: discord.Role):
	return top <= current


class Converters:

	@staticmethod
	def timeFromHuman(provided: str):
		"""Converts time from <num><s/h/mh/mh/m/hm> to an integer.

		SHOULD ONLY BE USED TO CONVERT TO BE USED IN .sleep() AS IT RETURNS VALUE IN SECONDS!"""
		conv_table = {
			"s": 1,
			"m": 60,
			"h": 3600,
			"d": 86400,
			"w": 604800,
			"y": 31536000,
			# Full
			"seconds": 1,
			"minutes": 60,
			"hours": 3600,
			"days": 86400,
			"weeks": 604800,
			"years": 31536000,
			"year": 315360000
		}
		toconv = provided.lower()
		if not toconv.endswith(tuple(conv_table.keys())):
			raise KeyError("No conversion available for '" + toconv[-1] + "'.")
		else:
			for key, totimesby in conv_table.items():
				try:
					time, ext = toconv.split(key)
					time = int(time)
				except ValueError:
					continue
				else:
					return [round(time * totimesby), str(time) + key]
			else:
				raise KeyError("Ran out of conversion options.")

	@staticmethod
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

	@staticmethod
	def fix_time(time: int = None, *, return_ints: bool = False, brief: bool = False):
		"""Convert a time (in seconds) into a readable format, e.g:
		86400 -> 1d
		3666 -> 1h, 1m, 1s

		set ::return_ints:: to True to get a tuple of (days, minutes, hours, seconds).
		--------------------------------
		:param time: int -> the time (in seconds) to convert to format.
		:keyword return_ints: bool -> whether to return the tuple or (default) formatted time.
		:raises ValueError: -> ValueError: time is larger then 7 days.
		:returns Union[str, tuple]:
		to satisfy pycharm:
		"""
		seconds = round(time, 2)
		minutes = 0
		hours = 0
		overflow = 0

		d = 'day(s)' if not brief else 'd'
		h = 'hour(s)' if not brief else 'h'
		m = 'minute(s)' if not brief else 'm'
		s = 'seconds(s)' if not brief else 's'
		a = 'and' if not brief else '&'

		while seconds >= 60:
			minutes += 1
			seconds -= 60
		while minutes >= 60:
			hours += 1
			minutes -= 60
		while hours > 23:
			overflow += 1
			hours -= 23

		if return_ints:
			return overflow, hours, minutes, seconds
		if overflow > 0:
			return f'{overflow} day(s), {hours} hour(s), {minutes} minute(s) and {seconds} second(s)'
		elif overflow == 0 and hours > 0:
			return f'{hours} hour(s), {minutes} minute(s) and {seconds} second(s)'
		elif overflow == 0 and hours == 0 and minutes > 0:
			return f'{minutes} minute(s) and {seconds} second(s)'
		else:
			return f'{seconds} second(s)'
