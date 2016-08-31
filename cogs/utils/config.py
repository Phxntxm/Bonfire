import ruamel.yaml as yaml
import asyncio
import rethinkdb as r

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

# This class will hold all our custom permissions
# We don't want to make queries everytime a command is run, to check for custom permissions
# What we'll do here is anytime custom permissions are changed, we'll update this class


class Perms:
    def __init__(self):
        self.custom_perms = {}
        # We need to set the permissions initially when created
        loop.create_task(self.update_perms())

    async def update_perms(self):
        # We need to make sure we're using asyncio
        r.set_loop_type("asyncio")
        # Just connect to the database
        opts = {'host': db_host, 'db': db_name, 'port': db_port, 'ssl': {'ca_certs': db_cert}}
        conn = await r.connect(**opts)
        try:
            cursor = await r.table('custom_permissions').run(conn)
            self.custom_perms = list(cursor.items)[0]
        except (IndexError, r.ReqlOpFailedError):
            return None

    def __repr__(self):
        return self.custom_perms

# Default bot's description
bot_description = global_config.get("description")
# Bot's default prefix for commands
command_prefix = global_config.get("command_prefix", "!")
# The key for bots.discord.pw and carbonitex
discord_bots_key = global_config.get('discord_bots_key', "")
carbon_key = global_config.get('carbon_key', "")
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
# We've set all the options we need to be able to connect
# so create a dictionary that we can use to unload to connect
db_opts = {'host': db_host, 'db': db_name, 'port': db_port, 'ssl': {'ca_certs': db_cert}}
# The perms object we'll update
perms = Perms()

async def save_content(table: str, content):
    # We need to make sure we're using asyncio
    r.set_loop_type("asyncio")
    # Just connect to the database
    conn = await r.connect(**db_opts)
    # We need to make at least one query to ensure the key exists, so attempt to create it as our query
    try:
        await r.table_create(table).run(conn)
    except r.ReqlOpFailedError:
        pass
    # So the table already existed, or it has now been created, we can update the data now
    # Since we're handling everything that is rewritten in the code itself, we just need to delete then insert
    await r.table(table).delete().run(conn)
    await r.table(table).insert(content).run(conn)

    # If we're changing custom_permissions, we want to update our internal object
    if table == "custom_permissions":
        await perms.update_perms()
    await conn.close()


async def get_content(key: str):
    # We need to make sure we're using asyncio
    r.set_loop_type("asyncio")
    # Just connect to the database
    conn = await r.connect(**db_opts)
    # We should only ever get one result, so use it if it exists, otherwise return none
    try:
        cursor = await r.table(key).run(conn)
        items = list(cursor.items)[0]
    except (IndexError, r.ReqlOpFailedError):
        return {}
    # Rethink db stores an internal id per table, delete this and return the rest
    del items['id']
    return items
