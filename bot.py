#!/usr/local/bin/python3.5

import asyncio
import discord
from discord.ext import commands
import sys
import os
import random
import subprocess
import urllib.request
import urllib.parse
import json
import re
import pymysql.cursors
import yaml
import playlist
from threading import Timer

with open("/home/phxntx5/public_html/bot/config.yml","r") as f:
    global_config = yaml.load(f)

botDescription = global_config.get("description")
commandPrefix = global_config.get("command_prefix")

#Custom predicates
def isOwner():
    def predicate(ctx):
        return ctx.message.author.id==ownerID
    return commands.check(predicate)
def isMod():
    def predicate(ctx):
        return ctx.message.author.top_role.permissions.kick_members
    return commands.check(predicate)
def isAdmin():
    def predicate(ctx):
        return ctx.message.author.top_role.permissions.manage_server
    return commands.check(predicate)
def isPM():
    def predicate(ctx):
        return ctx.message.channel.is_private
    return commands.check(predicate)
def battled():
    def predicate(ctx):
        return ctx.message.author==battleP2
    return commands.check(predicate)
        
bot = commands.Bot(command_prefix=commandPrefix,description=botDescription)
music = playlist.Music(bot)
bot.add_cog(music)

#Turn battling off, reset users
def battlingOff():
    global battleP1
    global battleP2
    global battling
    battling = False
    battleP1 = ""
    battleP2 = ""

#Bot event overrides
@bot.event
async def on_ready():
    #Change the status upon connection to the default status
    game = discord.Game(name=defaultStatus,type=0)
    await bot.change_status(game)
    cursor = connection.cursor()
    
    '''success = checkSetup(cursor)
    if success=="Error: default_db":
        await bot-send_message(determineId(ownerID),("The bot ran into an error while checking the database information."
        "Please double check the config.yml file, make sure the database is created, and the user has access to the database"))'''
    
    cursor.execute('use {0}'.format(db_default))
    cursor.execute('select channel_id from restart_server where id=1')
    result = cursor.fetchone()['channel_id']
    if int(result)!=0:
        await bot.send_message(determineId(result),"I have just finished restarting!")
        cursor.execute('update restart_server set channel_id=0 where id=1')
        connection.commit()

@bot.event
async def on_member_join(member):
    await bot.say("Welcome to the '{0.server.name}' server {0.mention}!".format(member))

@bot.event
async def on_member_remove(member):
    await bot.say("{0} has left the server, I hope it wasn't because of something I said :c".format(member))

#Bot commands
@bot.command()
async def joke():
    try:
        fortuneCommand = "/usr/bin/fortune riddles"
        fortune = subprocess.check_output(fortuneCommand.split()).decode("utf-8")
        await bot.say(fortune)
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

@bot.command(pass_context=True)
@isOwner()
async def restart(ctx):
    try:
        cursor = connection.cursor()
        cursor.execute('use {0}'.format(db_default))
        sql = "update restart_server set channel_id={0} where id=1".format(ctx.message.channel.id)
        cursor.execute(sql)
        connection.commit()
        await bot.say("Restarting; see you in the next life {0}!".format(ctx.message.author.mention))
        python = sys.executable
        os.execl(python, python, *sys.argv)
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

@bot.command(pass_context=True)
@isOwner()
async def py(ctx):
    try:
        match_single = getter.findall(ctx.message.content)
        match_multi = multi.findall(ctx.message.content)
        if not match_single and not match_multi:
            return
        else:
            if not match_multi:
                result = eval(match_single[0])
                await bot.say("```{0}```".format(result))
            else:
                def r(v):
                    loop.create_task(bot.say("```{0}```".format(v)))
                exec(match_multi[0])
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

@bot.command(pass_context=True)
@isOwner()
async def shutdown(ctx):
    try:
        fmt = 'Shutting down, I will miss you {0.author.name}'
        await bot.say(fmt.format(ctx.message))
        await bot.logout()
        await bot.close()
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

@bot.command()
@isOwner()
async def avatar(content):
    try:
        file = '/home/phxntx5/public_html/bot/images/' + content
        with open(file, 'rb') as fp:
            await bot.edit_profile(avatar=fp.read())
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

@bot.command()
@isOwner()
async def name(newNick):
    try:
        await bot.edit_profile(username=newNick)
        await bot.say('Changed username to ' + newNick)
        # Restart the bot after this, as profile changes are not immediate
        python = sys.executable
        os.execl(python, python, *sys.argv)
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

@bot.command(pass_context=True,no_pm=True)
@isOwner()
async def leave(ctx):
    try:
        await bot.say('Why must I leave? Hopefully I can come back :c')
        await bot.leave_server(ctx.message.server)
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

@bot.command()
@isMod()
async def status(*stat : str):
    try:
        newStatus = ' '.join(stat)
        game = discord.Game(name=newStatus, type=0)
        await bot.change_status(game)
        await bot.say("Just changed my status to '{0}'!".format(newStatus))
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

@bot.command(pass_context=True)
@isMod()
async def say(ctx,*msg : str):
    try:
        msg = ' '.join(msg)
        await bot.say(msg)
        await bot.delete_message(ctx.message)
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))
        
@bot.command()
async def urban(*msg : str):
    try:
        term = '+'.join(msg)
        url = "http://api.urbandictionary.com/v0/define?term={}".format(term)
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode('utf-8'))
        if len(data['list'])==0:
            await bot.say("No result with that term!")
        else:
            await bot.say(data['list'][0]['definition'])
    except discord.HTTPException:
        await bot.say('```Error: Defintion is too long for me to send```')
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))
    
@bot.command(pass_context=True)
async def derpi(ctx,*search : str):
    try:
        if len(search) > 0:
            url = 'https://derpibooru.org/search.json?q='
            query = '+'.join(search)
            url += query
            if ctx.message.channel.id in nsfwChannels:
                url+=",+explicit&filter_id=95938"
            # url should now be in the form of url?q=search+terms
            # Next part processes the json format, and saves the data in useful lists/dictionaries
            response = urllib.request.urlopen(url)
            data = json.loads(response.read().decode('utf-8'))
            results = data['search']

            if len(results) > 0:
                index = random.randint(0, len(results) - 1)
                randImageUrl = results[index].get('representations').get('full')[2:]
                randImageUrl = 'http://' + randImageUrl
                imageLink = randImageUrl.strip()
            else:
                await bot.say("No results with that search term, {0}!".format(ctx.message.author.mention))
                return
        else:
            with urllib.request.urlopen('https://derpibooru.org/images/random') as response:
                imageLink = response.geturl()
        url = 'https://shpro.link/redirect.php/'
        data = urllib.parse.urlencode({'link': imageLink}).encode('ascii')
        response = urllib.request.urlopen(url, data).read().decode('utf-8')
        await bot.say(response)
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

@bot.command(pass_context=True)
async def roll(ctx):
    try:
        num = random.randint(1, 6)
        fmt = '{0.author.name} has rolled a die and got the number {1}!'
        await bot.say(fmt.format(ctx.message, num))
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

@bot.command(no_pm=True)
@battled()
async def accept():
    try:
        if not battling:
            return
        num = random.randint(1, 100)
        fmt = battleWins[random.randint(0, len(battleWins) - 1)]
        if num <= 50:
            await bot.say(fmt.format(battleP1.mention, battleP2.mention))
            updateBattleRecords(battleP1,battleP2)
        elif num > 50:
            await bot.say(fmt.format(battleP2.mention, battleP1.mention))
            updateBattleRecords(battleP2,battleP1)
        battlingOff()
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

@bot.command(no_pm=True)
@battled()
async def decline():
    try:
        if not battling:
            return
        await bot.say("{0} has chickened out! {1} wins by default!".format(battleP2.mention, battleP1.mention))
        updateBattleRecords(battleP1,battleP2)
        battlingOff()
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

@bot.command(pass_context=True)
async def commands(ctx):
    try:
        fmt = 'Hello {0.author.name}!\n\nThis is {1.user.name}! '
        fmt += 'Here is a list of commands that you have access to '
        fmt += '(please note that this only includes the commands that you have access to):'
        await bot.whisper(fmt.format(ctx.message, bot))
        
        fmt2 = 'I have just sent you a private message, containing all the commands you have access to {0.author.mention}!'
        ocmds = 'Commands for everyone: ```'
        for com, act in openCommands.items():
            ocmds += commandPrefix + com + ": " + act + "\n\n"
        ocmds += '```'
        await bot.whisper(ocmds)
        vcmds = 'Voice Commands: ```'
        for com, act in voiceCommands.items():
            vcmds += commandPrefix + com + ": " + act + "\n\n"
        vcmds += '```'
        await bot.whisper(vcmds)
        if ctx.message.author.top_role.permissions.kick_members:
            if len(modCommands) > 0:
                mcmds = 'Moderator Commands: ```'
                for com, act in modCommands.items():
                    mcmds += commandPrefix + com + ": " + act + "\n\n"
                mcmds += '```'
                await bot.whisper(mcmds)
        if ctx.message.author.top_role.permissions.manage_server:
            if len(adminCommands) > 0:
                acmds = 'Admin Commands: ```'
                for com, act in adminCommands.items():
                    acmds += commandPrefix + com + ": " + act + "\n\n"
                acmds += '```'
                await bot.whisper(acmds)
        if ctx.message.author.id == ownerID:
            if len(ownerCommands) > 0:
                owncmds = 'Owner Commands: ```'
                for com, act in ownerCommands.items():
                    owncmds += commandPrefix + com + ": " + act + "\n\n"
                owncmds += '```'
                await bot.whisper(owncmds)
        await bot.say(fmt2.format(ctx.message))
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

@bot.command(pass_context=True,no_pm=True)
async def battle(ctx):
    try:
        global battleP1
        global battleP2
        global battling
        if battling:
            return
        if len(ctx.message.mentions) == 0:
            await bot.say("You must mention someone in the room " + ctx.message.author.mention + "!")
            return
        if len(ctx.message.mentions) > 1:
            await bot.say("You cannot battle more than one person at once!")
            return
        player2 = ctx.message.mentions[0]
        if ctx.message.author.id == player2.id:
            await bot.say("Why would you want to battle yourself? Suicide is not the answer")
            return
        if bot.user.id == player2.id:
            await bot.say("I always win, don't even try it.")
            return
        fmt = "{0.mention} has challenged you to a battle {1.mention}\n!accept or !decline"
        battleP1 = ctx.message.author
        battleP2 = player2
        await bot.say(fmt.format(ctx.message.author, player2))
        t = Timer(180, battlingOff)
        t.start()
        battling = True
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

@bot.command(pass_context=True,no_pm=True)
async def boop(ctx):
    try:
        if len(ctx.message.mentions) == 0:
            await bot.say("You must mention someone in the room " + ctx.message.author.mention + "!")
            return
        if len(ctx.message.mentions) > 1:
            await bot.say("You cannot boop more than one person at once!")
            return
        boopee = ctx.message.mentions[0]
        booper = ctx.message.author
        if boopee.id == booper.id:
            await bot.say("You can't boop yourself! Silly...")
            return
        if boopee.id == bot.user.id:
            await bot.say("Why the heck are you booping me? Get away from me >:c")
            return

        cursor = connection.cursor()
        cursor.execute('use {0}'.format(db_boops))
        sql = "show tables like '" + str(booper.id) + "'"
        cursor.execute(sql)
        result = cursor.fetchone()
        amount = 1
        # Booper's table exists, continue
        if result is not None:
            sql = "select `amount` from `" + booper.id + "` where id='" + str(boopee.id) + "'"
            cursor.execute(sql)
            result = cursor.fetchone()
            # Boopee's entry exists, continue
            if result is not None:
                amount = result.get('amount') + 1
                sql = "update `" + str(booper.id) + "` set amount = " + str(amount) + " where id=" + str(
                    boopee.id)
                cursor.execute(sql)
            # Boopee does not exist, need to create the field for it
            else:
                sql = "insert into `" + str(booper.id) + "` (id,amount) values ('" + str(boopee.id) + "',1)"
                cursor.execute(sql)
        # Booper's table does not exist, need to create the table
        else:
            sql = "create table `" + str(
                booper.id) + "` (`id` varchar(255) not null,`amount` int(11) not null,primary key (`id`)) engine=InnoDB default charset=utf8 collate=utf8_bin"
            cursor.execute(sql)
            sql = "insert into `" + str(booper.id) + "` (id,amount) values ('" + str(boopee.id) + "',1)"
            cursor.execute(sql)
        fmt = "{0.mention} has just booped you {1.mention}! That's {2} times now!"
        await bot.say(fmt.format(booper, boopee, amount))
        connection.commit()
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

@bot.command(pass_context=True,no_pm=True)
async def mostboops(ctx):
    try:
        cursor = connection.cursor()
        cursor.execute('use {0}'.format(db_boops))
        sql = "select id,amount from `{0}` where amount=(select MAX(amount) from `{0}`)".format(ctx.message.author.id)
        cursor.execute(sql)
        result = cursor.fetchone()
        member = determineId(result.get('id'))
        await bot.say("{0} you have booped {1} the most amount of times, coming in at {2} times".format(ctx.message.author.mention,member.mention,result.get('amount')))
        connection.commit()
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

@bot.command(pass_context=True,no_pm=True)
async def mostwins(ctx):
    try:
        members = ctx.message.server.members
        cursor = connection.cursor()
        cursor.execute('use {0}'.format(db_default))
        sql = "select * from battle_records"
        cursor.execute(sql)
        result = cursor.fetchall()
        count = 0
        fmt = []
        if result is not None:
            for r in result:
                member = determineId(r['id'])
                if member in members:
                    record = r['record']

                    winAmt = int(record.split('-')[0])
                    loseAmt = int(record.split('-')[1])
                    percentage = winAmt / ( winAmt + loseAmt )

                    position = count

                    indexPercentage = 0
                    if count > 0:
                        indexRecord = re.search('\d+-\d+',fmt[position-1]).group(0)
                        indexWin = int(indexRecord.split('-')[0])
                        indexLose = int(indexRecord.split('-')[1])
                        indexPercentage = indexWin / (indexWin + indexLose)
                    while position > 0 and indexPercentage < percentage:
                        position -= 1
                        indexRecord = re.search('\d+-\d+',fmt[position-1]).group(0)
                        indexWin = int(indexRecord.split('-')[0])
                        indexLose = int(indexRecord.split('-')[1])
                        indexPercentage = indexWin / (indexWin + indexLose)
                    fmt.insert(position,"{0} has a battling record of {1}".format(member.name,record))
                    count+=1
            for index in range(0,len(fmt)):
                fmt[index] = "{0}) {1}".format(index+1,fmt[index])
        connection.commit()
        if len(fmt) == 0:
            await bot.say("```No battling records found from any members in this server```")
            return
        await bot.say("```{}```".format("\n".join(fmt)))
    except Exception as e:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.say(fmt.format(type(e).__name__, e))

def determineId(ID):
    if type(ID) is int:
        ID=str(ID)
    member = discord.utils.find(lambda m: m.id == ID, bot.get_all_members())
    if member is not None:
        return member
    msg = discord.utils.find(lambda m: m.id == ID, bot.messages)
    if msg is not None:
        return msg
    server = discord.utils.find(lambda s: s.id == ID, bot.servers)
    if server is not None:
        return server
    channel = discord.utils.find(lambda c: c.id == ID, bot.get_all_channels())
    if channel is not None:
        return channel

def updateBattleRecords(winner,loser):
    cursor = connection.cursor()
    cursor.execute('use {0}'.format(db_default))
    
    #Update winners records
    sql = "select record from battle_records where id={0}".format(winner.id)
    cursor.execute(sql)
    result = cursor.fetchone()
    if result is not None:
        result = result['record'].split('-')
        result[0] = str(int(result[0])+1)
        sql = "update battle_records set record ='{0}' where id='{1}'".format("-".join(result),winner.id)
        cursor.execute(sql)
    else:
        sql = "insert into battle_records (id,record) values ('{0}','1-0')".format(winner.id)
        cursor.execute(sql)
    
    connection.commit()
        
    #Update losers records
    sql = "select record from battle_records where id={0}".format(loser.id)
    cursor.execute(sql)
    result = cursor.fetchone()
    if result is not None:
        result = result['record'].split('-')
        result[1] = str(int(result[1])+1)
        sql = "update battle_records set record ='{0}' where id='{1}'".format('-'.join(result),loser.id)
        cursor.execute(sql)
    else:
        sql = "insert into battle_records (id,record) values ('{0}','0-1')".format(loser.id)
        cursor.execute(sql)
    
    connection.commit()

def checkSetup(cursor):
    try:
        cursor.execute('use {}'.format(db_default))
    except pymysql.OperationalError:
        return "Error: default_db"
    else:
        try:
            cursor.execute('describe battle_records')
        except pymysql.ProgrammingError:
            #battle_records does not exist, create it
            sql = "create table `battle_records` (`id` varchar(32) not null,`record` varchar(32) not null,primary key (`id`)) engine=InnoDB default charset=utf8 collate=utf8_bin"
            cursor.execute(sql)
            connection.commit()
        try:
            cursor.execute('describe restart_server')
        except pymysql.ProgrammingError:
            #restart_server does not exist, create it
            sql = "create table `restart_server` (`id` int(11) not null auto_increment,`channel_id` varchar(32) not null,primary key (`id`)) engine=InnoDB default charset=utf8 collate=utf8_bin;"
            cursor.execute(sql)
            connection.commit()
            sql = "insert into restart_server (id,channel_id) values (1,'0')"
            cursor.execute(sql)
            connection.commit()
    try:
        cursor.execute('use {}'.format(db_boops))
    except pymysql.OperationalError:
        return "Error: boop_db"
    
db_default = global_config.get("db_default")
db_boops = global_config.get("db_boops")
nsfwChannels = global_config.get("nsfw_channel")
connection = pymysql.connect(host=global_config.get("db_host"), user=global_config.get("db_user"),
password=global_config.get("db_user_pass"),charset='utf8mb4',cursorclass=pymysql.cursors.DictCursor)

battling=False
battleP1=None
battleP2=None

battleWins = global_config.get("battleWins",[])
defaultStatus = global_config.get("default_status","")
botToken = global_config.get("bot_token","")
ownerID = global_config.get("owner_id","")

modCommands = global_config.get("modCommands",{})
adminCommands = global_config.get("adminCommands",{})
openCommands = global_config.get("openCommands",{})
ownerCommands = global_config.get("ownerCommands",{})
voiceCommands = global_config.get("voiceCommands",{})

getter = re.compile(r'`(?!`)(.*?)`')
multi = re.compile(r'```(.*?)```',re.DOTALL)
loop = asyncio.get_event_loop()
try:
    bot.run(botToken)
except:
    quit()