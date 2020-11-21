import asyncio

from discord.ext import commands
import discord

loop = asyncio.get_event_loop()


def should_ignore(ctx):
    if ctx.message.guild is None:
        return False
    ignored = ctx.bot.cache.ignored[ctx.guild.id]
    if not ignored:
        return False
    return (
        ctx.message.author.id in ignored["members"]
        or ctx.message.channel.id in ignored["channels"]
    )


async def check_not_restricted(ctx):
    # Return true if this is a private channel, we'll handle that in the registering of the command
    if type(ctx.message.channel) is discord.DMChannel:
        return True

    # First get all the restrictions
    restrictions = ctx.bot.cache.restrictions[ctx.guild.id]
    # Now lets check the "from" restrictions
    for from_restriction in restrictions.get("from", []):
        # Get the source and destination
        # Source should ALWAYS be a command in this case
        source = from_restriction.get("source")
        destination = from_restriction.get("destination")
        # Special check for what the "disable" command produces
        if destination == "everyone" and ctx.command.qualified_name == source:
            return False
        # If this isn't the command we care about, continue
        if source != ctx.command.qualified_name:
            continue

        # If the destination isn't everyone, then it's an integer
        destination = int(destination)

        # This means that the type of restriction we have is `command from channel`
        # Which means we do not want commands to be ran in this channel
        if destination == ctx.channel.id:
            return False
        # This type is `command from Role` meaning anyone with this role can't run this command
        elif discord.utils.get(ctx.author.roles, id=destination):
            return False
        # This is `command from Member` meaning this user specifically cannot run this command
        elif destination == ctx.author.id:
            return False

    # If we are here, then there are no blacklists stopping this from running

    # Now for the to restrictions this is a little different, we need to make a whitelist and
    # see if our current channel is in this whitelist, as well as any whitelisted roles are in the author's roles
    # Only if there is no whitelist, do we want to blanket return True
    to_restrictions = restrictions.get("to", [])
    if not to_restrictions:
        return True

    # If the author has a role that should whitelist them
    whitelisted_role = False
    # If this channel is one that is whitelisted
    whitelisted_channel = False
    # If a whitelist was found for this command
    whitelist_found = False

    # Otherwise check whitelists
    for to_restriction in to_restrictions:
        # Get the source and destination
        # Source should ALWAYS be a command in this case
        source = to_restriction.get("source")
        destination = int(to_restriction.get("destination"))
        # If this isn't the source we care about, continue
        if source != ctx.command.qualified_name:
            continue

        # If we've found a whitelist valid for this command, now we can set it
        whitelist_found = True
        # Now check against roles
        if not whitelisted_role and discord.utils.get(ctx.author.roles, id=destination):
            whitelisted_role = True
        if ctx.channel.id == destination:
            whitelisted_channel = True

    # If we have reached here, then there is a whitelist... so we just need to return if they matched
    # the whitelist
    return whitelisted_role or whitelisted_channel or not whitelist_found


def has_perms(ctx, **perms):
    # Return true if this is a private channel, we'll handle that in the registering of the command
    if type(ctx.message.channel) is discord.DMChannel:
        return True

    # Get the member permissions so that we can compare
    guild_perms = ctx.message.author.guild_permissions
    channel_perms = ctx.message.author.permissions_in(ctx.message.channel)
    # Currently the library doesn't handle administrator overrides..so lets do this manually
    if guild_perms.administrator:
        return True
    # Next, set the default permissions if one is not used, based on what was passed
    # This will be overriden later, if we have custom permissions
    required_perm = discord.Permissions.none()
    for perm, setting in perms.items():
        setattr(required_perm, perm, setting)

    required_perm_value = ctx.bot.cache.custom_permissions[ctx.guild.id].get(
        ctx.command.qualified_name
    )
    if required_perm_value:
        required_perm = discord.Permissions(required_perm_value)

    # Now just check if the person running the command has these permissions
    return guild_perms >= required_perm or channel_perms >= required_perm


def can_run(**kwargs):
    async def predicate(ctx):
        # Next check if it requires any certain permissions
        if kwargs and not has_perms(ctx, **kwargs):
            return False
        # Next...check custom restrictions
        if not await check_not_restricted(ctx):
            return False
        # Then if the user/channel should be ignored
        if should_ignore(ctx):
            return False
        # Otherwise....we're good
        return True

    predicate.perms = kwargs
    return commands.check(predicate)
