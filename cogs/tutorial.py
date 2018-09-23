from discord.ext import commands

from . import utils

import discord

class Tutorial:

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @utils.can_run(ownership=True)
    # @utils.can_run(send_messages=True)
    async def tutorial(self, ctx, *, cmd_or_cog = None):
        # The message we'll use to send
        output = ""

        # The list of commands we need to run through
        commands = []
        if cmd_or_cog:
            cmd = self.bot.get_command(cmd_or_cog.lower())
            # This should be a cog
            if cmd is None:
                cog = self.bot.get_cog(cmd_or_cog.title())
                if cog is None:
                    await ctx.send("Could not find a command or a cog for {}".format(cmd_or_cog))
                    return

                commands = [c for c in utils.get_all_commands(self.bot) if c.cog_name == cmd_or_cog.title()]
            # Specific command
            else:
                commands = [cmd]
        # Use all commands
        else:
            commands = list(utils.get_all_commands(self.bot))

        # Loop through all the commands that we want to use
        for command in commands:
            embed = self.generate_embed(command)
            # await ctx.author.send(embed=embed)
            await ctx.send(embed=embed)
            return
            
    def generate_embed(self, command):
        # Create the embed object
        opts = {
            "title": "`{}` command tutorial:\n\n".format(command.qualified_name),
            "colour": discord.Colour.green()
        }
        embed = discord.Embed(**opts)

        if command.help is not None:
            # Split into examples, results, and the description itself based on the string
            description, _, rest = command.help.partition('EXAMPLE:')
            example, _, rest = rest.partition('RESULT:')
            result, _, gif = rest.partition("GIF:")
        else:
            example = None
            result = None
            gif = None

        # Add a field for the aliases
        if command.aliases:
            embed.add_field(
                name="Aliases",
                value="\n".join(["\t{}".format(alias) for alias in command.aliases]),
                inline=False
            )
        # Add any paramaters needed
        if command.clean_params:
            params = []
            for key, value in command.clean_params.items():
                # Get the parameter type, as well as the default value if it exists
                param_type, has_default, default_value = str(value).partition("=")
                try:
                    # We want everything after the :
                    param_type = param_type.split(":")[1]
                    # Now we want to split based on . (for possible deep level types IE discord.member.Member) then get the last value
                    param_type = param_type.split(".")
                    param_type = param_type[len(param_type) - 1]
                # This could mean something like *param was provided as the parameter
                except IndexError:
                    param_type = "str"

                # Start the string that we'll use as the param's info
                string = "{} (Type: {}".format(key, param_type)

                if default_value:
                    string += ", Default: {}".format(default_value)

                # This is the = from the partition, if it exists, then there's a default...hence the name
                if has_default:
                    string += ", optional)"
                else:
                    string += ", required)"

                # Now push our string to the list of params
                params.append(string)
            name = "Paramaters"
            embed.add_field(name=name, value="\n".join(params), inline=False)
        # Set the description of the embed to the description
        if description:
            embed.description = description
        # Add these two in one embed
        if example and result:
            embed.add_field(
                name="Example",
                value="{}\n{}".format(example.strip(), result.strip()),
                inline=False
            )
        try:
            can_run = [func for func in command.checks if "can_run" in func.__qualname__][0]
            perms = ",".join(attribute for attribute, setting in can_run.perms.items() if setting)
            embed.set_footer(text="Permissions required: {}".format(perms))
        except IndexError:
            pass

        return embed



def setup(bot):
    bot.add_cog(Tutorial(bot))