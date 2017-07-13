import aiohttp
from io import BytesIO
import inspect
import discord
from discord.ext import commands

from . import config
from PIL import Image


def convert_to_jpeg(pfile):
    # Open the file given
    img = Image.open(pfile)
    # Create the BytesIO object we'll use as our new "file"
    new_file = BytesIO()
    # Save to this file as jpeg
    img.save(new_file, format='JPEG')
    # In order to use the file, we need to seek back to the 0th position
    new_file.seek(0)
    return new_file


def get_all_commands(bot):
    """Returns a list of all command names for the bot"""
    # First lets create a set of all the parent names
    for cmd in bot.commands:
        yield from get_all_subcommands(cmd)


def get_all_subcommands(command):
    yield command
    if type(command) is discord.ext.commands.core.Group:
        for subcmd in command.commands:
            yield from get_all_subcommands(subcmd)


async def channel_is_nsfw(channel, db):
    if type(channel) is discord.DMChannel:
        server = 'DMs'
    elif channel.is_nsfw():
        return True
    else:
        server = str(channel.guild.id)

    channel = str(channel.id)

    channels = db.load('server_settings', key=server, pluck='nsfw_channels') or []
    return channel in channels


async def download_image(url):
    """Returns a file-like object based on the URL provided"""
    # Simply read the image, to get the bytes
    bts = await request(url, attr='read')
    if bts is None:
        return None

    # Then wrap it in a BytesIO object, to be used like an actual file
    image = BytesIO(bts)
    return image


async def request(url, *, headers=None, payload=None, method='GET', attr='json', force_content_type_json=False):
    # Make sure our User Agent is what's set, and ensure it's sent even if no headers are passed
    if headers is None:
        headers = {}

    headers['User-Agent'] = config.user_agent

    # Try 5 times
    for i in range(5):
        try:
            # Create the session with our headeres
            with aiohttp.ClientSession(headers=headers) as session:
                # Make the request, based on the method, url, and paramaters given
                async with session.request(method, url, params=payload) as response:
                    # If the request wasn't successful, re-attempt
                    if response.status != 200:
                        continue

                    try:
                        # Get the attribute requested
                        return_value = getattr(response, attr)
                        # Next check if this can be called
                        if callable(return_value):
                            # This is use for json; it checks the mimetype instead of checking if the actual data
                            # This causes some places with different mimetypes to fail, even if it's valid json
                            # This check allows us to force the content_type to use whatever content type is given
                            if force_content_type_json:
                                return_value = return_value(content_type=response.headers['content-type'])
                            else:
                                return_value = return_value()
                        # If this is awaitable, await it
                        if inspect.isawaitable(return_value):
                            return_value = await return_value

                        # Then return it
                        return return_value
                    except AttributeError:
                        # If an invalid attribute was requested, return None
                        return None
        # If an error was hit other than the one we want to catch, try again
        except:
            continue

async def convert(ctx, option):
    """Tries to convert a string to an object of useful representiation"""
    cmd = ctx.bot.get_command(option)
    if cmd:
        return cmd

    async def do_convert(converter, _ctx, _option):
        try:
            return await converter.convert(_ctx, _option)
        except commands.converter.BadArgument:
            return None

    member = await do_convert(commands.converter.MemberConverter(), ctx, option)
    if member:
        return member

    channel = await do_convert(commands.converter.TextChannelConverter(), ctx, option)
    if channel:
        return channel

    channel = await do_convert(commands.converter.VoiceChannelConverter(), ctx, option)
    if channel:
        return channel

    role = await do_convert(commands.converter.RoleConverter(), ctx, option)
    if role:
        return role


async def update_records(key, db, winner, loser):
    # We're using the Harkness scale to rate
    # http://opnetchessclub.wikidot.com/harkness-rating-system
    r_filter = lambda row: (row['member_id'] == str(winner.id)) | (row['member_id'] == str(loser.id))
    matches = await db.actual_load(key, table_filter=r_filter)

    winner_stats = {}
    loser_stats = {}
    try:
        for stat in matches:
            if stat.get('member_id') == str(winner.id):
                winner_stats = stat
            elif stat.get('member_id') == str(loser.id):
                loser_stats = stat
    except TypeError:
        pass

    winner_rating = winner_stats.get('rating') or 1000
    loser_rating = loser_stats.get('rating') or 1000

    # The scale is based off of increments of 25, increasing the change by 1 for each increment
    # That is all this loop does, increment the "change" for every increment of 25
    # The change caps off at 300 however, so break once we are over that limit
    difference = abs(winner_rating - loser_rating)
    rating_change = 0
    count = 25
    while count <= difference:
        if count > 300:
            break
        rating_change += 1
        count += 25

    # 16 is the base change, increased or decreased based on whoever has the higher current rating
    if winner_rating > loser_rating:
        winner_rating += 16 - rating_change
        loser_rating -= 16 - rating_change
    else:
        winner_rating += 16 + rating_change
        loser_rating -= 16 + rating_change

    # Just increase wins/losses for each person, making sure it's at least 0
    winner_wins = winner_stats.get('wins', 0)
    winner_losses = winner_stats.get('losses', 0)
    loser_wins = loser_stats.get('wins', 0)
    loser_losses = loser_stats.get('losses', 0)
    winner_wins += 1
    loser_losses += 1

    # Now save the new wins, losses, and ratings
    winner_stats = {'wins': winner_wins, 'losses': winner_losses, 'rating': winner_rating, 'member_id': str(winner.id)}
    loser_stats = {'wins': loser_wins, 'losses': loser_losses, 'rating': loser_rating, 'member_id': str(loser.id)}

    db.save(key, winner_stats)
    db.save(key, loser_stats)
