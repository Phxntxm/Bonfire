import ruamel.yaml as yaml
import asyncio
import rethinkdb as r
import pendulum

loop = asyncio.get_event_loop()
global_config = {}

# Ensure that the required config.yml file actually exists
try:
    with open("config.yml", "r") as f:
        global_config = yaml.load(f)
except FileNotFoundError:
    print("You have no config file setup! Please use config.yml.sample to setup a valid config file")
    quit()

try:
    bot_token = global_config["bot_token"]
except KeyError:
    print("You have no bot_token saved, this is a requirement for running a bot.")
    print("Please use config.yml.sample to setup a valid config file")
    quit()

try:
    owner_ids = global_config["owner_id"]
except KeyError:
    print("You have no owner_id saved! You're not going to be able to run certain commands without this.")
    print("Please use config.yml.sample to setup a valid config file")
    quit()


# This is a simple class for the cache concept, all it holds is it's own key and the values
# With a method that gets content based on it's key
class Cache:
    def __init__(self, key):
        self.key = key
        self.values = {}
        self.refreshed = pendulum.utcnow()
        loop.create_task(self.update())

    async def update(self):
        self.values = await get_content(self.key)
        self.refreshed = pendulum.utcnow()


# Default bot's description
bot_description = global_config.get("description")
# Bot's default prefix for commands
default_prefix = global_config.get("command_prefix", "!")
# The key for bots.discord.pw and carbonitex
discord_bots_key = global_config.get('discord_bots_key', "")
carbon_key = global_config.get('carbon_key', "")
# The client ID for twitch requsets
twitch_key = global_config.get('twitch_key', "")
# The invite link for the server made for the bot
dev_server = global_config.get("dev_server", "")

# The variables needed for sharding
shard_count = global_config.get('shard_count', 1)
shard_id = global_config.get('shard_id', 0)

# The default status the bot will use
default_status = global_config.get("default_status", "")
# The steam API key
steam_key = global_config.get("steam_key", "")
# The key for youtube API calls
youtube_key = global_config.get("youtube_key", "")
# The rethinkdb hostname
db_host = global_config.get('db_host', 'localhost')
# The rethinkdb database name
db_name = global_config.get('db_name', 'Discord_Bot')
# The rethinkdb certification
db_cert = global_config.get('db_cert', '')
# The rethinkdb port
db_port = global_config.get('db_port', 28015)
# The user and password assigned
db_user = global_config.get('db_user', 'admin')
db_pass = global_config.get('db_pass', '')
# We've set all the options we need to be able to connect
# so create a dictionary that we can use to unload to connect
# db_opts = {'host': db_host, 'db': db_name, 'port': db_port, 'ssl':
# {'ca_certs': db_cert}, 'user': db_user, 'password': db_pass}
db_opts = {'host': db_host, 'db': db_name, 'port': db_port, 'user': db_user, 'password': db_pass}

possible_keys = ['prefixes', 'battle_records', 'boops', 'server_alerts', 'user_notifications', 'nsfw_channels',
                 'custom_permissions', 'rules', 'overwatch', 'picarto', 'twitch', 'strawpolls', 'tags',
                 'tictactoe', 'bot_data', 'command_manage']

# This will be a dictionary that holds the cache object, based on the key that is saved
cache = {}

# Populate cache with each object
# With the new saving method, we're not going to be able to cache the way that I was before
# This is on standby until I rethink how to do this, because I do still want to cache data
"""for k in possible_keys:
    ca che[k] = Cache(k)"""

# We still need 'cache' for prefixes and custom permissions however, so for now, just include that
cache['prefixes'] = Cache('prefixes')
cache['custom_permissions'] = Cache('custom_permissions')

async def update_cache():
    for value in cache.values():
        await value.update()

async def update_records(key, winner, loser):
    # We're using the Harkness scale to rate
    # http://opnetchessclub.wikidot.com/harkness-rating-system
    r_filter = lambda row: (row['member_id'] == winner.id) | (row['member_id'] == loser.id)
    matches = await get_content(key, r_filter)

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

    if not await update_content(key, winner_stats, {'member_id': winner.id}):
        winner_stats['member_id'] = winner.id
        await add_content(key, winner_stats, {'member_id': winner.id})
    if not await update_content(key, loser_stats, {'member_id': loser.id}):
        loser_stats['member_id'] = loser.id
        await add_content(key, loser_stats, {'member_id': loser.id})


def command_prefix(bot, message):
    # We do not want to make a query for every message that is sent
    # So assume it's in cache, or it doesn't exist
    # If the prefix does exist in the database and isn't in our cache; too bad, something has messed up
    # But it is not worth a query for every single message the bot detects, to fix
    try:
        values = cache['prefixes'].values
        try:
            prefix = [data['prefix'] for data in values if message.server.id == data['server_id']][0]
        except IndexError:
            prefix = None
        return prefix or default_prefix
    except KeyError:
        return default_prefix


async def add_content(table, content, r_filter=None):
    r.set_loop_type("asyncio")
    conn = await r.connect(**db_opts)
    # First we need to make sure that this entry doesn't exist
    # For all rethinkDB cares, multiple entries can exist with the same content
    # For our purposes however, we do not want this
    try:
        if r_filter is not None:
            cursor = await r.table(table).filter(r_filter).run(conn)
            cur_content = await _convert_to_list(cursor)
            if len(cur_content) > 0:
                await conn.close()
                return False
        await r.table(table).insert(content).run(conn)
        await conn.close()
        return True
    except r.ReqlOpFailedError:
        # This means the table does not exist
        await r.table_create(table).run(conn)
        await r.table(table).insert(content).run(conn)
        await conn.close()
        return True


async def remove_content(table, r_filter=None):
    if r_filter is None:
        r_filter = {}
    r.set_loop_type("asyncio")
    conn = await r.connect(**db_opts)
    try:
        result = await r.table(table).filter(r_filter).delete().run(conn)
    except r.ReqlOpFailedError:
        result = {}
        pass
    await conn.close()
    if table == 'prefixes' or table == 'custom_permissions':
        loop.create_task(cache[table].update())
    return result.get('deleted', 0) > 0


async def update_content(table, content, r_filter=None):
    if r_filter is None:
        r_filter = {}
    r.set_loop_type("asyncio")
    conn = await r.connect(**db_opts)
    # This method is only for updating content, so if we find that it doesn't exist, just return false
    try:
        # Update based on the content and filter passed to us
        # rethinkdb allows you to do many many things inside of update
        # This is why we're accepting a variable and using it, whatever it may be, as the query
        result = await r.table(table).filter(r_filter).update(content).run(conn)
    except r.ReqlOpFailedError:
        await conn.close()
        result = {}
    await conn.close()
    if table == 'prefixes' or table == 'custom_permissions':
        loop.create_task(cache[table].update())
    return result.get('replaced', 0) > 0 or result.get('unchanged', 0) > 0


async def replace_content(table, content, r_filter=None):
    # This method is here because .replace and .update can have some different functionalities
    if r_filter is None:
        r_filter = {}
    r.set_loop_type("asyncio")
    conn = await r.connect(**db_opts)
    try:
        result = await r.table(table).filter(r_filter).replace(content).run(conn)
    except r.ReqlOpFailedError:
        await conn.close()
        result = {}
    await conn.close()
    if table == 'prefixes' or table == 'custom_permissions':
        loop.create_task(cache[table].update())
    return result.get('replaced', 0) > 0 or result.get('unchanged', 0) > 0


async def get_content(table: str, r_filter=None):
    if r_filter is None:
        r_filter = {}
    r.set_loop_type("asyncio")
    conn = await r.connect(**db_opts)
    try:
        cursor = await r.table(table).filter(r_filter).run(conn)
        content = await _convert_to_list(cursor)
        if len(content) == 0:
            content = None
    except (IndexError, r.ReqlOpFailedError):
        content = None
    await conn.close()
    if table == 'prefixes' or table == 'custom_permissions':
        loop.create_task(cache[table].update())
    return content


async def _convert_to_list(cursor):
    # This method is here because atm, AsyncioCursor is not iterable
    # For our purposes, we want a list, so we need to do this manually
    cursor_list = []
    while True:
        try:
            val = await cursor.next()
            cursor_list.append(val)
        except r.ReqlCursorEmpty:
            break
    return cursor_list
