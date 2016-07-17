import yaml
import pymysql.cursors
import asyncio
import json

loop = asyncio.get_event_loop()

with open("/home/phxntx5/public_html/Bonfire/config.yml", "r") as f:
    global_config = yaml.load(f)

connection = None

db_default = global_config.get("db_default")
db_boops = global_config.get("db_boops")
db_perms = global_config.get("db_perms")

botDescription = global_config.get("description")
commandPrefix = global_config.get("command_prefix")

battleWins = global_config.get("battleWins", [])
defaultStatus = global_config.get("default_status", "")
botToken = global_config.get("bot_token", "")
ownerID = global_config.get("owner_id", "")

modCommands = global_config.get("modCommands", {})
adminCommands = global_config.get("adminCommands", {})
openCommands = global_config.get("openCommands", {})
ownerCommands = global_config.get("ownerCommands", {})
voiceCommands = global_config.get("voiceCommands", {})


def getCursor():
    global connection
    connection = pymysql.connect(host=global_config.get("db_host"), user=global_config.get("db_user"),
                                 password=global_config.get("db_user_pass"), charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)
    return connection.cursor()


def closeConnection():
    connection.commit()
    connection.close()

def saveContent(key: str, content):
    with open("/home/phxntx5/public_html/Bonfire/config.json", "r+") as jf:
        data = json.load(jf)
        data[key] = content
        jf.seek(0)
        json.dump(data, jf, indent=4)
        jf.close()
        
def getContent(key: str):
    try:
        with open("/home/phxntx5/public_html/Bonfire/config.json", "r+") as jf:
            data = json.load(jf)
            jf.close()
            return data[key]
    except KeyError:
        return None
