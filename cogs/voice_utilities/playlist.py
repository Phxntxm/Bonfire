import datetime
import traceback
import asyncio
from collections import deque
from itertools import islice
from random import shuffle

from .source import YoutubeDLSource
from .entry import URLPlaylistEntry, get_header
from .exceptions import ExtractionError, WrongEntryTypeError, LiveStreamError
from .event_emitter import EventEmitter


class Playlist(EventEmitter):
    """
        A playlist is manages the list of songs that will be played.
    """

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.loop = bot.loop
        self.downloader = bot.downloader
        self.entries = deque()

    def __iter__(self):
        return iter(self.entries)

    def shuffle(self):
        shuffle(self.entries)

    def clear(self):
        self.entries.clear()

    @property
    def count(self):
        if self.entries:
            return len(self.entries)
        else:
            return 0

    async def add_entry(self, song_url, **meta):
        """Adds a song to this playlist"""
        entry = YoutubeDLSource(self, song_url)
        await entry.prepare()
        self.entries.append(entry)
        return entry

    async def import_from(self, playlist_url, requester):
        """
            Imports the songs from `playlist_url` and queues them to be played.

            Returns a list of `entries` that have been enqueued.
        """

        try:
            info = await self.downloader.safe_extract_info(self.loop, playlist_url, download=False)
        except Exception as e:
            raise ExtractionError('Could not extract information from {}\n\n{}'.format(playlist_url, e))

        if not info:
            raise ExtractionError('Could not extract information from %s' % playlist_url)

        if info.get('playlist') is None:
            raise WrongEntryTypeError('This is not a playlist!', False, playlist_url)

        # Once again, the generic extractor fucks things up.
        if info.get('extractor', None) == 'generic':
            url_field = 'url'
        else:
            url_field = 'webpage_url'

        yield len(info['entries'])

        for items in info['entries']:
            if items:
                entry = YoutubeDLSource(self, items[url_field])
                try:
                    await entry.prepare()
                except:
                    yield False
                else:
                    entry.requester = requester
                    self.entries.append(entry)
                    yield True
            else:
                yield False

    async def async_process_youtube_playlist(self, playlist_url, **meta):
        """
            Processes youtube playlists links from `playlist_url` in a questionable, async fashion.

            :param playlist_url: The playlist url to be cut into individual urls and added to the playlist
            :param meta: Any additional metadata to add to the playlist entry
        """

        try:
            info = await self.downloader.safe_extract_info(self.loop, playlist_url, download=False, process=False)
        except Exception as e:
            raise ExtractionError('Could not extract information from {}\n\n{}'.format(playlist_url, e))

        if not info:
            raise ExtractionError('Could not extract information from %s' % playlist_url)

        gooditems = []
        baditems = 0
        for entry_data in info['entries']:
            if entry_data:
                baseurl = info['webpage_url'].split('playlist?list=')[0]
                song_url = baseurl + 'watch?v=%s' % entry_data['id']

                try:
                    entry, elen = await self.add_entry(song_url, **meta)
                    gooditems.append(entry)
                except ExtractionError:
                    baditems += 1
                except Exception as e:
                    baditems += 1
            else:
                baditems += 1

        return gooditems

    async def async_process_sc_bc_playlist(self, playlist_url, **meta):
        """
            Processes soundcloud set and bancdamp album links from `playlist_url` in a questionable, async fashion.

            :param playlist_url: The playlist url to be cut into individual urls and added to the playlist
            :param meta: Any additional metadata to add to the playlist entry
        """

        try:
            info = await self.downloader.safe_extract_info(self.loop, playlist_url, download=False, process=False)
        except Exception as e:
            raise ExtractionError('Could not extract information from {}\n\n{}'.format(playlist_url, e))

        if not info:
            raise ExtractionError('Could not extract information from %s' % playlist_url)

        gooditems = []
        baditems = 0
        for entry_data in info['entries']:
            if entry_data:
                song_url = entry_data['url']

                try:
                    entry, elen = await self.add_entry(song_url, **meta)
                    gooditems.append(entry)
                except ExtractionError:
                    baditems += 1
                except Exception as e:
                    baditems += 1
            else:
                baditems += 1

        return gooditems

    def _add_entry(self, entry):
        self.entries.append(entry)

    async def next_entry(self):
        """Get the next song in the playlist; this class will wait until the next song is ready"""
        entry = self.peek()

        # While we have an entry available
        while entry:
            # Check if we are ready or if we've errored, either way we'll pop it from the deque
            if entry.ready or entry.error:
                return self.entries.popleft()
            # Otherwise, wait a second and check again
            else:
                await asyncio.sleep(1)

        # If we've reached here, we have no entries
        return None

    def peek(self):
        """
            Returns the next entry that should be scheduled to be played.
        """
        if self.entries:
            return self.entries[0]

    def count_for_user(self, user):
        return sum(1 for e in self.entries if e.meta.get('author', None) == user)
