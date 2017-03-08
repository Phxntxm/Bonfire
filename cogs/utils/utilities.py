import aiohttp
from io import BytesIO
import inspect

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
    parent_command_names = set(cmd.qualified_name for cmd in bot.commands.values())
    all_commands = []

    # Now lets loop through and get all the child commands for each command
    # Only the command itself will be yielded if there are no children
    for cmd_name in parent_command_names:
        cmd = bot.commands.get(cmd_name)
        for child_cmd in get_subcommands(cmd):
            all_commands.append(child_cmd)

    return all_commands


def get_subcommands(command):
    yield command.qualified_name
    try:
        non_aliases = set(cmd.name for cmd in command.commands.values())
        for cmd_name in non_aliases:
            yield from get_subcommands(command.commands[cmd_name])
    except AttributeError:
        pass

async def channel_is_nsfw(channel):
    server = str(channel.guild.id)
    channel = str(channel.id)

    server_settings = await config.get_content('server_settings', server)

    try:
        return channel in server_settings['nsfw_channels']
    except (TypeError, IndexError):
        return False


async def download_image(url):
    """Returns a file-like object based on the URL provided"""
    # Simply read the image, to get the bytes
    bts = await request(url, attr='read')
    if bts is None:
        return None

    # Then wrap it in a BytesIO object, to be used like an actual file
    image = BytesIO(bts)
    return image


async def request(url, *, headers=None, payload=None, method='GET', attr='json'):
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


async def update_records(key, winner, loser):
    # We're using the Harkness scale to rate
    # http://opnetchessclub.wikidot.com/harkness-rating-system
    r_filter = lambda row: (row['member_id'] == str(winner.id)) | (row['member_id'] == str(loser.id))
    matches = await config.filter_content(key, r_filter)

    winner_stats = {}
    loser_stats = {}
    try:
        for stat in matches:
            if stat.get('member_id') == winner.id:
                winner_stats = stat
            elif stat.get('member_id') == loser.id:
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
    winner_stats = {'wins': winner_wins, 'losses': winner_losses, 'rating': winner_rating}
    loser_stats = {'wins': loser_wins, 'losses': loser_losses, 'rating': loser_rating}

    if not await config.update_content(key, winner_stats, str(winner.id)):
        winner_stats['member_id'] = str(winner.id)
        await config.add_content(key, winner_stats)
    if not await config.update_content(key, loser_stats, str(loser.id)):
        loser_stats['member_id'] = str(loser.id)
        await config.add_content(key, loser_stats)
