# -*- coding: utf-8 -*-
import asyncio
import time
import typing
from datetime import datetime, timedelta
from re import findall

import discord
from discord.ext import commands

from .mod import Mod
from .utils import config

_DEFAULTS = {
    "ignore": {"roles": [], "channels": []},
    "max emojis": {
        "total": 5,
        "in_seconds": 5,
        "action": "mute",
        "args": "30m [AUTOMOD] 5 emojis, emojispam"
    },
    "max mentions": {
        "total": 5,
        "in_seconds": 3,
        "action": "mute",
        "args": "1h [AUTOMOD] 5 mentions, mass mention"
    },
    "max messages": {
        "total": 5,
        "in_seconds": 5,
        "action": "mute",
        "args": "10m [AUTOMOD] 5 messages in 5 seconds, spam"
    },
    "invites": {
        "whitelisted": []
    },
    "min_account_age": {
        "total": 0,
        "timeframe": "seconds"
    },
    "version": 0.3
}

_VALID_INPUTS = {
    "action": ["warn", "mute", "kick", "ban"],
    "timeframe": ["seconds", "minutes", "hours", "days", "weeks", "months", "years"]
}


class AutoMod(commands.Cog):
    """Basic automoderation"""

    def __init__(self, bot):
        self.bot = bot
        self.mod_cls = Mod(self.bot)  # init it like this so we can just await mod_cls.command()
        self.watching = {
            "messages": {},
            "emojis": {},
            "mentions": {}
        }
        self.actions = {
            "warn": self.bot.get_command("warn"),
            "mute": self.bot.get_command("mute"),
            "kick": self.bot.get_command("kick"),
            "ban": self.bot.get_command("ban")
        }

    async def sleep(self, target: discord.Member, key: str, total: int, until: int):
        await discord.utils.sleep_until(datetime.utcnow() + timedelta(seconds=until))
        if target in self.watching[key].keys():
            if self.watching[key][target] >= total:
                del self.watching[key][target]
                return True
            else:
                del self.watching[key][target]
                return False
        else:
            return False

    async def handle_punish(self, message, data, me, ctx, key):
        succ = await self.sleep(message.author, key,
                                data[str(message.guild.id)]["max emojis"]["total"],
                                data[str(message.guild.id)]["max emojis"]["in_seconds"])
        if succ:
            try:
                await self.actions[me["action"]](ctx, message.author, reason=me["args"])
                await message.delete()
            except:
                raise
            return

    @commands.Cog.listener(name="on_message")
    async def on_message(self, message: discord.Message):
        start = time.time()
        data = config.read("./data/automod.json")
        ctx = await self.bot.get_context(message)
        ctx.prefix = "g!"
        ctx.guild = message.guild
        ctx.author = ctx.me
        ctx.message = message
        if message.guild:
            if str(message.guild.id) in data.keys():
                if not isinstance(message.author, discord.Member):
                    return  # bugged
                if message.channel.permissions_for(message.author).manage_messages:
                    return
                if not message.author.bot:
                    emojis = len(findall(
                        r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>",
                        message.content
                    ))
                    # print(f"Took {round(time.time() - start, 3)}s to regex emojis")
                    # invites = findall(
                    #     r"(?:https?://)?discord(?:app\.com/invite|\.gg)/?[a-zA-Z0-9]+/?",
                    #     message.content
                    # )
                    if self.watching["messages"].get(message.author):
                        # print(f"Took {round(time.time() - start, 3)}s to get to messages")
                        self.watching["messages"][message.author] += 1
                        mm = data[str(message.guild.id)]["max messages"]
                        if self.watching["messages"][message.author] >= mm["total"]:
                            del self.watching["messages"][message.author]
                            try:
                                ctx.command = self.actions[mm["action"]]
                                await ctx.invoke(ctx.command, *[message.author], reason=mm["args"])
                            except:
                                raise
                            return
                        else:
                            if self.watching["messages"][message.author] >= mm["total"] -2:
                                await message.delete()
                    else:
                        # print(f"Took {round(time.time() - start, 3)}s to get to messages else")
                        me = data[str(message.guild.id)]["max messages"]
                        self.watching["messages"][message.author] = 1
                        self.bot.loop.create_task(self.handle_punish(message, data, me, ctx, "messages"))

                    me = data[str(message.guild.id)]["max emojis"]
                    if emojis >= me["total"]:
                        print(f"Took {round(time.time() - start, 3)}s to get to emojis")
                        try:
                            ctx.command = self.actions[me["action"]]
                            await ctx.invoke(ctx.command, *[message.author], reason=me["args"])
                            await message.delete()
                        except:
                            raise
                    else:
                        if self.watching["emojis"].get(message.author):
                            # print(f"Took {round(time.time() - start, 3)}s to get to emojis if")
                            if self.watching["emojis"][message.author] >= me["total"]:
                                del self.watching["emojis"][message.author]
                                try:
                                    ctx.command = self.actions[me["action"]]
                                    await ctx.invoke(ctx.command, *[message.author], reason=me["args"])
                                    await message.delete()
                                except:
                                    raise
                                return
                            else:
                                pass
                        else:
                            # print(f"Took {round(time.time() - start, 3)}s to get to emojis else")
                            self.watching["emojis"][message.author] = emojis
                            self.bot.loop.create_task(self.handle_punish(message, data, me, ctx, "emojis"))
                    me = data[str(message.guild.id)]["max mentions"]
                    # print(f"{message.clean_content} -> {len(message.raw_mentions)}")
                    if len(message.mentions) >= me["total"]:
                        print(f"Took {round(time.time() - start, 3)}s to get to mentions")
                        try:
                            ctx.command = self.actions[me["action"]]
                            await ctx.invoke(ctx.command, *[message.author], reason=me["args"])
                            await message.delete()
                        except:
                            raise
                    else:
                        # print(f"Took {round(time.time() - start, 3)}s to get to mentions else")
                        if self.watching["mentions"].get(message.author):
                            if self.watching["mentions"][message.author] >= me["total"]:
                                del self.watching["mentions"][message.author]
                                try:
                                    ctx.command = self.actions[me["action"]]
                                    await ctx.invoke(ctx.command, *[message.author], reason=me["args"])
                                    await message.delete()
                                except:
                                    raise
                                return
                            else:
                                pass
                        else:
                            self.watching["mentions"][message.author] = len(message.raw_mentions)
                            self.bot.loop.create_task(self.handle_punish(message, data, me, ctx, "mentions"))
        # print(f"Took {time.time() - start}s to finish automod event with no returns")

    @commands.group(name="autoguardian", aliases=['automod', 'autoguard'], case_insensitive=True, invoke_without_command=True)
    @commands.has_permissions(manage_guild=True, manage_roles=True, manage_messages=True, ban_members=True)
    @commands.bot_has_permissions(manage_guild=True, manage_roles=True, manage_messages=True, ban_members=True)
    async def automod_root(self, ctx: commands.Context, setting = None, subsetting: str = None, *,
                           newvalue:typing.Union[int, float, bool, str] = None):
        """Displays the server's current autoguardian settings.

        By default, this is disabled. You can enable it by running `g!autoguardian toggle`.

        To change a setting, run `g!autoguardian <setting> <subsetting> <new value>`.
        Example: `g!autoguardian max_messages total_seconds 5` -> changes the time period to check for max_messages.total
        """
        ver = _DEFAULTS["version"]
        if ctx.invoked_subcommand:
            return
        data = config.read("./data/automod.json")
        if not data.get(str(ctx.guild.id)):
            return await ctx.send(f"You haven't enabled autoguardian yet.")
        else:
            # print(data[str(ctx.guild.id)].get("version", 0.0))
            # print(ver)
            # print(data[str(ctx.guild.id)].get("version", 0.0) == ver)
            # print(data[str(ctx.guild.id)].get("version", 0.0) != ver)
            if float(data[str(ctx.guild.id)].get("version", 0.0)) != ver:
                await ctx.send(f":exclamation: Uh oh! Your autoguardian is running an older version ("
                                      f"v{data[str(ctx.guild.id)].get('version', 0.0)}), when a newer version ("
                                      f"{_DEFAULTS['version']}) is available! Support for autoguardian's functionality on"
                                      f" outdated configurations is not guaranteed.\n\n**Run {ctx.prefix}"
                                      f"{ctx.command.qualified_name} fix** to upgrade.")
                await asyncio.sleep(2)
            if not all([setting, subsetting, newvalue]):  # no or not enough args
                e = discord.Embed(
                    title=f"Your AutoGuardian Settings:",
                    description=f"To change them, run `{ctx.prefix}{ctx.command.qualified_name} <setting>"
                                f" <subsetting> <new value>`.\nExample: `{ctx.prefix}{ctx.command.qualified_name} "
                                f"max_messages total 3` -> changes max messages in total_seconds to 3 (default is 5). So 3"
                                f" messages in 5 seconds would trigger <action>.",
                    colour=discord.Colour.green(),
                    timestamp=datetime.utcnow()
                )
                for key, values in data[str(ctx.guild.id)].items():
                    if key in ["invites", "ignore", "version"]:
                        continue
                    else:
                        name = key.replace(" ", "_")
                        value = ""
                        for subset, subval in values.items():
                            value += f"  - {subset}: {subval}\n"
                        e.add_field(name='**'+name+'**', value=value, inline=False)
                ignore_channels = data[str(ctx.guild.id)]["ignore"]["channels"]
                ignore_roles = data[str(ctx.guild.id)]["ignore"]["roles"]
                if ignore_channels:
                    filt = filter(lambda c: self.bot.get_channel(c) is not None, ignore_channels)
                    e.add_field(name="Ignored Channels:", value=', '.join([self.bot.get_channel(x).name for x in filt]) or 'None set.',
                                inline=False)
                if ignore_roles:
                    filt = filter(lambda c: self.bot.get_channel(c) is not None, ignore_channels)
                    e.add_field(name="Ignored Roles:", value=', '.join([self.bot.get_channel(x).name for x in filt]) or 'None set.',
                                inline=False)
                e.set_footer(text=f"AutoGuardian Version: {data[str(ctx.guild.id)].get('version', 0.0)}")
                return await ctx.send(embed=e)
            else:
                settings = ["max mentions", "max messages", "max emojis", "min account age"]
                setting = setting.lower().replace("_", " ")
                if setting not in settings:
                    return await ctx.send(f"Unable to parse arguments; Argument 1 is not in valid settings ("
                                          f"{', '.join(settings)}).")
                else:
                    subsettings = _DEFAULTS[setting]
                    subsetting = subsetting.lower()
                    if subsetting not in subsettings:
                        return await ctx.send(f"Unable to parse arguments: Argument 2 is not a valid subsetting ("
                                              f"{', '.join(subsettings)}).")
                    else:
                        if type(newvalue) != type(_DEFAULTS[setting][subsetting]):
                            expected = type(_DEFAULTS[setting][subsetting]).__name__
                            got = type(newvalue).__name__
                            return await ctx.send(f"Unable to parse arguments: Argument 3 is not the right type!"
                                                  f"\nExpected type {expected}, got {got}.")
                        else:
                            data[str(ctx.guild.id)][setting][subsetting] = newvalue
                            config.write("./data/automod.json", data)
                            return await ctx.send(f"Set `{setting}.{subsetting}.value` to {str(newvalue)[:1500]}.")

    @automod_root.command(name="toggle", aliases=['enable', 'disable', 'on', 'off'])
    @commands.has_permissions(manage_guild=True, manage_roles=True, manage_messages=True, ban_members=True)
    @commands.bot_has_permissions(manage_guild=True, manage_roles=True, manage_messages=True, ban_members=True)
    async def enable_automod(self, ctx: commands.Context):
        """Enables or disables automod"""
        data = config.read("./data/automod.json")
        if not data.get(str(ctx.guild.id)):
            m = await ctx.send("Are you sure you want to turn *AutoGuardian* on?\n\n*AutoGuardian* is in early "
                               "beta, so our support team isn't very attuned to it, and won't be able to help with"
                               " any issues you may face.")
            msg = await self.bot.wait_for("message", check=lambda ms: ms.author == ctx.author and ms.channel == ctx.channel,
                                        timeout=300)
            if msg.content.lower().startswith("y"):
                data[str(ctx.guild.id)] = _DEFAULTS
                config.write("./data/automod.json", data)
                return await m.edit(content="Enabled *AutoGuardian*.")
            else:
                return await m.edit(content="Ok then.")
        else:
            m = await ctx.send("Are you sure you want to disable *AutoGuardian*? All settings will be lost!")
            msg = await self.bot.wait_for("message",
                                          check=lambda ms: ms.author == ctx.author and ms.channel == ctx.channel,
                                          timeout=300)
            if msg.content.lower().startswith("y"):
                del data[str(ctx.guild.id)]
                config.write("./data/automod.json", data)
                return await m.edit(content="Disabled *AutoGuardian*.")
            else:
                return await m.edit(content="Ok then.")

    @automod_root.command(name="update", aliases=['fix', 'upgrade'])
    @commands.has_permissions(administrator=True)
    async def automod_update(self, ctx: commands.Context):
        """Fixes any issues autoguardian may be facing, versionwise."""
        data = config.read("./data/automod.json")
        if not data.get(str(ctx.guild.id)):
            return await ctx.send(f"No issues because you haven't enabled it yet!")
        if len(_DEFAULTS.keys()) == data[str(ctx.guild.id)].keys():
            return await ctx.send(f"No obvious issues found. If you are having feature-breaking issues, toggle the"
                                  f" autoguardian off and back on again. Sounds simple, but with this bot it fixes"
                                  f" most of the issues.")
        else:
            added = []
            for key in _DEFAULTS.keys():
                if key not in data[str(ctx.guild.id)].keys():
                    data[str(ctx.guild.id)][key] = _DEFAULTS[key]
                    added.append(key)
            if added:
                config.write("./data/automod.json", data)
            return await ctx.send("Resolved any dating issues. Give it a spin, all should be good now.")


def setup(bot):
    bot.add_cog(AutoMod(bot))
