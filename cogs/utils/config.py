import yaml
import asyncio
import json

loop = asyncio.get_event_loop()

with open("/home/phxntx5/public_html/Bonfire/config.yml", "r") as f:
    global_config = yaml.load(f)

connection = None

botDescription = global_config.get("description")
commandPrefix = global_config.get("command_prefix")

battleWins = global_config.get("battleWins", [])
defaultStatus = global_config.get("default_status", "")
botToken = global_config.get("bot_token", "")
ownerID = global_config.get("owner_id", "")


def saveContent(key: str, content):
    with open("/home/phxntx5/public_html/Bonfire/config.json", "r+") as jf:
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
        with open("/home/phxntx5/public_html/Bonfire/config.json", "r+") as jf:
            return json.load(jf)[key]
    except KeyError:
        return None
