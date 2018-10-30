import yaml
import asyncio

loop = asyncio.get_event_loop()
global_config = {}

# Ensure that the required config.yml file actually exists
try:
    with open("config.yml", "r") as f:
        global_config = yaml.load(f)
        global_config = {k: v for k, v in global_config.items() if v}
except FileNotFoundError:
    print("You have no config file setup! Please use config.yml.sample to setup a valid config file")
    quit()

try:
    bot_token = global_config["bot_token"]
except KeyError:
    print("You have no bot_token saved, this is a requirement for running a bot.")
    print("Please use config.yml.sample to setup a valid config file")
    quit()

# Default bot's description
bot_description = global_config.get("description")
# Bot's default prefix for commands
default_prefix = global_config.get("command_prefix", "!")
# The key for bot sites (discord bots and discordbots are TWO DIFFERENT THINGS)
discord_bots_key = global_config.get('discord_bots_key', "")
discordbots_key = global_config.get('discordbots_key', "")
carbon_key = global_config.get('carbon_key', "")
# The client ID for twitch requests
twitch_key = global_config.get('twitch_key', "")
# The key for youtube API calls
youtube_key = global_config.get("youtube_key", "")
# The key for Osu API calls
osu_key = global_config.get('osu_key', '')
# The key for League of Legends API calls
lol_key = global_config.get('lol_key', '')
# The keys needed for deviant art calls
# The invite link for the server made for the bot
dev_server = global_config.get("dev_server", "")
# The User-Agent that we'll use for most requests
user_agent = global_config.get('user_agent', None)
# The URL to proxy youtube_dl's requests through
ytdl_proxy = global_config.get('youtube_dl_proxy', None)
# The patreon key, as well as the patreon ID to use
patreon_key = global_config.get('patreon_key', None)
patreon_id = global_config.get('patreon_id', None)
patreon_link = global_config.get('patreon_link', None)
# The client ID/secret for spotify
spotify_id = global_config.get("spotify_id", None)
spotify_secret = global_config.get("spotify_secret", None)

# The extensions to load
extensions = [
    'cogs.interaction',
    'cogs.misc',
    'cogs.mod',
    'cogs.admin',
    'cogs.images',
    'cogs.birthday',
    'cogs.owner',
    'cogs.stats',
    'cogs.picarto',
    'cogs.overwatch',
    'cogs.links',
    'cogs.roles',
    'cogs.tictactoe',
    'cogs.hangman',
    'cogs.events',
    'cogs.raffle',
    'cogs.blackjack',
    'cogs.osu',
    'cogs.tags',
    'cogs.roulette',
    'cogs.spotify',
    'cogs.polls'
]


# The default status the bot will use
default_status = global_config.get("default_status", None)
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


def command_prefix(bot, message):
    if not message.guild:
        return default_prefix
    return bot.db.load('server_settings', key=message.guild.id, pluck='prefix') or default_prefix
