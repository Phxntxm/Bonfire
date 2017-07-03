from .voice_utilities import *
import discord


class DJEvents:
    """A simple class to save our DJ objects, once someone is detected to have joined a channel,
    their DJ information will automatically update"""

    def __init__(self, bot):
        self.bot = bot
        self.djs = {}

    async def on_ready(self):
        for channel in [c for c in self.bot.get_all_channels() if isinstance(c, discord.VoiceChannel)]:
            for member in [m for m in channel.members if not m.bot]:
                if member.id not in self.djs:
                    dj = DJ(member, self.bot)
                    self.bot.loop.create_task(dj.resolve_playlist())
                    self.djs[member.id] = dj

    async def on_voice_state_update(self, member, _, after):
        if member and not member.bot and member.id not in self.djs:
            dj = DJ(member, self.bot)
            self.bot.loop.create_task(dj.resolve_playlist())
            self.djs[member.id] = dj
        # Alternatively, if the bot has joined the channel and we never detected the members that are in the channel
        # This most likely means the bot has just started up, lets get these user's ready too
        if member and member.id == member.guild.me.id and after and after.channel:
            for m in after.channel.members:
                if not m.bot and m.id not in self.djs:
                    dj = DJ(m, self.bot)
                    self.bot.loop.create_task(dj.resolve_playlist())
                    self.djs[m.id] = dj


class DJ(Playlist):
    def __init__(self, member, bot):
        super().__init__(bot)
        self.member = member
        self.playlists = []

    async def next_entry(self):
        """Get the next song in the playlist; this class will wait until the next song is ready"""
        entry = self.peek()

        # While we have an entry available
        while entry:
            # Check if we are ready or if we've errored, either way we'll pop it from the deque
            if entry.ready or entry.error:
                self.entries.rotate(-1)
                return entry
            # Otherwise, wait a second and check again
            else:
                await asyncio.sleep(1)

        # If we've reached here, we have no entries
        return None

    async def resolve_playlist(self):
        self.playlists = self.bot.db.load('user_playlists', key=self.member.id, pluck='playlists') or []
        self.clear()

        for pl in self.playlists:
            if pl['active']:
                for song in pl['songs']:
                    try:
                        await self.add_entry(song['url'])
                    except ExtractionError:
                        # For now, just silently ignore this
                        pass


def setup(bot):
    bot.add_cog(DJEvents(bot))
