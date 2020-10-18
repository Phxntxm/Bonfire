import discord
import logging
import pendulum
import aiohttp
import asyncio

from discord.ext import commands
import utils

intent = discord.Intents.all()
intent.presences = False

opts = {
    "command_prefix": utils.command_prefix,
    "description": utils.bot_description,
    "pm_help": None,
    "command_not_found": "",
    "activity": discord.Activity(name=utils.default_status, type=0),
    "allowed_mentions": discord.AllowedMentions(everyone=False),
    "intents": intent,
    "chunk_guilds_at_startup": False,
}

bot = commands.AutoShardedBot(**opts)
logging.basicConfig(level=logging.INFO, filename="bonfire.log")


@bot.before_invoke
async def before_invocation(ctx):
    # Start typing
    try:
        await ctx.trigger_typing()
    except (discord.Forbidden, discord.HTTPException):
        pass

    # If this is a DM, or the guild has been chunked, we're done
    if not ctx.guild or ctx.guild.chunked:
        return

    # Get a lock for the guild
    lock = bot.chunked_guild_locks.get(ctx.guild.id)
    # If one hasn't been created yet, create it
    if lock is None:
        lock = asyncio.Lock()
        bot.chunked_guild_locks[ctx.guild.id] = lock
    # Now only try to chunk when the lock is available
    async with lock:
        # Recheck if it's been chunked just in case, don't want to chunk if we don't have to
        if ctx.guild and not ctx.guild.chunked:
            await ctx.guild.chunk()


@bot.event
async def on_command_completion(ctx):
    author = ctx.author.id
    guild = ctx.guild.id if ctx.guild else None
    command = ctx.command.qualified_name

    await bot.db.execute(
        "INSERT INTO command_usage(command, guild, author) VALUES ($1, $2, $3)",
        command,
        guild,
        author,
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
        "empty message" in str(error)
        or "INTERNAL SERVER ERROR" in str(error)
        or "REQUEST ENTITY TOO LARGE" in str(error)
        or "Unknown Message" in str(error)
        or "Origin Time-out" in str(error)
        or "Bad Gateway" in str(error)
        or "Gateway Time-out" in str(error)
        or "Explicit content" in str(error)
    ):
        return
    elif isinstance(error, discord.NotFound) and "Unknown Channel" in str(error):
        return

    try:
        if isinstance(error, (commands.BadArgument, commands.BadUnionArgument)):
            fmt = "Please provide a valid argument to pass to the command: {}".format(
                error
            )
            await ctx.message.channel.send(fmt)
        elif isinstance(error, commands.NoPrivateMessage):
            fmt = "This command cannot be used in a private message"
            await ctx.message.channel.send(fmt)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.message.channel.send(error)
        elif isinstance(
            error,
            (
                commands.InvalidEndOfQuotedStringError,
                commands.ExpectedClosingQuoteError,
                commands.UnexpectedQuoteError,
            ),
        ):
            await ctx.message.channel.send(
                "Quotes must go around the arguments you want to provide to the command,"
                " recheck where your quotes are"
            )
        else:
            await utils.log_error(error, ctx.bot, ctx)
    except discord.HTTPException:
        pass


if __name__ == "__main__":
    bot.remove_command("help")
    # Setup our bot vars, db and cache
    bot.db = utils.DB()
    bot.cache = utils.Cache(bot.db)
    bot.error_channel = utils.error_channel
    # Start our startup task (cache sets up the database, so just this)
    bot.loop.create_task(bot.cache.setup())
    for e in utils.extensions:
        bot.load_extension(e)

    bot.uptime = pendulum.now(tz="UTC")
    bot.chunked_guild_locks = {}
    bot.run(utils.bot_token)
