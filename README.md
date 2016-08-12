# Bonfire

This is for a Discord bot using the discord.py wrapper made for fun, used in a couple of Phxntxm's own servers.

If you'd like to add this bot to one of your own servers, please visit the following URL:
https://discordapp.com/oauth2/authorize?client_id=183748889814237186&scope=bot&permissions=0

This requires the discord.py library, as well as all of it's dependencies.
https://github.com/Rapptz/discord.py

I also use the pendulum library, which can be installed using pip.
```
pip install pendulum
```

The only required file to modify would be the config.yml.sample file. The entries are as follows:

- bot_token: The token that can be retrieved from the [bot's application page](https://discordapp.com/developers/applications/me)
- owner_id: This is your ID, which can be retrieved by right clicking your name in the discord application, when developer mode is on
- description: Self explanotory, the description for the bot
- command_prefix: A list of the prefixes you want the bot to respond to, if none is provided in the config file ! will be used
- default_stats: The default status to use when the bot is booted up, which will populate the "game" that the bot is playing
- battleWins: A list of random "outcomes" to the battle command, needs to be in the exact format provided in the sample file. `{0}` is the winner, `{1}` is the loser
- discord_bots_key: The key for the [bots.discord.pw site](https://bots.discord.pw/#g=1), if you don't have a key just leave it blank, it should fail and log the failure
