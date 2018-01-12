from discord.ext import commands

from . import utils

import discord

class Tutorial:

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.check(utils.is_owner)
    # @utils.custom_perms(send_messages=True)
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
            await ctx.author.send(embed=embed)
            return
            
    def generate_embed(self, command):
        # Create the embed object
        opts = {
            "title": "Here is the tutorial for the command {}:\n\n".format(command.qualified_name),
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
        embed.add_field(
            name="Aliases",
            value="\n".join(["\t{}".format(alias) for alias in command.aliases]),
            inline=False
        )
        # Add any paramaters needed
        if command.clean_params:
            required_params = [x for x in command.clean_params if "=" not in x]
            optional_params = [x for x in command.clean_params if "=" in x]
            name = "Paramaters"
            value = ""
            # Add the required params
            if required_params:
                value += "Requried:\n{}\n\n".format("\n".join(required_params))
            # Add the optional params
            if optional_params:
                value += "Optional:\n{}".format("\n".join(optional_params))
            embed.add_field(name=name, value=value, inline=False)
        # Set the description of the embed to the description
        if description:
            embed.description = description
        # Add these two in one embed
        if example and result:
            embed.add_field(
                name="Example",
                value="{}\n{}".format(example, result),
                inline=False
            )
        try:
            custom_perms = [func for func in command.checks if "custom_perms" in func.__qualname__][0]
            perms = ",".join(attribute for attribute, setting in custom_perms.perms.items() if setting)
            embed.set_footer(text="Permissions required: {}".format(perms))
        except IndexError:
            pass

        return embed



def setup(bot):
    bot.add_cog(Tutorial(bot))