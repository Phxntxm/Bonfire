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

   This command is used in order to bring up information about commands.
   It can be used in a few ways, by itsself to bring up an interactive list of all the
   commands. You can run also run it on another command, for example `help help` to 
   provide more information no that command. You can also run `help 5` to bring up the 
   5th page of the interactive menu.

   - Default permissions required: send_messages

.. data:: motd

   This command can be used to print the current MOTD (Message of the day). This will most likely 
   not be updated every day, however messages will still be pushed to this every now and then.
   The MOTD will be used as a sort of message board, and any updates to this will provide information
   about Bonfire.

   - Default permissions required: send_messages

.. data:: calendar

   Provides a printout of the current month's calendar
   Provide month and year to print the calendar of that year and month

   - Default permissions required: send_messages

.. data:: info

   Used to print out some information such as the total amount of servers Bonfire is on, amount of members,
   uptime, amount of different games running, etc.

   - Default permissions required: send_messages

.. data:: uptime

   Provides a printout of the current bot's uptime

   - Default permissions required: send_messages

.. data:: addbot

   Provides a link that can be used to add Bonfire to a server

   .. note::
      You need to have manage server permissions in a server to add a bot to that server

   - Default permissions required: send_messages
   - Aliases: `invite`

.. data:: doggo

   Prints a random doggo image

   - Default permissions required: send_messages

.. data:: snek

   Prints a random snek image

   - Default permissions required: send_messages

.. data:: joke

   Prints a random joke

   - Default permissions required: send_messages

.. data:: roll

   Rolls a die based on the notation given. Notation needs to be in #d#, for example 5d5.
   You can ignore the first number, and only 1 die will be rolled, for example d50

   - Default permissions required: send_messages
   - Maximum number of dice (first number): 10
   - Maximum number of sides (second number): 100

Links
-----

.. data:: google

   Searches google for a provided query

   - Default permissions required: send_message
   - Aliases: `g`
   - Safe search will be turned on or off based on whether the channel used is a nsfw channel or not

.. data:: youtube

   Searched youtube for a provided query

   - Default permissions required: send_message
   - Aliases: `yt`

.. data:: wiki

   Pulls the top match for a specific term from wikipedia, and returns the result

   - Default permissions required: send_message

.. data:: urban

   Pulls the top urbandictionary.com definition for a term

   - Default permissions required: send_message

.. data:: derpi

   Provides an image from derpibooru. Provide search times, separated by commands, to 
   search for an image. Provide no search time and a completely random image will be pulled

   - Default permissions required: send_message
   - If this is used in a nsfw channel this will query for suggestive/explicit pics. Otherwise
     It will pull a safe picture

.. data:: e621

   Provides an image from e621. Provide search times, separated by commands, to
   search for an image.

   - Default permissions required: send_message
   - If this is used in a nsfw channel this will query for suggestive/explicit pics. Otherwise
     It will pull a safe picture

