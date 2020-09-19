import asyncio
import datetime
import random
import re
import typing
from typing import Union

import aiohttp
import discord
from discord.ext import commands
from discord.utils import escape_mentions
from jishaku.paginators import PaginatorEmbedInterface

from .config import Configuration
from .utils import entry_helper, config
from .utils.config import read


class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ordered = [
            'https://mystb.in/documents',
            'https://hastebin.com/documents'
        ]

    async def work_and_post(self, messages):
        content = ""
        for message in messages:
            bot = '[BOT]' if message.author.bot else ''
            th = {
                1: 'st',
                2: 'nd',
                3: 'rd',
            }
            Th = th[int(message.created_at.strftime("%d"))] if int(
                message.created_at.strftime("%d")) in th.keys() else 'th'
            at = message.created_at.strftime(f"%a the %d{Th} %b, %H:%M UTC")
            content += f"{message.author} ({message.author.id}) {bot} {at}:\n{message.clean_content}\n\n"
        async with aiohttp.ClientSession() as session:
            for option in self.ordered:
                async with session.post(option, data=content) as resp:
                    _json = await resp.json()
                    return option.replace("documents", _json['key'])

    @commands.group(name="purge", aliases=['prune', 'bulkdelete', 'massdelete', 'clear'], invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    async def bulkdel(self, ctx, amount: int, *, flags: str = None):
        """Bulk delete messages. requires manage messages.
        if you still see your message after purging, this is a bug with discord and its not actually there. just
        refresh your app.

        Flags:
        -bots -> purge bot messages only
        -silent -> dont return any message
        -embeds -> only delete embed messages"""
        await ctx.message.delete()
        if flags:
            flags = str(flags).split(' ')
            opts = ['-bots', '-silent', '-embeds']
            for flag in flags:
                if flag.lower() not in opts:
                    flags.remove(flag)
        else:
            flags = []

        def check(message):
            if message.pinned:
                return False
            if "-bots" in flags:
                if not message.author.bot:
                    return False
                else:
                    return True
            elif "-embeds" in flags:
                if len(message.embeds) > 0:
                    return True
            else:
                return True

        if amount >= 50:
            msg = await ctx.send(embed=discord.Embed(title=f"Are you __sure__ you want to delete **__{amount}__** "
                                                           "messages?",
                                                     description="Reply `yes` to continue, or `no` to cancel, within"
                                                                 " the next 30s.",
                                                     color=discord.Color.red()))
            try:
                confirm = await self.bot.wait_for("message",
                                                  check=lambda m: m.author == ctx.author and ctx.channel == m.channel,
                                                  timeout=30)
                await confirm.delete()
                if confirm.content.lower().startswith(('n', 'c')):
                    return await msg.edit(embed=discord.Embed(title="Cancelled Purge."))
                else:
                    pass
            except asyncio.TimeoutError:
                return await msg.edit(embed=discord.Embed(title="Cancelled Purge."))
        msgs = await ctx.channel.purge(limit=amount if amount <= 500 else 500, check=check
                                       )
        if "-silent" not in flags:
            embed = discord.Embed(
                title=f"Purged {len(msgs)} messages.",
                color=discord.Color.blue()
            )
            return await ctx.send(embed=embed, delete_after=10)

    @bulkdel.command(name="text", aliases=['contains'])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    async def del_text(self, ctx, limit: int, case_sensitive: typing.Optional[bool], *, text: str):
        """Checks if <text> is in a message before deleting it."""
        text = text.lower() if not case_sensitive else text

        def ch(m):
            co = m.content.lower() if not case_sensitive else m.content
            if text in co:
                return True
            else:
                return False

        await ctx.message.delete()
        msgs = await ctx.channel.purge(limit=limit, check=ch)
        embed = discord.Embed(
            title=f"Purged {len(msgs)} messages.",
            color=discord.Color.blue()
        )
        embed.url = await self.work_and_post(msgs)
        await ctx.send(embed=embed, delete_after=10)

    @bulkdel.command(name="after")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    async def bulkdel_after(self, ctx, message: discord.Message, stop: typing.Union[discord.Message, bool] = None, *,
                            optional_amount: int = 300):
        """Purges 300 (or optional_amount) messages AFTER <message>. **this does not include <message>**.
        message takes an ID, channelID-messageID, or url."""
        stop = None if not stop else stop

        def check(messag):
            if messag.pinned:
                return False
            else:
                return True

        await ctx.message.delete()
        msgs = await ctx.channel.purge(limit=optional_amount, after=message.created_at, check=check, before=stop)
        embed = discord.Embed(
            title=f"Purged {len(msgs)} messages.",
            color=discord.Color.blue()
        )
        url = await self.work_and_post(msgs)
        await ctx.send(embed=embed, delete_after=10)

    @bulkdel.command(name="around")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    async def bulkdel_around(self, ctx, message: discord.Message, *, optional_amount: int = 101):
        """Purges 300 (or optional_amount) messages AROUND <message>. **this does not include <message>**.
        message takes an ID, channelID-messageID, or url."""
        if optional_amount > 101:
            await ctx.send("Max messages for `around` is `101`. Shorting down.", delete_after=3)
            optional_amount = 101

        def check(messag):
            if messag.pinned:
                return False
            else:
                return True

        await ctx.message.delete()
        msgs = await ctx.channel.purge(limit=optional_amount, around=message.created_at, check=check)
        embed = discord.Embed(
            title=f"Purged {len(msgs)} messages.",
            color=discord.Color.blue()
        )
        url = await self.work_and_post(msgs)
        await ctx.send(embed=embed, delete_after=10)

    @commands.command(name='warn', aliases=['w'])
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def warn(self, ctx, user: discord.Member, *, reason: str = "No Reason Provided."):
        """Warn somebody. Requires "kick members" permission.

        cooldown: 3s"""
        case = await entry_helper.create_modlog_case(ctx, author=ctx.author, target=user, reason=reason,
                                                     color=discord.Color.orange())
        if datetime.datetime.utcnow().day == 25 and datetime.datetime.utcnow().month == 12:
            reason += f" [Merry christmas]"
        try:
            await user.send(f"You have been warned in {ctx.guild.name} for: {reason}\n__Case ID: {case.case_id}__")
        except discord.Forbidden:
            pass
        finally:
            # print("finally reached")
            await ctx.send(f"**\U00002705 warned {escape_mentions(user.name)} for: {escape_mentions(reason)}**\n"
                           f"*case id: {case.case_id}*")
            return await ctx.message.delete(delay=0.2)

    @commands.command(name="kick", aliases=['k', 'boot', 'remove', 'assistedLeave'])
    @commands.bot_has_permissions(kick_members=True, manage_messages=True)
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True, manage_messages=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def kick(self, ctx, user: discord.Member, *, reason: str = "No Reason Provided."):
        """Kicks a member from the server. You (and the bot) must have kick members permission and be higher then the
        target.
        cooldown: 5s"""
        if ctx.author != ctx.guild.owner:
            check2 = entry_helper.check_height(user.top_role, ctx.author.top_role)
            if check2 is False:
                await ctx.send(f"You need to be higher then the role '{escape_mentions(user.top_role.name)}'!")
                return await ctx.message.delete(delay=0.2)
        check1 = entry_helper.check_height(user.top_role, ctx.me.top_role)
        if check1 is False:
            await ctx.send(f"I need to be higher then the role '{escape_mentions(user.top_role.name)}'!")
            return await ctx.message.delete(delay=0.2)
        case = await entry_helper.create_modlog_case(ctx, author=ctx.author, target=user, reason=reason,
                                                     color=discord.Color.dark_orange(), _type='kicks')
        if datetime.datetime.utcnow().day == 25 and datetime.datetime.utcnow().month == 12:
            reason += f" [Merry christmas]"
        try:
            await user.send(
                f"You have been kicked from {ctx.guild.name} for: {reason}\n\nIf you have an invite, you may rejoin."
                f" Or you can appeal it (with below details, __Case ID: {case.case_id}__)")
        except discord.Forbidden:
            pass
        await user.kick(reason=f"Action by {ctx.author.name} with reason: {reason}")
        reason = reason.replace("*", "\u200b*\u200b")
        await ctx.send(f"**\U00002705 kicked {escape_mentions(user.name)} for: {escape_mentions(reason)}**\n"
                       f"*case id: {case.case_id}*")
        return await ctx.message.delete(delay=0.2)

    @commands.command(name="ban", aliases=['b', 'forceremove', 'tempban'])
    @commands.bot_has_permissions(ban_members=True, manage_messages=True)
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, user: Union[discord.Member, discord.User, int], delete_messages_days: typing.Optional[int],
                  *, reason: str = "No Reason Provided."):
        """Bans someone. this person can either be in the server, or you can provide an ID.
        requires ban members permissions, and for us to be higher then the member if they are in the server."""
        delete_messages_days = 1 if not delete_messages_days else delete_messages_days
        if ctx.author != ctx.guild.owner and not isinstance(user, (int, discord.User)):
            check2 = entry_helper.check_height(user.top_role, ctx.author.top_role)
            if check2 is False:
                await ctx.send(f"You need to be higher then the role '{escape_mentions(user.top_role.name)}'!")
                return await ctx.message.delete(delay=0.2)
        if isinstance(user, discord.Member):
            check1 = entry_helper.check_height(user.top_role, ctx.me.top_role)
            if check1 is False:
                await ctx.send(f"I need to be higher then the role '{escape_mentions(user.top_role.name)}'!")
                return await ctx.message.delete(delay=0.2)
        if isinstance(user, int):
            try:
                user = await self.bot.fetch_user(user)
            except discord.NotFound:
                return await ctx.send("\U0001f6ab user not found. Is the ID correct?")
        case = await entry_helper.create_modlog_case(ctx, author=ctx.author, target=user, reason=reason,
                                                     color=discord.Color.red(), _type='bans')
        if datetime.datetime.utcnow().day == 25 and datetime.datetime.utcnow().month == 12:
            reason += f" [Merry christmas]"
        if not isinstance(user, (int, discord.User)):
            try:
                await user.send(
                    f"You have been banned from {ctx.guild.name} for: {reason}\n__Case ID: {case.case_id}__")
            except discord.Forbidden:
                pass
        await ctx.guild.ban(user,
                            reason=f"Action by {ctx.author.name} with reason: {reason}",
                            delete_message_days=delete_messages_days)
        reason = reason.replace("*", "\u200b*\u200b")
        await ctx.send(f"**\U00002705 banned {escape_mentions(user.name)} for: {escape_mentions(reason)}**\n"
                       f"*case id: {case.case_id}*")
        return await ctx.message.delete(delay=0.2)

    @commands.command(name="softban", aliases=['softkick', 'quickpurge', 'sb', 'qp'])
    @commands.bot_has_permissions(manage_messages=True, ban_members=True, create_instant_invite=True, manage_guild=True)
    @commands.has_permissions(ban_members=True, manage_messages=True)
    async def soft_ban(self, ctx, member: discord.Member, *, reason: str = "No Reason Provided."):
        """Quickly bans and unbans the target (MEMBER must be in the server currently) and re-invites them.

        __This will delete 7 days of messages from that user.__"""
        invite = ''
        c1 = entry_helper.check_height(member.top_role, ctx.author.top_role)
        c2 = entry_helper.check_height(member.top_role, ctx.guild.me.top_role)
        if not c1:
            return await ctx.send(f"<:fail:642157573583142932> You need to be higher then the "
                                  f"__{escape_mentions(member.top_role.name)}__ role!")
        elif not c2:
            return await ctx.send(f"<:fail:642157573583142932> I need to be higher then the "
                                  f"__{escape_mentions(member.top_role.name)}__ role!")
        invites = await ctx.guild.invites()
        if len(invites) == 0:
            for channel in ctx.guild.channels:
                try:
                    invite = await channel.create_invite(max_age=3600 * 48, max_uses=1)
                    invite = invite.url
                except discord.Forbidden:
                    continue
                else:
                    break
        else:
            try:
                invite = [inv.url for inv in invites if inv.max_age == 0 and inv.max_uses == 0][0]
            except Exception as e:
                await ctx.send(str(e))
                return await ctx.send(f"<:fail:642157573583142932> No valid invites found.")
        if datetime.datetime.utcnow().day == 25 and datetime.datetime.utcnow().month == 12:
            reason += f" [Merry christmas]"
        case = await entry_helper.create_modlog_case(ctx, author=ctx.author, target=member, reason=reason, _type="bans",
                                                     color=discord.Color.dark_red(), sub="SoftBan/quickpurge")
        try:
            await member.send(
                f"You were softbanned from {ctx.guild.name}. Rejoin with {invite}\n__Case ID: {case.case_id}__")
        except discord.Forbidden:
            pass
        await member.ban(reason=reason)
        await member.unban(reason="Softban Unban")
        return await ctx.send(f"<:success:642157573763629072> **SoftBanned {escape_mentions(member.display_name)}"
                              f" for: {escape_mentions(reason)}, deleting 7 days of messages.**")

    @commands.group(name="case", aliases=['viewcase', 'seecase', 'getcase'], invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def getcase(self, ctx, *, casenum: int):
        """Gets a case ID. requires you have manage roles permission."""
        data = config.read("./data/core.json")
        caseid = str(casenum)
        for _type in data[str(ctx.guild.id)].keys():
            if _type not in ['warns', 'mutes', 'kicks', 'bans', 'unbans', 'unmutes']:
                continue
            else:
                case = data[str(ctx.guild.id)][_type].get(caseid)
                if case:
                    # await ctx.send(case)
                    if case:
                        made = datetime.datetime.strptime(case["created at"], '%Y-%m-%d %H:%M:%S.%f')
                        x = f"```md\n# Case #{caseid}:\n- Subtype: {case['subtype']}\n- Moderator: " \
                            f"{str(self.bot.get_user(case['author']))}\n- Target: {str(self.bot.get_user(case['target']))}" \
                            f"\n- Reason: {case['reason']}\n- created: {str(made.date())} @ {str(made.time()).split('.')[0]}" \
                            f" (yyyy-mm-dd hh:mm:ss)\n- Modlog entry: {case['mod message url']}\n```"
                        return await ctx.send(x)
        else:
            return await ctx.send("case not found.")

    @getcase.command(name="delete", aliases=['forget', 'remove'])
    @commands.has_permissions(manage_guild=True)
    async def case_delete(self, ctx, *, casenum: int):
        """Deletes a case. This is not undo-able."""
        data = config.read("./data/core.json")
        caseid = str(casenum)
        for _type in data[str(ctx.guild.id)].keys():
            if _type not in ['warns', 'mutes', 'kicks', 'bans', 'unbans', 'unmutes']:
                continue
            else:
                case = data[str(ctx.guild.id)][_type].get(caseid)
                if case:
                    del data[str(ctx.guild.id)][_type][caseid]
                    config.write("./data/core.json", data)
                    return await ctx.send(f"Removed case #{casenum}.")
        else:
            return await ctx.send("case not found.")

    @getcase.command(name="reason", aliases=['edit', 'change'])
    @commands.has_permissions(manage_messages=True, manage_guild=True)
    async def case_edit(self, ctx, casenum: int, *, newreason: str):
        """Change the reasoning of a case."""
        data = config.read("./data/core.json")
        caseid = str(casenum)
        for _type in data[str(ctx.guild.id)].keys():
            if _type not in ['warns', 'mutes', 'kicks', 'bans', 'unbans', 'unmutes']:
                continue
            else:
                case = data[str(ctx.guild.id)][_type].get(caseid)
                if case:
                    if self.bot.get_user(case['author']) != ctx.author:
                        return await ctx.send("You can't edit this case as you did not create it.")
                    try:
                        msg = await commands.MessageConverter().convert(ctx, case["mod message url"])
                        embed = msg.embeds[0]
                        tmention = self.bot.get_user(case['target']).mention if self.bot.get_user(
                            case['target']) else '<@' + str(case['target']) + '>'
                        embed.description = f"**Moderator:** {ctx.author.mention} (`{str(ctx.author)}`)\n**Offending User:** " \
                                            f"{tmention} (`{str(self.bot.get_user(case['target']))}`)\n**Reason:** {newreason}"
                        embed.timestamp = datetime.datetime.utcnow()
                        await msg.edit(embed=embed)
                    except Exception as e:
                        await ctx.send(f"was unable to edit modlog message: `{str(e)}`")
                    case["reason"] = newreason
                    config.write("./data/core.json", data)
                    return await ctx.send(f"edited case #{casenum}.")
        else:
            return await ctx.send("case not found.")

    @commands.command(name="mute")
    @commands.bot_has_permissions(manage_roles=True, manage_messages=True)
    @commands.has_permissions(kick_members=True)
    async def mute(self, ctx, user: discord.Member, *, reason: str = "No Reason Provided."):
        """Mute somebody. Pretty simple. __Must be unmuted manually.__

        "EXP_time" is an experimental value for auto-unmuting. Please do not actually use this."""
        raisins = reason.split(" ")
        try:
            EXP_time = entry_helper.Converters.timeFromHuman(raisins[0])
            key = EXP_time[1]
            EXP_time = EXP_time[0]
            reason = ' '.join(raisins[1:])
        except (KeyError, ValueError):
            EXP_time = None
            key = None
        if user.top_role >= ctx.me.top_role or (user.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner):
            return await ctx.send("That user can not be muted due to hierarchy.")
        data = read("./data/core.json")
        g = str(ctx.guild.id)
        mrid = data[g]["muted role"]  # .get to support older config
        if ctx.guild.get_role(mrid) is None:
            if ctx.guild.me.guild_permissions.manage_roles:
                mutedrole = await ctx.guild.create_role(name="Muted", color=discord.Color(0x2f3136))
                await Configuration.set_up_muted_role(ctx, mutedrole)
                await ctx.send(f"It seems that you didn't have a muted role set! I have made one for now, "
                               f"{mutedrole.mention}, but it will only work this one time. Run `{ctx.prefix}mutedrole "
                               f"[role name]` to set one.", delete_after=10)
            else:
                return await ctx.send(f"It appears that you haven't set a muted role, and i couldn't create one"
                                      f" automatically. Please run `{ctx.prefix}mutedrole [role]`. Command stopped.")
        else:
            mutedrole = ctx.guild.get_role(mrid)
        case = await entry_helper.create_modlog_case(ctx, author=ctx.author, target=user, color=discord.Color.blue(),
                                                     reason=reason, _type="mutes")
        await user.add_roles(mutedrole, reason=f"case ID {case.case_id}.")
        await ctx.message.delete()
        if EXP_time:
            auto = f"`Auto-unmute in: {key}`"
        else:
            auto = ''
        if datetime.datetime.utcnow().day == 25 and datetime.datetime.utcnow().month == 12:
            reason += f" [Merry christmas]"
        try:
            await user.send(
                f"You have been Muted in **{ctx.guild.name}** for: **{reason}**.\n{auto}\n__Case ID: {case.case_id}__")
        except discord.Forbidden:
            pass
        reason = reason.replace("*", "\u200b*\u200b")
        await ctx.send(f"**\U00002705 muted {escape_mentions(user.name)} for: {escape_mentions(reason)}**\n"
                       f"*case id: {case.case_id}*. {auto}")
        if EXP_time:
            await asyncio.sleep(EXP_time)
            _ctx = ctx
            _ctx.command = self.bot.get_command("unmute")
            await _ctx.invoke(_ctx.command, user, reason=f"Auto Unmute (muted {key} ago).")

    @commands.command(name="unmute")
    @commands.bot_has_permissions(manage_roles=True, manage_messages=True)
    @commands.has_permissions(kick_members=True)
    async def unmute(self, ctx, user: discord.Member, *, reason: str = "No Reason Provided."):
        """Unmute somebody. Pretty simple."""
        if user.top_role >= ctx.me.top_role or user.top_role >= ctx.author.top_role:
            return await ctx.send("That user can not be unmuted due to hierarchy.")
        data = read("./data/core.json")
        g = str(ctx.guild.id)
        mrid = data[g].get("muted role")  # .get to support older config
        if mrid is None or ctx.guild.get_role(mrid) is None:
            return await ctx.send("You don't have a muted role set, so they aren't muted.")
        else:
            mutedrole = ctx.guild.get_role(mrid)
        case = await entry_helper.create_modlog_case(ctx, author=ctx.author, target=user,
                                                     color=discord.Color.lighter_grey(),
                                                     reason=reason, _type="mutes", sub="unmute")
        await user.remove_roles(mutedrole, reason=f"case ID {case.case_id}.")
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        reason = reason.replace("*", "\u200b*\u200b")
        await ctx.send(f"**\U00002705 unmuted {escape_mentions(user.name)} for: {escape_mentions(reason)}**\n"
                       f"*case id: {case.case_id}*")

    @commands.group(name="cases", invoke_without_command=True)
    @commands.bot_has_permissions(manage_messages=True, add_reactions=True, embed_links=True)
    @commands.has_permissions(manage_guild=True)
    async def caseslist(self, ctx, detailed: bool = False):
        """Lists all cases.

        run "g!cases True" to get a more detailed list. Note this increases the amount of pages you will need to scroll through"""
        es = discord.utils.escape_markdown
        paginator = PaginatorEmbedInterface(self.bot, commands.Paginator(max_size=750, prefix="", suffix=""))
        # prefix + suffix = "" because it stops it breaking markdown (for the box design)
        data = config.read("./data/core.json").get(str(ctx.guild.id))
        things = ['warns', 'mutes', 'kicks', 'bans', 'unbans']
        msgs = []
        for case_type in things:
            for case_id, case_data in data[case_type].items():
                case_data["ctx"] = ctx
                case_data["case_id"] = case_id
                case = await entry_helper.Case.from_dict(case_data)

                msg = f"```md\n# Case action: {case_type.replace('s', '')}\n# Case ID: {case.id}\n# Case Target: {es(str(case.target))}"
                if detailed:
                    msg += f"\n# Moderator: {es(str(case.author))}\n# Reason: {es(case.reason[:300])}"
                if len(msg) >= 1600:
                    msg = msg[:1590] + '...'
                msg += '```'
                # await paginator.add_line(msg, empty=True)
                n = case.id
                msgs.append((int(n), msg))
        for _, content in sorted(msgs):
            await paginator.add_line(content, empty=True)
        await paginator.send_to(ctx.channel)

    @caseslist.command(name="for", aliases=['by', 'target'])
    @commands.bot_has_permissions(manage_messages=True, add_reactions=True, embed_links=True)
    @commands.has_permissions(manage_guild=True)
    async def cases_for(self, ctx, *, target: typing.Union[discord.User, int] = None):
        """Gets cases the target was... the target. e.g: ?cases for bob == target: bob"""
        async with ctx.channel.typing():
            data = read("./data/core.json")
            if isinstance(target, int):
                try:
                    target = await self.bot.fetch_user(target)
                except discord.NotFound:
                    await ctx.send("target not found.")
                    target = None
            target = target if target else ctx.author
            paginator = PaginatorEmbedInterface(self.bot, commands.Paginator(max_size=1000))
            await paginator.add_line("[start]")
            unchecked = 0
            if data.get(str(ctx.guild.id)):
                for _type in data[str(ctx.guild.id)].keys():
                    if _type not in ['warns', 'mutes', 'unmutes', 'kicks', 'bans', 'unbans']:
                        continue
                    for _case in data[str(ctx.guild.id)][_type].keys():
                        data[str(ctx.guild.id)][_type][_case]['ctx'] = ctx
                        case = await entry_helper.Case.from_dict(data[str(ctx.guild.id)][_type][_case])
                        if isinstance(case.target, (discord.Member, discord.User)):
                            if case.target.id == target.id:
                                await paginator.add_line(f"Case {_case}: {_type.replace('s', '', 1)}\n")
                        else:
                            _target = self.bot.get_user(target)
                            if _target is None:
                                try:
                                    _target = await self.bot.fetch_user(case.target)
                                except discord.NotFound:
                                    unchecked += 1
                                    continue
                            if _target == target:
                                await paginator.add_line(f"Case {_case}: {_type.replace('s', '', 1)}\n")
            if unchecked > 0:
                await paginator.add_line(f"! {unchecked} cases were unavailable.")
            await paginator.add_line("[end]")
        await paginator.send_to(ctx.channel)

    @commands.command(name="statusads")
    @commands.bot_has_permissions(kick_members=True)
    @commands.has_permissions(kick_members=True)
    async def boot_those_status_ads(self, ctx: commands.Context, ignore_non_invite_links: bool = True):
        """Recursively goes through the member list and kicks members who are status advertising."""
        kicked = []
        for member in ctx.guild.members:
            if member.top_role >= ctx.me.top_role or member.top_role >= ctx.author.top_role or member.bot:
                continue
            status = str(member.activity)
            invites = re.findall(r"(?:https?://)?discord(?:app\.com/invite|\.gg)/?[a-zA-Z0-9]+/?", status)
            if invites:
                kicked.append(member)
                self.bot.loop.create_task(member.kick(reason=f"Status Advertising (detected: "
                                                             f"{', '.join(invites)})"))
                continue
            if ignore_non_invite_links is False:
                URLs = re.findall("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
                if URLs:
                    if invites:
                        kicked.append(member)
                        self.bot.loop.create_task(member.kick(reason=f"Status Advertising (detected: "
                                                                     f"{', '.join(URLs)})"))
                        continue
        desc = str(", ".join([str(x) for x in kicked]))[:2000]
        e = discord.Embed(
            title=f"Kicked {len(kicked)} members!",
            description=f"kicked {desc}",
            colour=discord.Colour.green()
        )
        e.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url_as(static_format="png"))
        e.set_footer(icon_url="https://cdn.discordapp.com/emojis/706509653726593064.gif?v=1",
                     text="If there are many people who are kicked, it may take time to actually kick all of them.")
        m = await ctx.send(embed=e)
        await asyncio.sleep(len(kicked))
        e.set_footer(text=discord.Embed.Empty, icon_url=discord.Embed.Empty)
        try:
            await m.edit(embed=e)
        except:
            return

    @commands.Cog.listener()
    async def on_message(self, message):
        ctx = await self.bot.get_context(message)
        if message.guild is None or message.author.bot:
            return
        else:
            data = read("./data/core.json")
            if data.get(str(message.guild.id)):
                if data[str(message.guild.id)].get("muted role"):
                    if data[str(message.guild.id)].get("muted role") in [x.id for x in message.author.roles]:
                        try:
                            await message.delete()
                        except discord.NotFound:
                            pass
                        roles = [x.mention for x in message.guild.roles if x.mentionable and
                                 any([x.permissions.kick_members or x.permissions.ban_members
                                      or x.permissions.administrator])]
                        try:
                            role = random.choice(roles)
                        except IndexError:
                            role = None
                        modlog = entry_helper.Case(
                            await self.bot.get_context(message)).modlog_channel  # should really be ctx, but it usually
                        # just gets guild so it *should* be fine.
                        # No Guarantees and no refunds.
                        if modlog:
                            await modlog.send(role, embed=discord.Embed(description=f"{message.author.mention}"
                                                                                    f" is bypassing mute in "
                                                                                    f"{message.channel.mention}!\n\n"
                                                                                    f"Message Content: ```md\n"
                                                                                    f"{message.content}\n```",
                                                                        color=discord.Color.red()), delete_after=30)
                        return
                    else:  # not muted
                        if message.content.startswith(self.bot.user.mention) and not ctx.valid:
                            await message.send(
                                f"Hello {message.author.mention}! Run `{self.bot.user.mention} help` to get my list "
                                f"of commands!",
                                delete_after=10)
            else:
                if message.content.startswith(self.bot.user.mention) and not ctx.valid:
                    await message.send(
                        f"Hello {message.author.mention}! Run `{self.bot.user.mention} help` to get my list "
                        f"of commands!",
                        delete_after=10)

    @commands.command(hidden=True)
    @commands.has_role(631741181424041984)
    async def ya(self, ctx):
        return await ctx.send("Due to the volume of support requests for yourapps, we have created a dedicated support "
                              "server where we have specially trained staff to help you with your issues better. "
                              "If you need to get support with yourapps, join https://discord.gg/Adp4y4v")


def setup(bot):
    bot.add_cog(Mod(bot))
