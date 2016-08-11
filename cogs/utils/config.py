import yaml
import asyncio
import json

loop = asyncio.get_event_loop()
base_path = "/home/phxntx5/public_html/Bonfire"
with open("{}/config.yml".format(base_path), "r") as f:
    global_config = yaml.load(f)

connection = None

botDescription = global_config.get("description")
commandPrefix = global_config.get("command_prefix", "!")
discord_bots_key = global_config.get('discord_bots_key')

battleWins = global_config.get("battleWins", [])
defaultStatus = global_config.get("default_status", "")
botToken = global_config.get("bot_token", "")
owner_ids = global_config.get("owner_id", [])


def saveContent(key: str, content):
    with open("{}/config.json".format(base_path), "r+") as jf:
        data = json.load(jf)
        jf.seek(0)
        data[key] = content
        try:
            json.dumps(data)
        except:
            return False
        else:
            jf.truncate()
            json.dump(data, jf, indent=4)
            return True


def getContent(key: str):
    try:
        with open("{}/config.json".format(base_path), "r+") as jf:
            return json.load(jf)[key]
    except KeyError:
        return None
