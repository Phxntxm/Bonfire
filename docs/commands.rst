Commands
========

This provides information on each command available to Bonfire.

.. note::
   By default the prefix used is either `?` or `!`, both work. However, this can
   be changed using the command 'prefix'. Due to this, only the command name will
   be what is labeled when described. For example, if your prefix has been set to >
   and the command is `example` then it will be labeled as `example` in the documentation,
   however you would call the command using `>example`.

Core
----

.. data:: help

   - Default permissions required: send_messages

   This command is used in order to bring up information about commands.
   It can be used in a few ways, by itsself to bring up an interactive list of all the
   commands. You can run also run it on another command, for example `help help` to 
   provide more information no that command. You can also run `help 5` to bring up the 
   5th page of the interactive menu.

.. data:: motd

   - Default permissions required: send_messages

   This command can be used to print the current MOTD (Message of the day). This will most likely 
   not be updated every day, however messages will still be pushed to this every now and then.
   The MOTD will be used as a sort of message board, and any updates to this will provide information
   about Bonfire.

.. data:: calendar

   - Default permissions required: send_messages

   Provides a printout of the current month's calendar
   Provide month and year to print the calendar of that year and month

.. data:: info

   - Default permissions required: send_messages

   Used to print out some information such as the total amount of servers Bonfire is on, amount of members,
   uptime, amount of different games running, etc.

.. data:: uptime

   - Default permissions required: send_messages

   Provides a printout of the current bot's uptime

.. data:: addbot

   - Default permissions required: send_messages
   - Aliases: `invite`

   Provides a link that can be used to add Bonfire to a server

   -- note::
      You need to have manage server permissions in a server to add a bot to that server

.. data:: doggo

   - Default permissions required: send_messages

   Prints a random doggo image

.. data:: snek

   - Default permissions required: send_messages

   Prints a random snek image

.. data:: joke

   - Default permissions required: send_messages

   Prints a random joke

.. data:: roll

   - Default permissions required: send_messages
   - Maximum number of dice (first number): 10
   - Maximum number of sides (second number): 100

   Rolls a die based on the notation given. Notation needs to be in #d#, for example 5d5.
   You can ignore the first number, and only 1 die will be rolled, for example d50
