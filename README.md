# Bonfire

This is for a Discord bot using the discord.py wrapper made for fun, used in a couple of my own servers.

If you'd like to add this bot to one of your own servers, please visit the following URL:
https://discordapp.com/oauth2/authorize?client_id=183748889814237186&scope=bot&permissions=0

To save the data for the bot, rethinkdb is what is used:
https://www.rethinkdb.com/docs/install/

I will not assist with, nor provide instructions on the setup for rethinkdb.

In order to install the requirements for Bonfire you will first need to install python3.5. Once that is installed, run the following (replacing python with the correct executable based on your installation):


```
#NOTE: To use the requirements.txt file, you need to be in the installation directory for this bot.
python -m pip install --upgrade -r requirements.txt
```

The only required file to modify would be the config.yml.sample file. The entries are as follows:

- bot_token: The token that can be retrieved from the [bot's application page](https://discordapp.com/developers/applications/me)
- owner_id: This is your ID, which can be retrieved by right clicking your name in the discord application, when developer mode is on
- description: Self explanatory, the description for the bot
- command_prefix: A list of the prefixes you want the bot to respond to, if none is provided in the config file ! will be used
- default_status: The default status to use when the bot is booted up, which will populate the "game" that the bot is playing
- discord_bots_key: The key for the [bots.discord.pw site](https://bots.discord.pw/#g=1), if you don't have a key just leave it blank, it should fail and log the failure
- carbon_key: The key used for the [carbonitex site](https://www.carbonitex.net/discord/bots)
- twitch_key: The twitch token that is used for the API calls
- youtube_key: The key used for youtube API calls
- osu_key: The key used for Osu API calls
- db_*: This is the information for the rethinkdb database.
