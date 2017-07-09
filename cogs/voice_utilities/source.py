import discord
import time
import asyncio

from .exceptions import ExtractionError, WrongEntryTypeError, LiveStreamError
from .entry import get_header


class YoutubeDLSource(discord.FFmpegPCMAudio):
    def __init__(self, playlist, url):
        self.playlist = playlist
        self.loop = playlist.loop
        self.downloader = playlist.downloader
        self.url = url
        self.info = None
        self.ready = False
        self.error = False
        asyncio.run_coroutine_threadsafe(self.download(), self.loop)

    async def get_info(self):
        try:
            # First attempt to gather the information
            info = await self.downloader.extract_info(self.loop, self.url, download=False)
        except Exception as e:
            raise ExtractionError('Could not extract information from {}\n\n{}'.format(self.url, e))

        # Check if a playlist was provided
        if info.get('_type', None) == 'playlist':
            # It is possible that the 'playlist' is the search
            if info.get('extractor') == 'youtube:search':
                # If so, and we have no entries, then nothing with this search was found
                if len(info['entries']) == 0:
                    raise ExtractionError('Could not extract information from %s' % self.url)
                # Otherwise get the first result
                else:
                    info = info['entries'][0]
            # If this isn't a search, then it is a playlist, this can't be done
            else:
                raise WrongEntryTypeError("This is a playlist.", True,
                                          info.get('webpage_url', None) or info.get('url', None))

        if info['extractor'] in ['generic', 'Dropbox']:
            try:
                # unfortunately this is literally broken
                # https://github.com/KeepSafe/aiohttp/issues/758
                # https://github.com/KeepSafe/aiohttp/issues/852
                headers = await get_header(info['url'])
                content_type = headers.get('Content-Type')
            except Exception as e:
                content_type = None

            if content_type:
                if content_type.startswith(('application/', 'image/')):
                    if '/ogg' not in content_type:  # How does a server say `application/ogg` what the actual fuck
                        raise ExtractionError("Invalid content type \"%s\" for url %s" % (content_type, song_url))
                if headers.get('ice-audio-info'):
                    raise LiveStreamError("Cannot download from a livestream")

        if info.get('is_live', False):
            raise LiveStreamError("Cannot download from a livestream")

        # Set our info
        self.info = info

    async def prepare(self):
        await self.get_info()
        return self.info

    async def download(self):
        try:
            result = await self.downloader.extract_info(self.loop, self.url, download=True)
        except Exception as e:
            self.error = True
            raise ExtractionError(e)
        if result:
            self.ready = True
            opts = {
                'before_options': '-nostdin',
                'options': '-vn -b:a 128k'
            }
            super().__init__(self.downloader.ytdl.prepare_filename(result), **opts)

    @property
    def title(self):
        return self.info.get('title', 'Untitled')

    @property
    def thumbnail(self):
        return self.info.get('thumbnail', None)

    @property
    def length(self):
        return self.info.get('duration') or 0

    @property
    def progress(self):
        if hasattr(self, 'start_time') and self.start_time:
            return round(time.time() - self.start_time)

    @property
    def remaining(self):
        length = self.length
        progress = self.progress
        if length and progress:
            return length - progress

    @property
    def embed(self):
        """A property that returns an embed that can be used to display information about this particular song"""
        # Create the embed object we'll use
        embed = discord.Embed()
        # Fill in the simple things
        embed.add_field(name='Title', value=self.title, inline=False)
        embed.add_field(name='Requester', value=self.requester.display_name, inline=False)
        if self.thumbnail:
            embed.set_thumbnail(url=self.thumbnail)
        # Get the current length of the song and display this
        if self.length:
            length = divmod(round(self.length, 0), 60)
            fmt = "{0[0]}m {0[1]}s".format(length)
            embed.add_field(name='Duration', value=fmt, inline=False)
        # And return the embed we created
        return embed
