from discord.ext import commands
import discord

import utils

import re
import asyncio


class Roles(commands.Cog):
    """Class to handle management of roles on the server"""

    @commands.command(aliases=["color"])
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def colour(self, ctx, role_colour: discord.Colour):
        """Used to give yourself a role matching the colour given.
        If the role doesn't exist, it will be created. Names such as red, blue, yellow, etc. can be used.
        Additionally, hex codes can be used as well

        EXAMPLE: !colour red
        RESULT: A role that matches red (#e74c3c) will be given to you"""
        result = await ctx.bot.db.fetchrow(
            "SELECT colour_roles FROM guilds WHERE id = $1", ctx.guild.id
        )
        if result and not result["colour_roles"]:
            await ctx.send(
                "Colour roles not allowed on this server! "
                "The command `allowcolours` must be ran to enable them!"
            )
            return

        if not ctx.me.guild_permissions.manage_roles:
            await ctx.send("Error: I need manage_roles to be able to use this command")
            return

        # The convention we'll use for the name
        name = "Bonfire {}".format(role_colour)

        # Try to find a role that matches our convention, Name #000000 with the colour matching
        role = discord.utils.get(ctx.guild.roles, name=name, colour=role_colour)

        # The colour roles they currently have, we need to remove them if they want a new colour
        old_roles = [
            r for r in ctx.author.roles if re.match(r"Bonfire #[0-9a-zA-Z]+", r.name)
        ]
        if old_roles:
            await ctx.author.remove_roles(*old_roles)

        # If the role doesn't exist, we need to create it
        if not role:
            opts = {"name": name, "colour": role_colour}
            try:
                role = await ctx.guild.create_role(**opts)
            except discord.HTTPException:
                await ctx.send("{} is not a valid colour".format(role_colour))
                return
        # Now add the role
        await ctx.author.add_roles(role)

        await ctx.send("I have just given you your requested colour!")

    @commands.group(aliases=["roles"], invoke_without_command=True)
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def role(self, ctx, *, role: discord.Role = None):
        """This command can be used to modify the roles on the server.
        Pass no subcommands and this will print the roles currently available on this server
        If you give a role as the argument then it will give some information about that role

        EXAMPLE: !role
        RESULT: A list of all your roles"""

        if role:
            # Create the embed object
            opts = {
                "title": role.name,
                "colour": role.colour,
            }
            if role.managed:
                opts["description"] = "This role is managed by a third party service"
            embed = discord.Embed(**opts)
            # Add details to it
            embed.add_field(name="Created", value=role.created_at.date())
            embed.add_field(
                name="Mentionable", value="Yes" if role.mentionable else "No"
            )
            total_members = len(role.members)
            embed.add_field(name="Total members", value=str(total_members))
            # If there are only a few members in this role, display them
            if 5 >= total_members > 0:
                embed.add_field(
                    name="Members",
                    value="\n".join(m.display_name for m in role.members),
                )
            await ctx.send(embed=embed)
        else:
            # Don't include the colour roles
            colour_role = re.compile("Bonfire #.+")
            # Simply get a list of all roles in this server and send them
            entries = [
                r.name for r in ctx.guild.roles[1:] if not colour_role.match(r.name)
            ]
            if len(entries) == 0:
                await ctx.send(
                    "You do not have any roles setup on this server, other than the default role!"
                )
                return

            try:
                pages = utils.Pages(ctx, entries=entries)
                await pages.paginate()
            except utils.CannotPaginate as e:
                await ctx.send(str(e))

    @role.command(name="remove")
    @commands.guild_only()
    @utils.can_run(manage_roles=True)
    async def remove_role(self, ctx):
        """Use this to remove roles from a number of members

        EXAMPLE: !role remove @Jim @Bot @Joe
        RESULT: A follow-along to remove the role(s) you want to, from these 3 members"""
        # No use in running through everything if the bot cannot manage roles
        if not ctx.message.guild.me.permissions_in(ctx.message.channel).manage_roles:
            await ctx.send(
                "I can't manage roles in this server, do you not trust  me? :c"
            )
            return
        check = (
            lambda m: m.author == ctx.message.author
            and m.channel == ctx.message.channel
        )

        server_roles = [
            role for role in ctx.message.guild.roles if not role.is_default()
        ]
        # First get the list of all mentioned users
        members = ctx.message.mentions
        # If no users are mentioned, ask the author for a list of the members they want to remove the role from
        if len(members) == 0:
            await ctx.send(
                "Please provide the list of members you want to remove a role from"
            )
            try:
                msg = await ctx.bot.wait_for("message", check=check, timeout=60)
            except asyncio.TimeoutError:
                await ctx.send("You took too long. I'm impatient, don't make me wait")
                return
            if len(msg.mentions) == 0:
                await ctx.send(
                    "I cannot remove a role from someone if you don't provide someone..."
                )
                return
            # Override members if everything has gone alright, and then continue
            members = msg.mentions

        # This allows the user to remove multiple roles from the list of users, if they want.
        await ctx.send(
            "Alright, please provide the roles you would like to remove from this member. "
            "Make sure the roles, if more than one is provided, are separate by commas. "
        )
        try:
            msg = await ctx.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("You took too long. I'm impatient, don't make me wait")
            return

        # Split the content based on commas, using regex so we can split if a space was not provided or if it was
        role_names = re.split(", ?", msg.content)
        roles = []
        # This loop is just to get the actual role objects based on the name
        for role in role_names:
            _role = discord.utils.get(server_roles, name=role)
            if _role is not None:
                roles.append(_role)

        # If no valid roles were given, let them know that and return
        if len(roles) == 0:
            await ctx.send("Please provide a valid role next time!")
            return

        # Otherwise, remove the roles from each member given
        for member in members:
            await member.remove_roles(*roles)
        await ctx.send(
            "I have just removed the following roles:```\n{}``` from the following members:"
            "```\n{}```".format(
                "\n".join(role_names), "\n".join([m.display_name for m in members])
            )
        )

    @role.command(name="add", aliases=["give", "assign"])
    @commands.guild_only()
    @utils.can_run(manage_roles=True)
    async def add_role(self, ctx):
        """Use this to add a role to multiple members.
        Provide the list of members, and I'll ask for the role
        If no members are provided, I'll first ask for them

        EXAMPLE: !role add @Bob @Joe @jim
        RESULT: A follow along to add the roles you want to these 3"""
        # No use in running through everything if the bot cannot manage roles
        if not ctx.message.guild.me.permissions_in(ctx.message.channel).manage_roles:
            await ctx.send(
                "I can't manage roles in this server, do you not trust  me? :c"
            )
            return
        check = (
            lambda m: m.author == ctx.message.author
            and m.channel == ctx.message.channel
        )

        # This is exactly the same as removing roles, except we call add_roles instead.
        server_roles = [
            role for role in ctx.message.guild.roles if not role.is_default()
        ]
        members = ctx.message.mentions
        if len(members) == 0:
            await ctx.send(
                "Please provide the list of members you want to add a role to"
            )
            try:
                msg = await ctx.bot.wait_for("message", check=check, timeout=60)
            except asyncio.TimeoutError:
                await ctx.send("You took too long. I'm impatient, don't make me wait")
                return
            if len(msg.mentions) == 0:
                await ctx.send(
                    "I cannot add a role to someone if you don't provide someone..."
                )
                return
            members = msg.mentions

        await ctx.send(
            "Alright, please provide the roles you would like to add to this member. "
            "Make sure the roles, if more than one is provided, are separate by commas. "
        )
        try:
            msg = await ctx.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("You took too long. I'm impatient, don't make me wait")
            return
        role_names = re.split(", ?", msg.content)
        roles = []
        for role in role_names:
            _role = discord.utils.get(server_roles, name=role)
            if _role is not None:
                roles.append(_role)

        if len(roles) == 0:
            await ctx.send("Please provide a valid role next time!")
            return

        for member in members:
            await member.add_roles(*roles)
        await ctx.send(
            "I have just added the following roles:```\n{}``` to the following members:"
            "```\n{}```".format(
                "\n".join(role_names), "\n".join([m.display_name for m in members])
            )
        )

    @role.command(name="delete")
    @commands.guild_only()
    @utils.can_run(manage_roles=True)
    async def delete_role(self, ctx, *, role: discord.Role = None):
        """This command can be used to delete one of the roles from the server

        EXAMPLE: !role delete StupidRole
        RESULT: No more role called StupidRole"""
        # No use in running through everything if the bot cannot manage roles
        if not ctx.message.guild.me.permissions_in(ctx.message.channel).manage_roles:
            await ctx.send(
                "I can't delete roles in this server, do you not trust  me? :c"
            )
            return

        # If no role was given, get the current roles on the server and ask which ones they'd like to remove
        if role is None:
            server_roles = [
                role for role in ctx.message.guild.roles if not role.is_default()
            ]

            await ctx.send(
                "Which role would you like to remove from the server? Here is a list of this server's roles:"
                "```\n{}```".format("\n".join([r.name for r in server_roles]))
            )

            # For this method we're only going to delete one role at a time
            # This check attempts to find a role based on the content provided, if it can't find one it returns None
            # We can use that fact to simply use just that as our check
            def check(m):
                if m.author == ctx.message.author and m.channel == ctx.message.channel:
                    return discord.utils.get(server_roles, name=m.content) is not None
                else:
                    return False

            try:
                msg = await ctx.bot.wait_for("message", timeout=60, check=check)
            except asyncio.TimeoutError:
                await ctx.send("You took too long. I'm impatient, don't make me wait")
                return
            # If we have gotten here, based on our previous check, we know that the content provided is a valid role.
            # Due to that, no need for any error checking here
            role = discord.utils.get(server_roles, name=msg.content)

        await role.delete()
        await ctx.send(
            "I have just removed the role {} from this server".format(role.name)
        )

    @role.command(name="create")
    @commands.guild_only()
    @utils.can_run(manage_roles=True)
    async def create_role(self, ctx):
        """This command can be used to create a new role for this server
        A prompt will follow asking what settings you would like for this new role
        I'll then ask if you'd like to set anyone to use this role

        EXAMPLE: !role create
        RESULT: A follow along in order to create a new role"""
        # No use in running through everything if the bot cannot create the role
        if not ctx.message.guild.me.permissions_in(ctx.message.channel).manage_roles:
            await ctx.send(
                "I can't create roles in this server, do you not trust  me? :c"
            )
            return

        # Save a couple variables that will be used repeatedly
        author = ctx.message.author
        server = ctx.message.guild
        channel = ctx.message.channel

        # A couple checks that will be used in the wait_for_message's
        def num_seperated_check(m):
            if m.author == author and m.channel == channel:
                return re.search(r"(\d(, ?| )?|[nN]one)", m.content) is not None
            else:
                return False

        def yes_no_check(m):
            if m.author == author and m.channel == channel:
                return re.search("(yes|no)", m.content.lower()) is not None
            else:
                return False

        def members_check(m):
            if m.author == author and m.channel == channel:
                return len(m.mentions) > 0
            else:
                return False

        # Start the checks for the role, get the name of the role first
        await ctx.send(
            "Alright! I'm ready to create a new role, please respond with the name of the role you want to create"
        )
        try:
            msg = await ctx.bot.wait_for(
                "message",
                timeout=60.0,
                check=lambda m: m.author == author and m.channel == channel,
            )
        except asyncio.TimeoutError:
            await ctx.send("You took too long. I'm impatient, don't make me wait")
            return
        name = msg.content

        # Print a list of all the permissions available, then ask for which ones need to be active on this new role
        all_perms = list(discord.Permissions.VALID_FLAGS.keys())
        fmt = "\n".join("{}) {}".format(i, perm) for i, perm in enumerate(all_perms))
        await ctx.send(
            "Sounds fancy! Here is a list of all the permissions available. Please respond with just "
            "the numbers, seperated by commas, of the permissions you want this role to have.\n"
            "```\n{}```".format(fmt)
        )
        # For this we're going to give a couple extra minutes before we timeout
        # as it might take a bit to figure out which permissions they want
        try:
            msg = await ctx.bot.wait_for(
                "message", timeout=180.0, check=num_seperated_check
            )
        except asyncio.TimeoutError:
            await ctx.send("You took too long. I'm impatient, don't make me wait")
            return

        # Check if any integer's were provided that are within the length of the list of permissions
        num_permissions = [
            int(i)
            for i in re.split(" ?,?", msg.content)
            if i.isdigit() and int(i) < len(all_perms)
        ]

        # Check if this role should be in a separate section on the sidebard, i.e. hoisted
        await ctx.send(
            "Do you want this role to be in a separate section on the sidebar? (yes or no)"
        )
        try:
            msg = await ctx.bot.wait_for("message", timeout=60.0, check=yes_no_check)
        except asyncio.TimeoutError:
            await ctx.send("You took too long. I'm impatient, don't make me wait")
            return
        hoist = True if msg.content.lower() == "yes" else False

        # Check if this role should be able to be mentioned
        await ctx.send("Do you want this role to be mentionable? (yes or no)")
        try:
            msg = await ctx.bot.wait_for("message", timeout=60.0, check=yes_no_check)
        except asyncio.TimeoutError:
            await ctx.send("You took too long. I'm impatient, don't make me wait")
            return
        mentionable = True if msg.content.lower() == "yes" else False

        # Ready to actually create the role
        # First create a permissions object based on the numbers provided
        perms = discord.Permissions.none()
        for index in num_permissions:
            setattr(perms, all_perms[index], True)

        payload = {
            "name": name,
            "permissions": perms,
            "hoist": hoist,
            "mentionable": mentionable,
        }
        # Create the role, and wait a second, sometimes it goes too quickly and we get a role with 'new role' to print
        role = await server.create_role(**payload)
        await asyncio.sleep(1)
        await ctx.send(
            "We did it! You just created the new role {}\nIf you want to add this role"
            " to some people, mention them now".format(role.name)
        )
        try:
            msg = await ctx.bot.wait_for("message", timeout=60.0, check=members_check)
        except asyncio.TimeoutError:
            # There's no need to mention the users, so don't send a failure message if they didn't, just return
            return

        # Otherwise members were mentioned, add the new role to them now
        for member in msg.mentions:
            await member.add_roles(role)

        fmt = "\n".join(m.display_name for m in msg.mentions)
        await ctx.send("I have just added the role {} to: ```\n{}```".format(name, fmt))

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def assign(self, ctx, *role: discord.Role):
        """Assigns the provided role(s) to you, if they can be assigned

        EXAMPLE: !assign me Member
        RESULT: You now have the Member role"""
        if not ctx.message.guild.me.guild_permissions.manage_roles:
            await ctx.send("I need to have manage roles permissions to assign roles")
            return

        author = ctx.message.author
        result = await ctx.bot.db.fetchrow(
            "SELECT assignable_roles FROM guilds WHERE id = $1", ctx.guild.id
        )

        if result is None:
            await ctx.send("There are no self-assignable roles on this server")
            return
        self_assignable_roles = result["assignable_roles"]

        if len(self_assignable_roles) == 0:
            await ctx.send("There are no self-assignable roles on this server")
            return

        fmt = ""
        roles = [r for r in role if r.id in self_assignable_roles]
        fmt += "\n".join(
            [
                "Successfully added {}".format(r.name)
                if r.id in self_assignable_roles
                else "{} is not available to be self-assigned".format(r.name)
                for r in role
            ]
        )

        try:
            await author.add_roles(*roles)
            await ctx.send(fmt)
        except discord.HTTPException:
            await ctx.send("I cannot assign roles to you {}".format(author.mention))

    @commands.command()
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def unassign(self, ctx, *role: discord.Role):
        """Unassigns the provided role(s) to you, if they can be assigned

        EXAMPLE: !unassign Member
        RESULT: You now no longer have the Member role"""
        if not ctx.message.guild.me.guild_permissions.manage_roles:
            await ctx.send("I need to have manage roles permissions to assign roles")
            return

        author = ctx.message.author
        result = await ctx.bot.db.fetchrow(
            "SELECT assignable_roles FROM guilds WHERE id = $1", ctx.guild.id
        )

        if result is None:
            await ctx.send("There are no self-assignable roles on this server")
            return
        self_assignable_roles = result["assignable_roles"]

        if len(self_assignable_roles) == 0:
            await ctx.send("There are no self-assignable roles on this server")
            return

        fmt = ""
        roles = [r for r in role if r.id in self_assignable_roles]
        fmt += "\n".join(
            [
                f"Successfully removed {r.name}"
                if r.id in self_assignable_roles
                else f"{r.name} is not available to be self-assigned"
                for r in role
            ]
        )

        try:
            await author.remove_roles(*roles)
            await ctx.send(fmt)
        except discord.HTTPException:
            await ctx.send("I cannot remove roles from you {}".format(author.mention))


def setup(bot):
    bot.add_cog(Roles(bot))
