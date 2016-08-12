import yaml
import asyncio
import json

loop = asyncio.get_event_loop()

try:
    with open("config.yml", "r") as f:
        global_config = yaml.load(f)
except FileNotFoundError:
    print("You have no config file setup! Please use config.yml.sample to setup a valid config file")
    quit()

botDescription = global_config.get("description")
commandPrefix = global_config.get("command_prefix", "!")
discord_bots_key = global_config.get('discord_bots_key', "")

battleWins = global_config.get("battleWins", [])
defaultStatus = global_config.get("default_status", "")
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


def saveContent(key: str, content):
    try:
        with open("config.json", "r+") as jf:
            data = json.load(jf)
            data[key] = content
            jf.seek(0)
            jf.truncate()
            json.dump(data, jf, indent=4)
    except FileNotFoundError:
        with open("config.json", "w+") as jf:
            json.dump({key: content}, jf, indent=4)


def getContent(key: str):
    try:
        with open("config.json", "r+") as jf:
            return json.load(jf)[key]
    except KeyError:
        return None
    except FileNotFoundError:
        return None
