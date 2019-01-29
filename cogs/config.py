from discord.ext import commands
from asyncpg import UniqueViolationError

import utils

import discord

valid_perms = [p for p in dir(discord.Permissions) if isinstance(getattr(discord.Permissions, p), property)]


class ConfigException(Exception):
    pass


class WrongSettingType(ConfigException):

    def __init__(self, message):
        self.message = message


class MessageFormatError(ConfigException):

    def __init__(self, original, keys):
        self.original = original
        self.keys = keys


class GuildConfiguration:
    """Handles configuring the different settings that can be used on the bot"""

    def _str_to_bool(self, opt, setting):
        setting = setting.title()
        if setting.title() not in ["True", "False"]:
            raise WrongSettingType(
                f"The {opt} setting requires either 'True' or 'False', not {setting}"
            )

        return setting.title() == "True"

    async def _get_channel(self, ctx, setting):
        converter = commands.converter.TextChannelConverter()
        return await converter.convert(ctx, setting)

    async def _set_db_guild_opt(self, opt, setting, ctx):
        if opt == "prefix":
            ctx.bot.cache.update_prefix(ctx.guild, setting)
        try:
            return await ctx.bot.db.execute(f"INSERT INTO guilds (id, {opt}) VALUES ($1, $2)", ctx.guild.id, setting)
        except UniqueViolationError:
            return await ctx.bot.db.execute(f"UPDATE guilds SET {opt} = $1 WHERE id = $2", setting, ctx.guild.id)

    # These are handles for each setting type
    async def _handle_set_birthday_notifications(self, ctx, setting):
        opt = "birthday_notifications"
        setting = self._str_to_bool(opt, setting)
        return await self._set_db_guild_opt(opt, setting, ctx)

    async def _handle_set_welcome_notifications(self, ctx, setting):
        opt = "welcome_notifications"
        setting = self._str_to_bool(opt, setting)
        return await self._set_db_guild_opt(opt, setting, ctx)

    async def _handle_set_goodbye_notifications(self, ctx, setting):
        opt = "goodbye_notifications"
        setting = self._str_to_bool(opt, setting)
        return await self._set_db_guild_opt(opt, setting, ctx)

    async def _handle_set_colour_roles(self, ctx, setting):
        opt = "colour_roles"
        setting = self._str_to_bool(opt, setting)
        return await self._set_db_guild_opt(opt, setting, ctx)

    async def _handle_set_include_default_battles(self, ctx, setting):
        opt = "include_default_battles"
        setting = self._str_to_bool(opt, setting)
        return await self._set_db_guild_opt(opt, setting, ctx)

    async def _handle_set_include_default_hugs(self, ctx, setting):
        opt = "include_default_hugs"
        setting = self._str_to_bool(opt, setting)
        return await self._set_db_guild_opt(opt, setting, ctx)

    async def _handle_set_welcome_msg(self, ctx, setting):
        try:
            setting.format(member='test', server='test')
        except KeyError as e:
            raise MessageFormatError(e, ["member", "server"])
        else:
            return await self._set_db_guild_opt("welcome_msg", setting, ctx)

    async def _handle_set_goodbye_msg(self, ctx, setting):
        try:
            setting.format(member='test', server='test')
        except KeyError as e:
            raise MessageFormatError(e, ["member", "server"])
        else:
            return await self._set_db_guild_opt("goodbye_msg", setting, ctx)

    async def _handle_set_prefix(self, ctx, setting):
        if len(setting) > 20:
            raise WrongSettingType("Please keep the prefix under 20 characters")
        if setting.lower().strip() == "none":
            setting = None

        result = await self._set_db_guild_opt("prefix", setting, ctx)
        # We want to update our cache for prefixes
        ctx.bot.cache.update_prefix(ctx.guild, setting)
        return result

    async def _handle_set_default_alerts(self, ctx, setting):
        channel = await self._get_channel(ctx, setting)
        return await self._set_db_guild_opt("default_alerts", channel.id, ctx)

    async def _handle_set_welcome_alerts(self, ctx, setting):
        channel = await self._get_channel(ctx, setting)
        return await self._set_db_guild_opt("welcome_alerts", channel.id, ctx)

    async def _handle_set_goodbye_alerts(self, ctx, setting):
        channel = await self._get_channel(ctx, setting)
        return await self._set_db_guild_opt("goodbye_alerts", channel.id, ctx)

    async def _handle_set_picarto_alerts(self, ctx, setting):
        channel = await self._get_channel(ctx, setting)
        return await self._set_db_guild_opt("picarto_alerts", channel.id, ctx)

    async def _handle_set_birthday_alerts(self, ctx, setting):
        channel = await self._get_channel(ctx, setting)
        return await self._set_db_guild_opt("birthday_alerts", channel.id, ctx)

    async def _handle_set_raffle_alerts(self, ctx, setting):
        channel = await self._get_channel(ctx, setting)
        return await self._set_db_guild_opt("raffle_alerts", channel.id, ctx)

    async def _handle_set_followed_picarto_channels(self, ctx, setting):
        user = await utils.request(f"http://api.picarto.tv/v1/channel/name/{setting}")
        if user is None:
            raise WrongSettingType(f"Could not find a picarto user with the username {setting}")

        query = """
UPDATE
    guilds
SET
    followed_picarto_channels = array_append(followed_picarto_channels, $1)
WHERE
    id=$2 AND
    NOT $1 = ANY(followed_picarto_channels);
"""
        return await ctx.bot.db.execute(query, setting, ctx.guild.id)

    async def _handle_set_ignored_channels(self, ctx, setting):
        channel = await self._get_channel(ctx, setting)

        query = """
UPDATE
    guilds
SET
    ignored_channels = array_append(ignored_channels, $1)
WHERE
    id=$2 AND
    NOT $1 = ANY(ignored_channels);
"""
        ctx.bot.loop.create_task(ctx.cache.load_ignored())
        return await ctx.bot.db.execute(query, channel.id, ctx.guild.id)

    async def _handle_set_ignored_members(self, ctx, setting):
        # We want to make it possible to have members that aren't in the server ignored
        # So first check if it's a digit (the id)
        if not setting.isdigit():
            converter = commands.converter.MemberConverter()
            member = await converter.convert(ctx, setting)
            setting = member.id

        query = """
UPDATE
    guilds
SET
    ignored_members = array_append(ignored_members, $1)
WHERE
    id=$2 AND
    NOT $1 = ANY(ignored_members);
"""
        ctx.bot.loop.create_task(ctx.cache.load_ignored())
        return await ctx.bot.db.execute(query, setting, ctx.guild.id)

    async def _handle_set_rules(self, ctx, setting):
        query = """
UPDATE
    guilds
SET
    rules = array_append(rules, $1)
WHERE
    id=$2 AND
    NOT $1 = ANY(rules);
"""
        return await ctx.bot.db.execute(query, setting, ctx.guild.id)

    async def _handle_set_assignable_roles(self, ctx, setting):
        converter = commands.converter.RoleConverter()
        role = await converter.convert(ctx, setting)

        query = """
UPDATE
    guilds
SET
    assignable_roles = array_append(assignable_roles, $1)
WHERE
    id=$2 AND
    NOT $1 = ANY(assignable_roles);
"""
        return await ctx.bot.db.execute(query, role.id, ctx.guild.id)

    async def _handle_set_custom_battles(self, ctx, setting):
        try:
            setting.format(loser="player1", winner="player2")
        except KeyError as e:
            raise MessageFormatError(e, ["loser", "winner"])
        else:
            query = """
UPDATE
    guilds
SET
    custom_battles = array_append(custom_battles, $1)
WHERE
    id=$2 AND
    NOT $1 = ANY(custom_battles);
"""
        return await ctx.bot.db.execute(query, setting, ctx.guild.id)

    async def _handle_set_custom_hugs(self, ctx, setting):
        try:
            setting.format(user="user")
        except KeyError as e:
            raise MessageFormatError(e, ["user"])
        else:
            query = """
UPDATE
    guilds
SET
    custom_hugs = array_append(custom_hugs, $1)
WHERE
    id=$2 AND
    NOT $1 = ANY(custom_hugs);
"""
        return await ctx.bot.db.execute(query, setting, ctx.guild.id)

    async def _handle_remove_birthday_notifications(self, ctx, setting=None):
        return await self._set_db_guild_opt("birthday_notifications", False, ctx)

    async def _handle_remove_welcome_notifications(self, ctx, setting=None):
        return await self._set_db_guild_opt("welcome_notifications", False, ctx)

    async def _handle_remove_goodbye_notifications(self, ctx, setting=None):
        return await self._set_db_guild_opt("goodbye_notifications", False, ctx)

    async def _handle_remove_colour_roles(self, ctx, setting=None):
        return await self._set_db_guild_opt("colour_roles", False, ctx)

    async def _handle_remove_include_default_battles(self, ctx, setting=None):
        return await self._set_db_guild_opt("include_default_battles", False, ctx)

    async def _handle_remove_include_default_hugs(self, ctx, setting=None):
        return await self._set_db_guild_opt("include_default_hugs", False, ctx)

    async def _handle_remove_welcome_msg(self, ctx, setting=None):
        return await self._set_db_guild_opt("welcome_msg", None, ctx)

    async def _handle_remove_goodbye_msg(self, ctx, setting=None):
        return await self._set_db_guild_opt("goodbye_msg", None, ctx)

    async def _handle_remove_prefix(self, ctx, setting=None):
        return await self._set_db_guild_opt("prefix", None, ctx)

    async def _handle_remove_default_alerts(self, ctx, setting=None):
        return await self._set_db_guild_opt("default_alerts", None, ctx)

    async def _handle_remove_welcome_alerts(self, ctx, setting=None):
        return await self._set_db_guild_opt("welcome_alerts", None, ctx)

    async def _handle_remove_goodbye_alerts(self, ctx, setting=None):
        return await self._set_db_guild_opt("goodbye_alerts", None, ctx)

    async def _handle_remove_picarto_alerts(self, ctx, setting=None):
        return await self._set_db_guild_opt("picarto_alerts", None, ctx)

    async def _handle_remove_birthday_alerts(self, ctx, setting=None):
        return await self._set_db_guild_opt("birthday_alerts", None, ctx)

    async def _handle_remove_raffle_alerts(self, ctx, setting=None):
        return await self._set_db_guild_opt("raffle_alerts", None, ctx)

    async def _handle_remove_followed_picarto_channels(self, ctx, setting=None):
        if setting is None:
            raise WrongSettingType("Specifying which channel you want to remove is required")

        query = """
UPDATE
    guilds
SET
    followed_picarto_channels = array_remove(followed_picarto_channels, $1)
WHERE
    id=$2
"""
        return await ctx.bot.db.execute(query, setting, ctx.guild.id)

    async def _handle_remove_ignored_channels(self, ctx, setting=None):
        if setting is None:
            raise WrongSettingType("Specifying which channel you want to remove is required")

        channel = await self._get_channel(ctx, setting)

        query = """
UPDATE
    guilds
SET
    ignored_channels = array_remove(ignored_channels, $1)
WHERE
    id=$2
"""
        return await ctx.bot.db.execute(query, channel.id, ctx.guild.id)

    async def _handle_remove_ignored_members(self, ctx, setting=None):
        if setting is None:
            raise WrongSettingType("Specifying which channel you want to remove is required")
        # We want to make it possible to have members that aren't in the server ignored
        # So first check if it's a digit (the id)
        if not setting.isdigit():
            converter = commands.converter.MemberConverter()
            member = await converter.convert(ctx, setting)
            setting = member.id

        query = """
UPDATE
    guilds
SET
    ignored_members = array_remove(ignored_members, $1)
WHERE
    id=$2
"""
        return await ctx.bot.db.execute(query, setting, ctx.guild.id)

    async def _handle_remove_rules(self, ctx, setting=None):
        if setting is None or not setting.isdigit():
            raise WrongSettingType("Please provide the number of the rule you want to remove")

        query = """
UPDATE
    guilds
SET
    rules = array_remove(rules, rules[$1])
WHERE
    id=$2
"""
        return await ctx.bot.db.execute(query, setting, ctx.guild.id)

    async def _handle_remove_assignable_roles(self, ctx, setting=None):
        if setting is None:
            raise WrongSettingType("Specifying which channel you want to remove is required")
        if not setting.isdigit():
            converter = commands.converter.RoleConverter()
            role = await converter.convert(ctx, setting)
            setting = role.id

        query = """
UPDATE
    guilds
SET
    assignable_roles = array_remove(assignable_roles, $1)
WHERE
    id=$2
"""
        return await ctx.bot.db.execute(query, setting, ctx.guild.id)

    async def _handle_remove_custom_battles(self, ctx, setting=None):
        if setting is None or not setting.isdigit():
            raise WrongSettingType("Please provide the number of the custom battle you want to remove")

        query = """
UPDATE
    guilds
SET
    custom_battles = array_remove(custom_battles, rules[$1])
WHERE
    id=$2
"""
        return await ctx.bot.db.execute(query, setting, ctx.guild.id)

    async def _handle_remove_custom_hugs(self, ctx, setting=None):
        if setting is None or not setting.isdigit():
            raise WrongSettingType("Please provide the number of the custom hug you want to remove")

        query = """
UPDATE
    guilds
SET
    custom_hugs = array_remove(custom_hugs, rules[$1])
WHERE
    id=$2
"""
        return await ctx.bot.db.execute(query, setting, ctx.guild.id)

    async def __after_invoke(self, ctx):
        """Here we will facilitate cleaning up settings, will remove channels/roles that no longer exist, etc."""
        pass

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @utils.can_run(manage_guild=True)
    async def config(self, ctx, *, opt=None):
        """Handles the configuration of the bot for this server"""
        if opt:
            setting = await ctx.bot.db.fetchrow("SELECT * FROM guilds WHERE id=$1", ctx.guild.id)
            if setting and opt in setting:
                setting = await utils.convert(ctx, str(setting[opt])) or setting[opt]

                await ctx.send(f"{opt} is set to:\n{setting}")
                return

        settings = await ctx.bot.db.fetchrow("SELECT * FROM guilds WHERE id=$1", ctx.guild.id)

        # For convenience, if it's None, just create it and return the default values
        if settings is None:
            await ctx.bot.db.execute("INSERT INTO guilds (id) VALUES ($1)", ctx.guild.id)
            settings = await ctx.bot.db.fetchrow("SELECT * FROM guilds WHERE id=$1", ctx.guild.id)

        alerts = {}
        # This is dirty I know, but oh well...
        for alert_type in ["default", "welcome", "goodbye", "picarto", "birthday", "raffle"]:
            channel = ctx.guild.get_channel(settings.get(f"{alert_type}_alerts"))
            name = channel.name if channel else None
            alerts[alert_type] = name

        fmt = f"""
**Notification Settings**
    birthday_notifications
    *Notify on the birthday that users in this guild have saved*
    **{settings.get("birthday_notifications")}**
    
    welcome_notifications
    *Notify when someone has joined this guild*
    **{settings.get("welcome_notifications")}** 
    
    goodbye_notifications
    *Notify when someone has left this guild
    **{settings.get("goodbye_notifications")}**
    
    welcome_msg
    *A message that can be customized and used when someone joins the server*
    **{"Set" if settings.get("welcome_msg") is not None else "Not set"}** 
    
    goodbye_msg
    *A message that can be customized and used when someone leaves the server*
    **{"Set" if settings.get("goodbye_msg") is not None else "Not set"}**
    
**Alert Channels**
    default_alerts
    *The channel to default alert messages to*
    **{alerts.get("default_alerts")}**
    
    welcome_alerts
    *The channel to send welcome alerts to (when someone joins the server)*
    **{alerts.get("welcome_alerts")}**
    
    goodbye_alerts
    *The channel to send goodbye alerts to (when someone leaves the server)*
    **{alerts.get("goodbye_alerts")}**
    
    picarto_alerts
    *The channel to send Picarto alerts to (when a channel the server follows goes on/offline)*
    **{alerts.get("picarto_alerts")}**
    
    birthday_alerts
    *The channel to send birthday alerts to (on the day of someone's birthday)*
    **{alerts.get("birthday_alerts")}**
    
    raffle_alerts
    *The channel to send alerts for server raffles to*
    **{alerts.get("raffle_alerts")}**


**Misc Settings**
    followed_picarto_channels
    *Channels for the bot to "follow" and notify this server when they go live*
    **{len(settings.get("followed_picarto_channels"))}**
    
    ignored_channels
    *Channels that the bot ignores*
    **{len(settings.get("ignored_channels"))}** 
    
    ignored_members
    *Members that the bot ignores*
    **{len(settings.get("ignored_members"))}**
    
    rules
    *Rules for this server*
    **{len(settings.get("rules"))}**
    
    assignable_roles
    *Roles that can be self-assigned by users*
    **{len(settings.get("assignable_roles"))}**
    
    custom_battles
    *Possible outcomes to battles that can be received on this server*
    **{len(settings.get("custom_battles"))}** 
    
    custom_hugs
    *Possible outcomes to hugs that can be received on this server*
    **{len(settings.get("custom_hugs"))}** 
""".strip()

        embed = discord.Embed(title=f"Configuration for {ctx.guild.name}", description=fmt)
        embed.set_image(url=ctx.guild.icon_url)
        await ctx.send(embed=embed)

    @config.command(name="set", aliases=["add"])
    @commands.guild_only()
    @utils.can_run(manage_guild=True)
    async def _set_setting(self, ctx, option, *, setting):
        """Sets one of the configuration settings for this server"""
        try:
            coro = getattr(self, f"_handle_set_{option}")
        except AttributeError:
            await ctx.send(f"{option} is not a valid config option. Use {ctx.prefix}config to list all config options")
        else:
            try:
                await coro(ctx, setting=setting)
            except WrongSettingType as exc:
                await ctx.send(exc.message)
            except MessageFormatError as exc:
                fmt = f"""
Failed to parse the format string provided, possible keys are: {', '.join(k for k in exc.keys)}
Extraneous args provided: {', '.join(k for k in exc.original.args)}
"""
                await ctx.send(fmt)
            except commands.BadArgument:
                pass
            else:
                await ctx.send(f"{option} has succesfully been set to {setting}")

    @config.command(name="unset", aliases=["remove"])
    @commands.guild_only()
    @utils.can_run(manage_guild=True)
    async def _remove_setting(self, ctx, option, *, setting=None):
        """Unsets/removes an option from one of the settings."""
        try:
            coro = getattr(self, f"_handle_remove_{option}")
        except AttributeError:
            await ctx.send(f"{option} is not a valid config option. Use {ctx.prefix}config to list all config options")
        else:
            try:
                await coro(ctx, setting=setting)
            except WrongSettingType as exc:
                await ctx.send(exc.message)
            except commands.BadArgument:
                pass
            else:
                await ctx.send(f"{option} has succesfully been unset")


def setup(bot):
    bot.add_cog(GuildConfiguration())