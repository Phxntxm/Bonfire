from discord.ext import commands
from .utils import config
from .utils import checks

class Tags:
    """This class contains all the commands for custom tags"""

    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(pass_context=True)
    @checks.customPermsOrRole("send_messages")
    async def tags(self, ctx):
        """Prints all the custom tags that this server currently has"""
        tags = config.getContent('tags')
        fmt = "\n".join("{}".format(tag['tag']) for tag in tags if tag['server_id']==ctx.message.server.id)
        await self.bot.say('```{}```'.format(fmt))

    @commands.group(pass_context=True, invoke_without_command=True, no_pm=True)
    @checks.customPermsOrRole("send_messages")
    async def tag(self, ctx, *, tag: str):
        """This can be used to call custom tags
         The format to call a custom tag is !tag <tag>"""
        tags = config.getContent('tags')
        result = [t for t in tags if t['tag'] == tag and t['server_id'] == ctx.message.server.id]
        if len(result) == 0:
            await self.bot.say('That tag does not exist!')
            return
        await self.bot.say("{}".format(result[0]['result']))

    @tag.command(name='add', aliases=['create', 'start'], pass_context=True, no_pm=True)
    @checks.customPermsOrRole("kick_members")
    async def add_tag(self, ctx, *, result: str):
        """Use this to add a new tag that can be used in this server
        Format to add a tag is !tag add <tag> - <result>"""
        tag = result[0:result.find('-')].strip()
        tag_result = result[result.find('-') + 2:].strip()
        if len(tag) == 0 or len(result) == 0:
            await self.bot.say("Please provide the format for the tag in: !tag add <tag> - <result>")
            return
        tags = config.getContent('tags')
        for t in tags:
            if t['tag'] == tag and t['server_id'] == ctx.message.server.id:
                t['result'] = tag_result
                if config.saveContent('tags', tags):
                    await self.bot.say("I have just updated the tag `{0}`! You can call this tag by entering !tag {0}".format(tag))
                else:
                    await self.bot.say("I was unable to save this data")
                return
        tags.append({'server_id': ctx.message.server.id, 'tag': tag, 'result': tag_result})
        if config.saveContent('tags', tags):
            await self.bot.say("I have just added the tag `{0}`! You can call this tag by entering !tag {0}".format(tag))
        else:
            await self.bot.say("I was unable to save this data")

    @tag.command(name='delete', aliases=['remove', 'stop'], pass_context=True, no_pm=True)
    @checks.customPermsOrRole("kick_members")
    async def del_tag(self, ctx, *, tag: str):
        """Use this to remove a tag that from use for this server
        Format to delete a tag is !tag delete <tag>"""
        tags = config.getContent('tags')
        result = [t for t in tags if t['tag'] == tag and t['server_id'] == ctx.message.server.id]
        if len(result) == 0:
            await self.bot.say(
                "The tag {} does not exist! You can't remove something if it doesn't exist...".format(tag))
            return
        for t in tags:
            if t['tag'] == tag and t['server_id'] == ctx.message.server.id:
                tags.remove(t)
                if config.saveContent('tags', tags):
                    await self.bot.say('I have just removed the tag `{}`'.format(tag))
                else:
                    await self.bot.say("I was unable to save this data")
