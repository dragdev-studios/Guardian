from utils import save
from discord.ext import commands
from aiohttp import web
import ssl
import threading
import asyncio
import typing
import markdown
import random


def html_response(text):
  cssfile = open("css/main.css", "r")
  css = cssfile.read()
  cssfile.close()
  return web.Response(text="<style>" +  css + "</style>" + text, content_type='text/html')

class Appeals(commands.Cog, name="Server Appeal Policies"):
  def __init__(self, bot):
    self.bot = bot
    self.policies = save.Save("appeal_policies")
    routes = web.RouteTableDef()
    routes = web.RouteTableDef()

    @routes.get('/{serverid:[0-9]+}/')
    @routes.get('/{serverid:[0-9]+}')
    async def policy(request):
      guild = bot.get_guild(int(request.match_info['serverid']))
      if not guild:
        return html_response(text=f"<h1>That isn't a valid server ID</h1><ul><li>Did you type it correctly?</li><li>Am I in it?</li></ul>")
      policies = self.policies.read_key(guild.id)
      policy_message = ""
      if not policies:
        policy_message = "<ul><li><p>This server hasn't set an appeals policy. Guess you aren't getting back then...</p></li>" \
                         "<li>If you're a server administrator you can set a policy with "\
                         "<code>g!setpolicy \"{policy1}\" \"{policy2}\" \"{policy3}\"...</code>. You <b>must</b> include the speech marks</li>" \
                         "<li>Markdown is supported in policies, enjoy :)</li></ul>"
      else:
        policy_message = "<ul><li>Full markdown is supported including links. Please be careful of any links on this page</li>" \
                         "<li>DragDev takes no responsibility for any user content on this page</li></ul><ol><li>" + \
			"</li><li>".join(markdown.markdown(policy
                                                          .replace('<', '&lt;')
     				                          .replace('>', '&gt;'), extensions=[
                                                                   "extra",
                                                                   "nl2br",
                                                                   "wikilinks"
                                                               ]
                                                           ) for policy in policies) + \
			"</li></ol>"
      return html_response(text=f"<h1>How to appeal in {guild.name.replace('<', '&lt;').replace('>', '&gt;')}:</h1>\n{policy_message}")

    @routes.get('/{serverid:.+}')
    async def invalid_id(request):
      return html_response(text=f"<h1>That isn't a valid server ID</h1><ul><li>Was it an integer?</li><li>Was it 18 digits long?</li></ul>")

    @routes.get('')
    async def home(request):
      return html_response(text=f"<h1>Welcome! Find server appeal policies on this website</h1><ul>"
                                f"<li>Our server <a href='/606866057998762023'>DragDev Studios</a></li>"
                                f"<li>The best testing server (according to Minion3665) <a href='/606866057998762023'>The Nothing Server</a></li>"
                                f"<li>Featured: <a href='/{random.choice(list(self.policies.load_data().keys()))}'>a random server</a></li>"
                                f"<li>or any server of your choice...</li></ul>")

    self.app = web.Application()
    self.app.add_routes(routes)

    self.runner = web.AppRunner(self.app)

    async def run_server():
      await self.runner.setup()

      sites = []

      sites.append(web.TCPSite(self.runner, "127.0.0.1", 9001, reuse_port=True, reuse_address=True))

      for site in sites:
        await site.start()
    bot.loop.create_task(run_server())

  @commands.command(name="setpolicy", aliases=["set", "pset", "appealset"])
  @commands.has_permissions(administrator=True)
  async def set_policy(self, ctx, *policies):
    """Set the appeal policy for your server

    Run `g!setpolicy "policy1" "policy2" "policy3"`. You __must__ include the speech marks

    *Note: Omit all policies to clear the appeal policies for your server*
    """
    self.policies.save_key(ctx.guild.id, policies)
    if policies:
      await ctx.send(f"Set {len(policies)} appeal {'policy' if len(policies) == 1 else 'policies'}. "
                     f"Give members the link https://appeals.dragdev.xyz/{ctx.guild.id} to view them")
    else:
      await ctx.send(f"Cleared your servers appeal policies")

  def __unload(self):
    bot.loop.create_task(self.runner.cleanup())


def setup(bot):
  bot.add_cog(Appeals(bot))
