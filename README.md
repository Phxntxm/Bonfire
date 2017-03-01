# Bonfire

This is for a Discord bot using the discord.py wrapper made for fun, used in a couple of my own servers.

If you'd like to add this bot to one of your own servers, please visit the following URL:
https://discordapp.com/oauth2/authorize?client_id=183748889814237186&scope=bot&permissions=0

This requires the discord.py library, as well as all of its dependencies.
https://github.com/Rapptz/discord.py

To save the data for the bot, rethinkdb is what is used:
https://www.rethinkdb.com/docs/install/

I also use a few libraries that aren't included by default, which can be installed using pip.
```
python3.5 -m pip install discord.py[voice] lxml fuzzywuzzy youtube_dl rethinkdb ruamel.yaml pendulum Pillow==3.4.1 readline
# Or on windows
py -3 -m pip install discord.py[voice] lxml fuzzywuzzy youtube_dl rethinkdb ruamel.yaml pendulum Pillow==3.4.1 readline
```

The joke command requires the fortune-mod package, which should be installable on Linux distros, including Debian and Ubuntu.
```
sudo apt install fortune-mod
```
If you're on Windows, you might want to consider [this guide](http://superuser.com/questions/683162/bsd-fortune-for-windows-command-prompt-or-dos), but you're on your own.


Note: ATM of writing this, Pillow 3.4.2 (the stable version...good job Pillow?) is broken, do not use pip's default to install this. This is why we're using Pillow==3.4.1 above, and not just Pillow

The only required file to modify would be the config.yml.sample file. The entries are as follows:

- bot_token: The token that can be retrieved from the [bot's application page](https://discordapp.com/developers/applications/me)
- owner_id: This is your ID, which can be retrieved by right clicking your name in the discord application, when developer mode is on
- description: Self explanotory, the description for the bot
- command_prefix: A list of the prefixes you want the bot to respond to, if none is provided in the config file ! will be used
- default_status: The default status to use when the bot is booted up, which will populate the "game" that the bot is playing
- discord_bots_key: The key for the [bots.discord.pw site](https://bots.discord.pw/#g=1), if you don't have a key just leave it blank, it should fail and log the failure
- carbon_key: The key used for the [carbonitex site](https://www.carbonitex.net/discord/bots)
- twitch_key: The twitch token that is used for the API calls
- youtube_key: The key used for youtube API calls
- osu_key: The key used for Osu API calls
- da_id: The deviant art ID retrieved when registering an application, needed for API calls.
- da_secret: The deviant art Secret, given with the da_id above
- shard_count: This is the number of shards the bot is split over. 1 needs to be used if the bot is not being sharded
- shard_id: This will be the ID of the shard in particular, 0 if sharding is not used
- extensions: This is a list of the extensions loaded into the bot (check the cogs folder for the extensions available). The disabled playlist is a special entry....read that file for what its purpose is....most likely you will not need it. Entries in this list need to be separated by ", " like in the example.
- db_*: This is the information for the rethinkdb database. The cert is the certificate used for driver connections

