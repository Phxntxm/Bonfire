import yaml
import asyncio
import json

loop = asyncio.get_event_loop()

try:
    with open("config.yml", "r") as f:
        global_config = yaml.load(f)
except FileNotFoundError:
    print("You have no config file setup! Please use config.yml.sample to setup a valid config file.")
    quit()

try:
    with open("phrases.yml", "r") as f:
        global_phrases = yaml.load(f)
except FileNotFoundError:
    print("All phrases are missing!  I can't exactly talk to the members without these, can I?")
    quit()

connection = None

botName = global_config.get("bot_name", "Bonfire")
botDescription = global_config.get("description", "")
commandPrefix = global_config.get("command_prefix", "!")
discord_bots_key = global_config.get('discord_bots_key', "")

battleWins = global_config.get("battleWins", [])
defaultStatus = global_config.get("default_status", "")
try:
    botToken = global_config["bot_token"]
except KeyError:
    print("You have no bot_token saved, this is a requirement for running a bot.")
    botToken = None
    
try:
    owner_ids = global_config["owner_id"]
except KeyError:
    print("You have no owner_id saved! You're not going to be able to run certain commands without this.")
    owner_ids = None

if not (botToken and owner_ids):
    print("Please use config.yml.sample to setup a valid config file.")
    quit()


def saveContent(key: str, content):
    with open("config.json", "a+") as jf:
        try:
            data = json.load(jf)
        except json.JSONDecodeError:
            data = {}
        data[key] = content
        jf.seek(0)
        jf.truncate()
        json.dump(data, jf, indent=4)


def getContent(key: str):
    try:
        with open("config.json", "r+") as jf:
            return json.load(jf)[key]
    except KeyError:
        return None

def getPhrase(key: str):
    return global_phrases.get(key, key)
