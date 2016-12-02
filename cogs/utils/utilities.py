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
        non_aliases = set(cmd.qualified_name for cmd in command.commands.values())
        for cmd_name in non_aliases:
            yield from _get_all_commands(command.commands[cmd_name])
    except AttributeError:
        pass
