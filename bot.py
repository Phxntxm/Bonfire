import discord
import traceback
import logging
import datetime
import pendulum
import os
import aiohttp

os.chdir(os.path.dirname(os.path.realpath(__file__)))

from discord.ext import commands
import utils

opts = {
    'command_prefix': utils.command_prefix,
    'description': utils.bot_description,
    'pm_help': None,
    'command_not_found': '',
    'activity': discord.Activity(name=utils.default_status, type=0)
}

bot = commands.AutoShardedBot(**opts)
logging.basicConfig(level=logging.INFO, filename='bonfire.log')


@bot.before_invoke
async def start_typing(ctx):
    try:
        await ctx.trigger_typing()
    except (discord.Forbidden, discord.HTTPException):
        pass


@bot.event
async def on_command_completion(ctx):
    author = ctx.author.id
    guild = ctx.guild.id if ctx.guild else None
    command = ctx.command.qualified_name

    await bot.db.execute(
        "INSERT INTO command_usage(command, guild, author) VALUES ($1, $2, $3)",
        command,
        guild,
        author
    )

    # Now add credits to a users amount
    # user_credits = bot.db.load('credits', key=ctx.author.id, pluck='credits') or 1000
    # user_credits = int(user_credits) + 5
    # update = {
    #    'member_id': str(ctx.author.id),
    #    'credits': user_credits
    # }
    # await bot.db.save('credits', update)


@bot.event
async def on_command_error(ctx, error):
    error = error.original if hasattr(error, "original") else error
    ignored_errors = (
        commands.CommandNotFound,
        commands.DisabledCommand,
        discord.Forbidden,
        aiohttp.ClientOSError,
        commands.CheckFailure,
        commands.CommandOnCooldown,
    )

    if isinstance(error, ignored_errors):
        return
    elif isinstance(error, discord.HTTPException) and (
            'empty message' in str(error) or
            'INTERNAL SERVER ERROR' in str(error) or
            'REQUEST ENTITY TOO LARGE' in str(error) or
            'Unknown Message' in str(error) or
            'Origin Time-out' in str(error) or
            'Bad Gateway' in str(error) or
            'Gateway Time-out' in str(error) or
            'Explicit content' in str(error)):
        return
    elif isinstance(error, discord.NotFound) and 'Unknown Channel' in str(error):
        return

    try:
        if isinstance(error, (commands.BadArgument, commands.BadUnionArgument)):
            fmt = "Please provide a valid argument to pass to the command: {}".format(error)
            await ctx.message.channel.send(fmt)
        elif isinstance(error, commands.NoPrivateMessage):
            fmt = "This command cannot be used in a private message"
            await ctx.message.channel.send(fmt)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.message.channel.send(error)
        elif isinstance(error, (
                commands.InvalidEndOfQuotedStringError,
                commands.ExpectedClosingQuoteError,
                commands.UnexpectedQuoteError)
                        ):
            await ctx.message.channel.send("Quotes must go around the arguments you want to provide to the command,"
                                           " recheck where your quotes are")
        else:
            if isinstance(bot.error_channel, int):
                bot.error_channel = bot.get_channel(bot.error_channel)

            if bot.error_channel is None:
                now = datetime.datetime.now()
                with open("error_log", 'a') as f:
                    print("In server '{0.message.guild}' at {1}\n"
                          "Full command: `{0.message.content}`".format(ctx, str(now)), file=f)
                    traceback.print_tb(error.__traceback__, file=f)
                    print('{0.__class__.__name__}: {0}'.format(error), file=f)
            else:
                await bot.error_channel.send(f"""```
Command = {discord.utils.escape_markdown(ctx.message.clean_content).strip()}
{''.join(traceback.format_tb(error.__traceback__)).strip()}
{error.__class__.__name__}: {error}```""")
    except discord.HTTPException:
        pass


if __name__ == '__main__':
    bot.remove_command('help')
    # Setup our bot vars, db and cache
    bot.db = utils.DB()
    bot.cache = utils.Cache(bot.db)
    bot.error_channel = utils.error_channel
    # Start our startup task (cache sets up the database, so just this)
    bot.loop.create_task(bot.cache.setup())
    for e in utils.extensions:
        bot.load_extension(e)

    bot.uptime = pendulum.now(tz="UTC")
    bot.run(utils.bot_token)
