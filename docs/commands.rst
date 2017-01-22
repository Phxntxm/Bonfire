Commands
========

This should provide information on each command available to Bonfire.

.. note::
   By default the prefix used is either `?` or `!`, both work. However, this can
   be changed using the command :ref:'prefix'. Due to this, only the command name will
   be what is labeled when described. For example, if your prefix has been set to >
   and the command is `example` then it will be labeled as `example` in the documentation,
   however you would call the command using `>example`.

Core
----

.. data:: help

   .. note::
      Default permissions required: send_messages

   This command is used in order to bring up information about commands.
   It can be used in a few ways, by itsself to bring up an interactive list of all the
   commands. You can run also run it on another command, for example `help help` to 
   provide more information no that command. You can also run `help 5` to bring up the 
   5th page of the interactive menu.

.. data:: motd
   This command can be used to print the current MOTD (Message of the day). This will most likely 
   not be updated every day, however messages will still be pushed to this every now and then.
   The MOTD will be used as a sort of message board, and any updates to this will provide information
   about Bonfire.

.. data:: calendar
   Provides a printout of the current month's calendar
   Provide month and year to print the calendar of that year and month

.. data:: info
   Used to print out some information such as the total amount of servers Bonfire is on, amount of members,
   uptime, amount of different games running, etc.

.. data:: 
