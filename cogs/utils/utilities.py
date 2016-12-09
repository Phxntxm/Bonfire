def get_all_commands(bot):
    # First lets create a set of all the parent names
    parent_command_names = set(cmd.qualified_name for cmd in bot.commands.values())
    all_commands = []

    # Now lets loop through and get all the child commands for each command
    # Only the command itself will be yielded if there are no children
    for cmd_name in parent_command_names:
        cmd = bot.commands.get(cmd_name)
        for child_cmd in _get_all_commands(cmd):
            all_commands.append(child_cmd)

    return all_commands

def _get_all_commands(command):
    yield command.qualified_name
    try:
        non_aliases = set(cmd.name for cmd in command.commands.values())
        for cmd_name in non_aliases:
            yield from _get_all_commands(command.commands[cmd_name])
    except AttributeError:
        pass

def find_command(bot, command):
    # This method ensures the command given is valid. We need to loop through commands
    # As bot.commands only includes parent commands
    # So we are splitting the command in parts, looping through the commands
    # And getting the subcommand based on the next part
    # If we try to access commands of a command that isn't a group
    # We'll hit an AttributeError, meaning an invalid command was given
    # If we loop through and don't find anything, cmd will still be None
    # And we'll report an invalid was given as well
    cmd = None

    for part in command.split():
        try:
            if cmd is None:
                cmd = bot.commands.get(part)
            else:
                cmd = cmd.commands.get(part)
        except AttributeError:
            cmd = None
            break

    return cmd
