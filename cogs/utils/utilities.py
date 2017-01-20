import aiohttp
import io
import inspect

from . import config

def get_all_commands(bot):
    """Returns a list of all command names for the bot"""
    # First lets create a set of all the parent names
    parent_command_names = set(cmd.qualified_name for cmd in bot.commands.values())
    all_commands = []

    # Now lets loop through and get all the child commands for each command
    # Only the command itself will be yielded if there are no children
    for cmd_name in parent_command_names:
        cmd = bot.commands.get(cmd_name)
        for child_cmd in _get_all_commands(cmd):
            all_commands.append(child_cmd)

    return all_commands

def _get_all_commands(command):
    yield command.qualified_name
    try:
        non_aliases = set(cmd.name for cmd in command.commands.values())
        for cmd_name in non_aliases:
            yield from _get_all_commands(command.commands[cmd_name])
    except AttributeError:
        pass

def find_command(bot, command):
    """Finds a command (be it parent or sub command) based on string given"""
    # This method ensures the command given is valid. We need to loop through commands
    # As bot.commands only includes parent commands
    # So we are splitting the command in parts, looping through the commands
    # And getting the subcommand based on the next part
    # If we try to access commands of a command that isn't a group
    # We'll hit an AttributeError, meaning an invalid command was given
    # If we loop through and don't find anything, cmd will still be None
    # And we'll report an invalid was given as well
    cmd = None

    for part in command.split():
        try:
            if cmd is None:
                cmd = bot.commands.get(part)
            else:
                cmd = cmd.commands.get(part)
        except AttributeError:
            cmd = None
            break

    return cmd

async def download_image(url):
    """Returns a file-like object based on the URL provided"""
    headers = {'User-Agent': config.user_agent}
    # Simply download the image
    with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as r:
            # Then wrap it in a BytesIO object, to be used like an actual file
            image = io.BytesIO(await r.read())
    return image

async def request(url, *, headers=None, payload=None, method='GET', attr='json'):
    # Make sure our User Agent is what's set, and ensure it's sent even if no headers are passed
    if headers == None:
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
    r_filter = lambda row: (row['member_id'] == winner.id) | (row['member_id'] == loser.id)
    matches = await config.get_content(key, r_filter)

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

    if not await config.update_content(key, winner_stats, {'member_id': winner.id}):
        winner_stats['member_id'] = winner.id
        await config.add_content(key, winner_stats, {'member_id': winner.id})
    if not await config.update_content(key, loser_stats, {'member_id': loser.id}):
        loser_stats['member_id'] = loser.id
        await config.add_content(key, loser_stats, {'member_id': loser.id})
