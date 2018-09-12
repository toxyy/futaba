#
# cogs/journal/tracking.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

'''
Cog for journaling live API events such as username changes, users joining and leaving, etc.
'''

import asyncio
import logging

import discord
from discord.ext import commands

from futaba import permissions
from futaba.enums import Reactions

logger = logging.getLogger(__name__)

__all__ = [
    'LISTENERS',
    'Tracking',
]

LISTENERS = (
    'on_typing',
    'on_message',
    'on_message_edit',
    'on_message_delete',
    'on_reaction_add',
    'on_reaction_remove',
    'on_reaction_clear',
    'on_guild_channel_create',
    'on_guild_channel_delete',
)

def user_discrim(user):
    return f'{user.name}#{user.discriminator} ({user.id})'

class Tracking:
    __slots__ = (
        'bot',
        'journal',
    )

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster('/tracking')

    def __unload(self):
        '''
        Remove listeners when unloading the cog.
        '''

        for listener in LISTENERS:
            self.bot.remove_listener(getattr(self, listener), listener)

    async def on_typing(self, channel, user, when):
        if channel.guild is None:
            return

        logger.debug("Received typing event from %s (%d) in #%s (%d)",
                user.name, user.id, channel.name, channel.id)

        content = f'{user.name}#{user.discriminator} ({user.id}) is typing in {channel.mention}'
        self.journal.send('typing', channel.guild, content, icon='typing')

    async def on_message(self, message):
        if message.guild is None:
            return

        logger.debug("Received message from %s (%d) in #%s (%d)",
                message.author.name, message.author.id, message.channel.name, message.channel.id)

        content = f'{user_discrim(message.author)} sent a message in {message.channel.mention}'
        self.journal.send('message/new', message.guild, content, icon='message')

    async def on_message_edit(self, before, after):
        if after.guild is None:
            return

        logger.debug("Message %d by %s (%d) in #%s (%d) was edited",
                after.id, after.author.name, after.author.id, after.channel.name, after.channel.id)

        content = f'{user_discrim(after.author)} edited message {after.id} in {after.channel.mention}'
        self.journal.send('message/edit', after.guild, content, icon='edit')

    async def on_message_delete(self, message):
        if message.guild is None:
            return

        logger.debug("Message %d by %s (%d) was deleted", message.id, message.author.name, message.author.id)
        content = f'Message {message.id} by {user_discrim(message.author)} was deleted'
        self.journal.send('message/delete', message.guild, content, icon='delete')

    async def on_reaction_add(self, reaction, user):
        message = reaction.message
        channel = message.channel
        emoji = reaction.emoji

        if message.guild is None:
            return

        logger.debug("Reaction %s added to message %d by %s (%d)", emoji, message.id, user.name, user.id)
        content = f'{user_discrim(user)} added reaction {emoji} to message {message.id} in {channel.mention}'
        self.journal.send('reaction/add', message.guild, content, icon='item_add')

    async def on_reaction_remove(self, reaction, user):
        message = reaction.message
        channel = message.channel
        emoji = reaction.emoji

        if message.guild is None:
            return

        logger.debug("Reaction %s removed to message %d by %s (%d)", emoji, message.id, user.name, user.id)
        content = f'{user_discrim(user)} removed reaction {emoji} from message {message.id} in {channel.mention}'
        self.journal.send('reaction/remove', message.guild, content, icon='item_remove')

    async def on_reaction_clear(self, message, reactions):
        if message.guild is None:
            return

        logger.debug("All reactions from message %d were removed", message.id)
        content = f'All reactions on message {message.id} in {message.channel.mention} were removed'
        self.journal.send('reaction/clear', message.guild, content, icon='item_clear')

    async def on_guild_channel_create(self, channel):
        logger.debug("Channel #%s (%d) was created", channel.name, channel.id)
        content = f'Guild channel {channel.mention} created'
        self.journal.send('channel/new', channel.guild, content, icon='channel')

    async def on_guild_channel_delete(self, channel):
        logger.debug("Channel #%s (%d) was deleted", channel.name, channel.id)
        content = f'Guild channel #{channel.name} ({channel.id}) deleted'
        self.journal.send('channel/delete', channel.guild, content, icon='delete')
