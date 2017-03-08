import ruamel.yaml as yaml
import asyncio
import rethinkdb as r
import pendulum

loop = asyncio.get_event_loop()
global_config = {}

# Ensure that the required config.yml file actually exists
try:
    with open("config.yml", "r") as f:
        global_config = yaml.safe_load(f)
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
# The steam API key
steam_key = global_config.get("steam_key", "")
# The key for youtube API calls
youtube_key = global_config.get("youtube_key", "")
# The key for Osu API calls
osu_key = global_config.get('osu_key', '')
# The key for League of Legends API calls
lol_key = global_config.get('lol_key', '')
# The keys needed for deviant art calls
da_id = global_config.get("da_id", "")
da_secret = global_config.get("da_secret", "")
# The invite link for the server made for the bot
dev_server = global_config.get("dev_server", "")
# The User-Agent that we'll use for most requests
user_agent = global_config.get('user_agent', "")
# The extensions to load
extensions = global_config.get('extensions', [])

# The default status the bot will use
default_status = global_config.get("default_status", None)
# The URL that will be used to link to for the help command
help_url = global_config.get("help_url", "")
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
cache['server_settings'] = Cache('server_settings')

async def update_cache():
    for value in cache.values():
        await value.update()


def command_prefix(bot, message):
    # We do not want to make a query for every message that is sent
    # So assume it's in cache, or it doesn't exist
    # If the prefix does exist in the database and isn't in our cache; too bad, something has messed up
    # But it is not worth a query for every single message the bot detects, to fix
    try:
        prefixes = cache['server_settings'].values
        prefix = [x for x in prefixes if x['server_id'] == str(message.guild.id)][0]['prefix']
        return prefix or default_prefix
    except (KeyError, TypeError, IndexError, AttributeError, KeyError):
        return default_prefix


async def add_content(table, content):
    r.set_loop_type("asyncio")
    conn = await r.connect(**db_opts)
    # First we need to make sure that this entry doesn't exist
    # For all rethinkDB cares, multiple entries can exist with the same content
    # For our purposes however, we do not want this
    try:
        result = await r.table(table).insert(content).run(conn)
        await conn.close()
    except r.ReqlOpFailedError:
        # This means the table does not exist
        await r.table_create(table).run(conn)
        await r.table(table).insert(content).run(conn)
        await conn.close()
        result = {}
    return result.get('inserted', 0) > 0


async def remove_content(table, key):
    r.set_loop_type("asyncio")
    conn = await r.connect(**db_opts)
    try:
        result = await r.table(table).get(key).delete().run(conn)
    except r.ReqlOpFailedError:
        result = {}
        pass
    await conn.close()
    if table == 'prefixes' or table == 'server_settings':
        loop.create_task(cache[table].update())
    return result.get('deleted', 0) > 0


async def update_content(table, content, key):
    r.set_loop_type("asyncio")
    conn = await r.connect(**db_opts)
    # This method is only for updating content, so if we find that it doesn't exist, just return false
    try:
        # Update based on the content and filter passed to us
        # rethinkdb allows you to do many many things inside of update
        # This is why we're accepting a variable and using it, whatever it may be, as the query
        result = await r.table(table).get(key).update(content).run(conn)
    except r.ReqlOpFailedError:
        await conn.close()
        result = {}
    await conn.close()
    if table == 'prefixes' or table == 'server_settings':
        loop.create_task(cache[table].update())
    return result.get('replaced', 0) > 0 or result.get('unchanged', 0) > 0


async def replace_content(table, content, key):
    # This method is here because .replace and .update can have some different functionalities
    r.set_loop_type("asyncio")
    conn = await r.connect(**db_opts)
    try:
        result = await r.table(table).get(key).replace(content).run(conn)
    except r.ReqlOpFailedError:
        await conn.close()
        result = {}
    await conn.close()
    if table == 'prefixes' or table == 'server_settings':
        loop.create_task(cache[table].update())
    return result.get('replaced', 0) > 0 or result.get('unchanged', 0) > 0


async def get_content(table, key=None):
    r.set_loop_type("asyncio")
    conn = await r.connect(**db_opts)

    try:
        if key:
            cursor = await r.table(table).get(key).run(conn)
        else:
            cursor = await r.table(table).run(conn)
        if cursor is None:
            content = None
        elif type(cursor) is not dict:
            content = await _convert_to_list(cursor)
            if len(content) == 0:
                content = None
        else:
            content = cursor
    except (IndexError, r.ReqlOpFailedError):
        content = None
    await conn.close()
    if table == 'prefixes' or table == 'server_settings':
        loop.create_task(cache[table].update())
    return content

async def filter_content(table: str, r_filter):
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
    if table == 'prefixes' or table == 'server_settings':
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
