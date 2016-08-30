import yaml
import asyncio
import json
import rethinkdb as r

loop = asyncio.get_event_loop()

# Ensure that the required config.yml file actually exists
try:
    with open("config.yml", "r") as f:
        global_config = yaml.load(f)
except FileNotFoundError:
    print("You have no config file setup! Please use config.yml.sample to setup a valid config file")
    quit()

# Default bot's description
botDescription = global_config.get("description")
# Bot's default prefix for commands
commandPrefix = global_config.get("command_prefix", "!")
# The key for bots.discord.pw and carbonitex
discord_bots_key = global_config.get('discord_bots_key', "")
carbon_key = global_config.get('carbon_key', "")
# The invite link for the server made for the bot
dev_server = global_config.get("dev_server", "")

# The variables needed for sharding
shard_count = global_config.get('shard_count', '')
shard_id = global_config.get('shard_id', '')

# A list of all the outputs for the battle command
battleWins = global_config.get("battleWins", [])
# The default status the bot will use
defaultStatus = global_config.get("default_status", "")
# The steam API key
steam_key = global_config.get("steam_key", "")

# The rethinkdb hostname
db_host = global_config.get('db_host', '')
# The rethinkdb database name
db_name = global_config.get('db_name', '')
# The rethinkdb certification
db_cert = global_config.get('db_cert', 'localhost')
# The rethinkdb port
db_port = global_config.get('db_port', 28015)

try:
    botToken = global_config["bot_token"]
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


def save_content(key: str, content):
    try:
        with open("config.json", "r+") as jf:
            data = json.load(jf)
            data[key] = content
            jf.seek(0)
            json.dumps(data)
            jf.truncate()
            json.dump(data, jf, indent=4)
    except FileNotFoundError:
        with open("config.json", "w+") as jf:
            json.dump({key: content}, jf, indent=4)


# Not in use yet
async def _save_content(table: str, content):
    r.set_loop_type("asyncio")
    opts = {'host': db_host, 'db': db_name, 'port': db_port, 'ssl': {'ca_certs': db_cert}}
    conn = await r.connect(**opts)
    # We need to make at least one query to ensure the key exists, so attempt to create it as our query
    try:
        r.table_create(table).run(conn)
    except r.ReqlOpFailedError:
        pass
    # So now either the table was created already, or it has now been created, we can update the code
    # Since we're handling everything that is rewritten in the code itself, we just need to delet then insert
    r.table(table).delete().run(conn)
    r.table(table).insert(content).run(conn)
    await conn.close()


def get_content(key: str):
    try:
        with open("config.json", "r+") as jf:
            return json.load(jf)[key]
    except KeyError:
        return None
    except FileNotFoundError:
        return None
