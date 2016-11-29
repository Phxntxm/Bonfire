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
        """Provides the progress of the current song

        EXAMPLE: !progress
        RESULT: 532 minutes! (Hopefully not)"""
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def join(self, ctx, *, channel: discord.Channel):
        """Joins a voice channel.

        EXAMPLE: !join Music
        RESULT: I'm in the Music voice channel!"""
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def summon(self, ctx):
        """Summons the bot to join your voice channel.

        EXAMPLE: !summon
        RESULT: I'm in your voice channel!"""
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def play(self, ctx, *, song: str):
        """Plays a song.
        If there is a song currently in the queue, then it is
        queued until the next song is done playing.
        This command automatically searches as well from YouTube.
        The list of supported sites can be found here:
        https://rg3.github.io/youtube-dl/supportedsites.html
        
        EXAMPLE: !play Song by Band
        RESULT: Song by Band will be queued to play!
        """
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(kick_members=True)
    async def volume(self, ctx, value: int = None):
        """Sets the volume of the currently playing song.

        EXAMPLE: !volume 50
        RESULT: My volume is now set to 50"""
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(kick_members=True)
    async def pause(self, ctx):
        """Pauses the currently played song.

        EXAMPLE: !pause
        RESULT: I'm paused!"""
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(kick_members=True)
    async def resume(self, ctx):
        """Resumes the currently played song.

        EXAMPLE: !resume
        RESULT: Ain't paused no more!"""
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(kick_members=True)
    async def stop(self, ctx):
        """Stops playing audio and leaves the voice channel.
        This also clears the queue.

        EXAMPLE: !stop
        RESULT: No more music"""
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def eta(self, ctx):
        """Provides an ETA on when your next song will play

        EXAMPLE: !eta
        RESULT: 5,000 days! Lol have fun"""
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def queue(self, ctx):
        """Provides a printout of the songs that are in the queue

        EXAMPLE: !queue
        RESULT: A list of shitty songs you probably don't wanna listen to"""
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def queuelength(self, ctx):
        """Prints the length of the queue

        EXAMPLE: !queuelength
        RESULT: Probably 10 songs"""
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def skip(self, ctx):
        """Vote to skip a song. The song requester can automatically skip.
        approximately 1/3 of the members in the voice channel
        are required to vote to skip for the song to be skipped.

        EXAMPLE: !skip
        RESULT: You probably still have to wait for others to skip...have fun listening still
        """
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(kick_members=True)
    async def modskip(self, ctx):
        """Forces a song skip, can only be used by a moderator

        EXAMPLE: !modskip
        RESULT: No more terrible song :D"""
        pass

    @commands.command(pass_context=True, no_pm=True, enabled=False)
    @checks.custom_perms(send_messages=True)
    async def playing(self, ctx):
        """Shows info about the currently played song.

        EXAMPLE: !playing
        RESULT: Information about the song that's currently playing!"""
        pass


def setup(bot):
    bot.add_cog(Music(bot))
