from .utils import checks

import discord
from discord.ext import commands

class Music:
"""
This cog is simply created in order to add all commands in the playlist cog
in case 'this' instance of the bot has not loaded the playlist cog.
This is useful to have the possiblity to split the music and text commands,
And still use commands that require another command to be passed
from the instance that hasn't loaded the playlist cog
"""
    def __init__(self, bot):
        self.bot = bot

    async def on_voice_state_update(self, before, after):
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def progress(self, ctx):
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def join(self, ctx, *, channel: discord.Channel):
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def summon(self, ctx):
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def play(self, ctx, *, song: str):
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(kick_members=True)
    async def volume(self, ctx, value: int = None):
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(kick_members=True)
    async def pause(self, ctx):
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(kick_members=True)
    async def resume(self, ctx):
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(kick_members=True)
    async def stop(self, ctx):
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def eta(self, ctx):
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def queue(self, ctx):
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def queuelength(self, ctx):
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def skip(self, ctx):
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(kick_members=True)
    async def modskip(self, ctx):
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def playing(self, ctx):
        pass

def setup(bot):
    bot.add_cog(Music(bot))
