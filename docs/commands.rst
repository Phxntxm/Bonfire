Commands
========

This provides information on each command available to Bonfire.

.. note::
   By default the prefix used is either `?` or `!`, both work. However, this can
   be changed using the command 'prefix'. Due to this, only the command name will
   be what is labeled when described. For example, if your prefix has been set to >
   and the command is `example` then it will be labeled as `example` in the documentation,
   however you would call the command using `>example`.

.. note::
   Command usability is based on permissions, to run a command you need to have a certain permission.
   Each command will label what permission is required, by default, to run the command. You can manage
   custom permissions for a server with the command `perms`.

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

Interaction
-----------

.. data:: hug

   Causes Bonfire to hug a person

   - Default permissions required: send_message

.. data:: avatar

   Posts the full image of a provided person's avatar

   - Default permissions required: send_message

.. data:: battle

   Challenges the provided player to a battle

   - Default permissions required: send_message
   - Cooldown, per member, for 3 minutes

.. data:: accept

   Accepts the challenger's battle

   - Default permissions required: send_message

.. data:: decline

   Declines the challenger's battle

   - Default permissions required: send_message

.. data:: boop

   Boops the provided person

   - Default permissions required: send_message

Music
-----

.. data:: progress

   Prints the progress of the curent song

   - Default permissions required: send_message

.. data:: join

   Causes Bonfire to join the provided channel

   - Default permissions required: send_message

.. data:: summon

   Causes Bonfire to join the channel you are in


   - Default permissions required: send_message

.. data:: play

   Plays a song; you can provide a link to a song or search terms, and youtube will be searched.
   
   - Default permissions required: send_message
   - Playlists, live streams, and soundcloud cannot be used
   - 10 songs can be queued at a time

.. data:: volume

   Sets the volume of the bot to a provided number

   - Default permissions required: kick_members
   - The number needs to be between 0 and 200

.. data:: pause

   Pauses the current song

   - Default permissions required: kick_members

.. data:: resume

   Resumes the current song

   - Default permissions required: kick_members

.. data:: stop

   Stops playing songs, and causes Bonfire to leave her voice channel

   - Default permissions required: kick_members

.. data:: eta

   Provides an ETA on when your next song will play

   - Default permissions required: send_message

.. data:: queue

   Prints out the songs currently in the queue

   - Default permissions required: send_message

.. data:: skip

   Vote to skip a song. The song requester can automatically skip.
   approximately 1/3 of the members in the voice channel
   are required to vote to skip for the song to be skipped.

   - Default permissions required: send_message

.. data:: modskip

   Force skips a song

   - Default permissions required: kick_members

.. data:: playing

   Displays some information about the current song playing

   - Default permissions required: send_message

Moderator Utilities
-------------------

.. data:: nickname

   Changes Bonfire's nickname on the server

   - Default permissions required: kick_members
   - Aliases `nick`

.. data:: kick

   Kicks a member from the server

   - Default permissions required: kick_members

.. data:: ban

   Bans a member from the server. For this you can provide a member, or their ID.
   This is useful in cases where you want to ban someone preemptively from the server

   - Default permissions required: ban_members

.. data:: unban

   Unbans a member from the server; the ID must be provided to unban a member.

   - Default permissions required: ban_members

.. data:: alerts

   This is used to set a certain channel as the server's notifications channel.
   Notifications such as someone going live on twitch or picarto go to this channel.

   - Default permissions required: kick_members

.. data:: usernotify
   
   Turns user notification on or off for the server; provide either on or off to change this.
   This will set the channel that the command is ran in as the channel for these notifications

   - Default permissions required: kick_members

.. data:: nsfw add

   Adds the current channel as a nsfw channel

   - Default permissions required: kick_members

.. data:: nsfw remove

   Removes the current channel as a nsfw channel

   - Default permissions required: kick_members
   - Aliases `delete`

.. data:: say

   Causes the bot to say whatever you provide

   - Default permissions required: kick_members

.. data:: perms

   Prints a message providing all possible permissions. This can be used to help with custom
   permission settings.

   - Default permissions required: send_messages

.. data:: perms add

   Sets custom permissions for a provided command. Format must be 'perms add <command> <permission>'
   If you want to open the command to everyone, provide 'none' as the permission

   - Default permissions required: manage_server
   - Aliases `setup, create`

.. data:: perms remove
   
   Removes the custom permissions setup on a command

   - Default permissions required: manage_server
   - Aliases `delete`

.. data:: prefix

   Used to setup a custom prefix for this server

   - Default permissions required: manage_server

.. data:: purge

   Purges the channel of a specified number of messages. By default this is 100

   - Default permissions required: manage_messages

.. data:: prune

   Prunes the channel from specified members, based on the number provided. The number 
   must be provided by the members. If no members are provided, Bonfire's messages are assumed

   - Default permissions required: manage_messages

.. data:: rules

   Prints out the rules setup on the server. By default will print out all rules; if you provide
   a number it will print that rule

   - Default permissions required: send_messages
   - Aliases `rule`

.. data:: rules add

   Adds the specified rule to the list of server's rules.

   - Default permissions required: manage_server
   - Aliases `rules create, rule create, rule add`

.. data:: rules remove
   
   Deletes a specified rule from the server; the rule deleted needs to be specified by the number.

   - Default permissions required: manage_server
   - Aliases `rules delete, rule delete, rules remove`

Stats
-----

.. data:: serverinfo

   Provide 'me' to print a leaderboard for your own usageProvides some information about the server

   - Default permissions required: send_messages

.. data:: command stats

   This command can be used to view some usage stats about a specific command

   - Default permissions required: send_messages

.. data:: command leaderboard

   This command can be used to print a leaderboard of commands. 
   Provide 'server' to print a leaderboard for this server. 
   Provide 'me' to print a leaderboard for your own usage

   - Default permissions required: send_messages

.. data:: mostboops

   Shows you the person you have booped the most, as well as how many times

   - Default permissions required: send_messages

.. data:: listboops

   Provides a list of all the users you have booped and the amount of times

   - Default permissions required: send_messages

.. data:: leaderboard

   Provides a leaderboard of this server's battle records

   - Default permissions required: send_messages

.. data:: stats
   
   Provides battle stats about the person provided, defaulting to you

   - Default permissions required: send_messages

Blackjack
---------

.. data:: blackjack

   Starts a game of blackjack; if a game is already running joins the current game of blackjack.
   This is to be played like normal blackjack, and the rest of the usage for this is prompt based.
   Bonfire will prompt at different stages of the game (i.e. hit or stand, what do you want to bet, etc.)

   - Default permissions required: send_messages

.. data:: blackjack leave

   Leaves the current game of blackjack

   - Default permissions required: send_messages

.. data:: blackjack stop

   Stops the current game of blackjack.

   .. note::
      Think of this as a completely normal table of blackjack, the person
      who started the game cannot end it, it will continue even if they leave, as long as their are players.
      That is why this is restricted to someone who can manage the server, as it should only be used in case
      people have gone afk and the game is still running, which can get annoying.

   - Default permissions required: manage_server

DeviantArt
----------

.. data:: da sub

   This can be used to add a feed to your notifications. Provide a username, and when posts are made
   from this user, you will be notified.

   - Default permissions required: send_messages
   - Aliases `add, subscribe`

.. data:: da unsub

   This command can be used to unsubscribe from the specified user

   - Default permissions required: send_messages
   - Aliases `delete, remove, unsubscribe`

Hangman
-------

.. data:: hangman

   Makes a guess towards the server's currently running hangman game. A letter or the phrase can be guessed
 
   - Default permissions required: send_messages
   - Aliases `hm`

.. data:: hangman start

   Starts a new game of hangman. A predefined phrase will be randomly chosen as the phrase to use

   - Default permissions required: send_messages
   - Aliases `hangman create, hm start, hm create`

.. data:: hangman stop

   Force stops a game of hangman.

   - Default permissions required: kick_members
   - Aliases `hangman delete, hangman end, hangman remove, hm stop, hm delete, hm remove, hm end`

Overwatch
---------

.. data:: ow stats

   Provides a basic overview of a member's stats. By default the member used is the author; to lookup hero
   specific stats, provide the hero after the  member to look up.

   - Default permissions required: send_messages

.. data:: ow add

   Saves your provided battletag to your user, for lookup later. Format for a battletag is Username#1234

   - Default permissions required: send_messages

.. data:: ow delete

   Unlinks your saved battletag from your user

   - Default permissions required: send_messages
   - Aliases `ow remove`
