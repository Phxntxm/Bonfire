import ruamel.yaml as yaml
import asyncio
import rethinkdb as r
import pendulum

loop = asyncio.get_event_loop()

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
        self.values = await _get_content(self.key)
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
shard_count = global_config.get('shard_count', '')
shard_id = global_config.get('shard_id', '')

# A list of all the outputs for the battle command
battle_wins = global_config.get("battleWins", [])
# The default status the bot will use
default_status = global_config.get("default_status", "")
# The steam API key
steam_key = global_config.get("steam_key", "")

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

possible_keys = ['prefixes', 'battling', 'battle_records', 'boops', 'server_alerts', 'user_notifications',
                 'nsfw_channels', 'custom_permissions', 'rules', 'overwatch', 'picarto', 'twitch', 'strawpolls', 'tags',
                 'tictactoe', 'bot_data', 'command_manage']

# This will be a dictionary that holds the cache object, based on the key that is saved
cache = {}

sharded_data = {}

# Populate cache with each object
for k in possible_keys:
    cache[k] = Cache(k)


def command_prefix(bot, message):
    # We do not want to make a query for every message that is sent
    # So assume it's in cache, or it doesn't exist
    # If the prefix does exist in the database and isn't in our cache; too bad, something has messed up
    # But it is not worth a query for every single message the bot detects, to fix
    try:
        prefix = cache['prefixes'].values.get(message.server.id)
        return prefix or default_prefix
    except KeyError:
        return default_prefix

async def add_content(table, filter, content):
        r.set_loop_type("asyncio")
        conn = await r.connect(**db_opts)
        # First we need to make sure that this entry doesn't exist
        # For all rethinkDB cares, multiple entries can exist with the same content
        # For our purposes however, we do not want this
        try:
                cursor = await r.table(table).filter(filter).run(conn)
                if len(list(cursor)) > 0:
                        await conn.close()
                        return False
                else:
                        await r.table(table).insert(content).run(conn)
                        await conn.close()
                        return True
        except r.ReqlOpFailedError:
                # This means the table does not exist
                await r.create_table(table).run(conn)
                await r.table(table).filter(filter).insert(content).run(conn)
                await con.close()
                return False

async def update_content(table, filter, content):
        r.set_loop_type("asyncio")
        conn = await r.connect(**db_opts)
        # This method is only for updating content, so if we find that it doesn't exist, just return false
        try:
                # Update based on the content and filter passed to us
                # rethinkdb allows you to do many many things inside of update
                # This is why we're accepting a variable and using it, whatever it may be, as the query
                # Will take some testing, but I might not even need the add_content method above
                await r.table(table).filter(filter).update(content).run(conn)
        except r.ReqlOpFailedError:
                await conn.close()
                return False
        await conn.close()
        return True

async def get_content(key: str, filter):
        r.set_loop_type("asyncio")
        conn = await r.connect(**db_opts)
        try:
                cursor = await r.table(key).filter(filter).run(conn)
                content = list(cursor.items)[0]
                del content['id']
        except (IndexError, r.ReqlOpFailedError):
                content = None
        await conn.close()
        return content

