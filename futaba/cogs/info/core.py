#
# cogs/info/core.py
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
Informational commands that make finding and gathering data easier.
'''

import asyncio
import logging
from collections import Counter
from itertools import islice

import discord
from discord.ext import commands

from futaba.enums import Reactions
from futaba.parse import get_role_id, get_user_id, similar_user_ids
from futaba.permissions import check_mod_perm
from futaba.utils import escape_backticks, fancy_timedelta, first, plural

logger = logging.getLogger(__package__)

__all__ = [
    'Info',
]

class Info:
    '''
    Cog for informational commands.
    '''

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='uinfo', aliases=['userinfo'])
    async def uinfo(self, ctx, *, name: str = None):
        '''
        Fetch information about a user, whether they are in the guild or not.
        If no argument is passed, the caller is checked instead.
        '''

        if name is None:
            name = str(ctx.message.author.id)

        logger.info("Running uinfo on '%s'", name)

        id = get_user_id(name, self.bot.users)
        if id is None:
            logger.debug("No user ID found!")
            await Reactions.FAIL.add(ctx.message)
            return

        logger.debug("Fetched user ID is %d", id)

        user = None
        if ctx.guild is not None:
            user = ctx.guild.get_member(id)

        if user is None:
            user = self.bot.get_user(id)
            if user is None:
                user = await self.bot.get_user_info(id)
                if user is None:
                    logger.debug("No user with that ID found!")
                    await Reactions.FAIL.add(ctx.message)
                    return

        logger.debug("Found user! %r", user)

        # Status
        if getattr(user, 'status', None):
            status = 'do not disturb' if user.status == discord.Status.dnd else user.status
            descr = f'{user.mention}, {status}'
        else:
            descr = user.mention

        embed = discord.Embed(description=descr)
        embed.timestamp = user.created_at
        embed.set_author(name=f'{user.name}#{user.discriminator}')
        embed.set_thumbnail(url=user.avatar_url)

        # User colour
        if hasattr(user, 'colour'):
            embed.colour = user.colour

        # User id
        embed.add_field(name='ID', value=f'`{user.id}`')

        # Roles
        if getattr(user, 'roles', None):
            roles = ' '.join(role.mention for role in islice(user.roles, 1, len(user.roles)))
            if roles:
                embed.add_field(name='Roles', value=roles)

        # Current game
        if getattr(user, 'activity', None):
            act = user.activity
            if isinstance(act, discord.Game):
                if act.start is None:
                    if act.end is None:
                        time_msg = ''
                    else:
                        time_msg = f'until {act.end}'
                else:
                    if act.end is None:
                        time_msg = f'since {act.start}'
                    else:
                        time_msg = f'from {act.start} to {act.end}'

                embed.description += f'\nPlaying `{act.name}` {time_msg}'
            elif isinstance(act, discord.Streaming):
                embed.description += f'\nStreaming [{act.name}]({act.url})'
                if act.details is not None:
                    embed.description += f'\n{act.details}'
            elif isinstance(act, discord.Activity):
                embed.description += '\n{act.state} [{act.name}]({act.url})'

        # Voice activity
        if getattr(user, 'voice', None):
            mute = user.voice.mute or user.voice.self_mute
            deaf = user.voice.deaf or user.voice.self_deaf

            states = []
            if mute:
                states.append('muted')
            if deaf:
                states.append('deafened')

            if states:
                state = ', '.join(states)
            else:
                state = 'active'

            embed.add_field(name='Voice', value=state)

        # Guild join date
        if hasattr(user, 'joined_at'):
            embed.add_field(name='Member for', value=fancy_timedelta(user.joined_at))

        # Discord join date
        embed.add_field(name='Account age', value=fancy_timedelta(user.created_at))

        # Send them
        await asyncio.gather(
            Reactions.SUCCESS.add(ctx.message),
            ctx.send(embed=embed),
        )

    @commands.command(name='ufind', aliases=['userfind', 'usearch', 'usersearch'])
    async def ufind(self, ctx, *, name: str):
        '''
        Perform a fuzzy search to find users who match the given name.
        They are listed with the closest matches first.
        '''

        logger.info("Running ufind on '%s'", name)
        user_ids = similar_user_ids(name, self.bot.users)
        users_in_guild = set(member.id for member in getattr(ctx.guild, 'members', []))

        lines = ['**Users found:**']
        for user_id in user_ids:
            user = self.bot.get_user(user_id)
            if user is None:
                user = await self.bot.get_user_info(user_id)

            logger.debug("Result for user ID %d: %r", user_id, user)
            if user is not None:
                extra = '' if user_id in users_in_guild else '\N{GLOBE WITH MERIDIANS}'
                lines.append(f'- {user.mention} {extra}')

        if len(lines) > 1:
            descr = '\n'.join(lines)
            colour = discord.Colour.teal()
        else:
            descr = '**No users found!**'
            colour = discord.Colour.dark_red()

        embed = discord.Embed(description=descr, colour=colour)
        await asyncio.gather(
            ctx.send(embed=embed),
            Reactions.SUCCESS.add(ctx.message),
        )

    @commands.command(name='rinfo', aliases=['roleinfo', 'role'])
    @commands.guild_only()
    async def rinfo(self, ctx, *, name: str = None):
        '''
        Fetches and prints information about a particular role in the current guild.
        If no role is specified, it displays information about the default role.
        '''

        if name in (None, '@everyone', 'everyone', '@here', 'here', 'default'):
            role = ctx.guild.default_role
        else:
            id = get_role_id(name, ctx.guild.roles)
            if id is None:
                role = None
            else:
                role = discord.utils.get(ctx.guild.roles, id=id)

        if role is None:
            await Reactions.FAIL.add(ctx.message)
            return

        logger.info("Running rinfo on '%s'", role)

        embed = discord.Embed(colour=role.colour)
        embed.timestamp = role.created_at
        embed.add_field(name='ID', value=str(role.id))
        embed.add_field(name='Position', value=str(role.position))

        lines = [role.mention]
        if role.mentionable:
            lines.append('Mentionable')
        if role.hoist:
            lines.append('Hoisted')
        if role.managed:
            lines.append('Managed')
        embed.description = '\n'.join(lines)

        if role.members:
            max_members = 15
            members = ", ".join(map(lambda m: m.mention, islice(role.members, 0, max_members)))
            if len(role.members) > max_members:
                diff = len(role.members) - max_members
                members += f' (and {diff} other{plural(diff)})'
        else:
            members = '(none)'

        embed.add_field(name='Members', value=members)

        await asyncio.gather(
            ctx.send(embed=embed),
            Reactions.SUCCESS.add(ctx.message),
        )

    @commands.command(name='roles', aliases=['lroles', 'listroles'])
    @commands.guild_only()
    async def roles(self, ctx):
        ''' Lists all roles in the guild. '''

        contents = []
        lines = []
        current_len = 0

        logger.info("Listing roles within the guild")
        for role in ctx.guild.roles:
            line = f'- {role.mention} id: `{role.id}`, members: `{len(role.members)}`'
            current_len += len(line)

            if current_len > 1900:
                # Too long, break into new embed
                contents.append('\n'.join(lines))

                # Start lines over
                lines.clear()
                lines.append(line)
                current_len = len(line)
            else:
                lines.append(line)

        contents.append('\n'.join(lines))
        lines.clear()

        async def post_all():
            for i, content in enumerate(contents):
                embed = discord.Embed(description=content)
                page = f'Page {i + 1}/{len(contents)}'
                if i == 0:
                    embed.set_author(name=page)
                else:
                    embed.set_author(name=f'{page} Roles in {ctx.guild.name}')

                await ctx.send(embed=embed)

        await asyncio.gather(
            post_all(),
            Reactions.SUCCESS.add(ctx.message),
        )

    @staticmethod
    async def get_messages(channels, ids):
        return await asyncio.gather(*[Info.get_message(channels, id) for id in ids])

    @staticmethod
    async def get_message(channels, id):
        async def from_channel(channel, id):
            try:
                return await channel.get_message(id)
            except discord.NotFound:
                return None

        results = await asyncio.gather(*[from_channel(channel, id) for channel in channels])
        return first(results)

    @commands.command(name='message', aliases=['findmsg', 'msg'])
    @commands.guild_only()
    async def message(self, ctx, *ids: int):
        '''
        Finds and prints the contents of the messages with the given IDs.
        '''

        logger.info("Finding message IDs for dump: %s", ids)

        if not check_mod_perm(ctx) and len(ids) > 3:
            ids = islice(ids, 0, 3)
            await ctx.send(content='Too many messages requested, stopping at 3...')

        def make_embed(message, id):
            if message is None:
                embed = discord.Embed(colour=discord.Colour.dark_red())
                embed.description = f'No message with id `{id}` found'
                embed.timestamp = discord.utils.snowflake_time(id)
            else:
                embed = discord.Embed(colour=message.author.colour)
                embed.description = message.content or None
                embed.timestamp = message.created_at
                embed.url = message.jump_url
                embed.set_author(name=f'{message.author.name}#{message.author.discriminator}')
                embed.set_thumbnail(url=message.author.avatar_url)
                embed.add_field(name='Sent by', value=message.author.mention)

                if ctx.guild is not None:
                    embed.add_field(name='Channel', value=message.channel.mention)

                embed.add_field(name='Permalink', value=message.jump_url)

                if message.edited_at is not None:
                    delta = fancy_timedelta(message.edited_at - message.created_at)
                    embed.add_field(name='Edited at', value=f'`{message.edited_at}` ({delta} afterwords)')

                if message.attachments:
                    embed.add_field(name='Attachments', value='\n'.join(
                        attach.url for attach in message.attachments
                    ))

                if message.embeds:
                    embed.add_field(name='Embeds', value=str(len(message.embeds)))

                if message.reactions:
                    emojis = Counter()
                    for reaction in message.reactions:
                        emojis[str(reaction.emoji)] += 1

                    embed.add_field(name='Reactions', value='\n'.join((
                        f'{count}: {emoji}' for emoji, count in emojis.items()
                    )))

            return embed

        messages = await self.get_messages(ctx.guild.text_channels, ids)
        for message, id in zip(messages, ids):
            await ctx.send(embed=make_embed(message, id))

        await Reactions.SUCCESS.add(ctx.message)

    @commands.command(name='rawmessage', aliases=['raw', 'rawmsg'])
    @commands.guild_only()
    async def raw_message(self, ctx, *ids: int):
        '''
        Finds and prints the raw contents of the messages with the given IDs.
        '''

        logger.info("Finding message IDs for raws: %s", ids)

        if not check_mod_perm(ctx) and len(ids) > 5:
            ids = islice(ids, 0, 5)
            await ctx.send(content='Too many messages requested, stopping at 5...')

        messages = await self.get_messages(ctx.guild.text_channels, ids)
        for message in messages:
            await ctx.send(content='\n'.join((
                f'{message.author.name}#{message.author.discriminator} sent:',
                '```',
                escape_backticks(message.content),
                '```',
            )))

        await Reactions.SUCCESS.add(ctx.message)

    @commands.command(name='embeds')
    @commands.guild_only()
    async def embeds(self, ctx, id: int):
        '''
        Finds and copies embeds from the given message.
        '''

        logger.info("Copying embeds from message %d", id)
        message = await self.get_message(ctx.guild.text_channels, id)
        if message is None:
            logger.debug("No message with this id found")
            embed = discord.Embed(colour=discord.Colour.dark_red())
            embed.description = f'No message with id `{id}` found'
            await asyncio.gather(
                ctx.send(embed=embed),
                Reactions.FAIL.add(ctx.message),
            )
            return

        if not message.embeds:
            logger.debug("This message does not have any embeds")
            embed = discord.Embed(colour=discord.Colour.teal())
            embed.description = 'This message contains no embeds.'
            await asyncio.gather(
                ctx.send(embed=embed),
                Reactions.SUCCESS.add(ctx.message),
            )
            return

        for i, embed in enumerate(message.embeds, 1):
            await ctx.send(content=f'#{i}:', embed=embed)

        await Reactions.SUCCESS.add(ctx.message)

    @commands.command(name='ginfo', aliases=['guildinfo'])
    @commands.guild_only()
    async def ginfo(self, ctx):
        ''' Gets information about the current guild. '''

        embed = discord.Embed()
        embed.timestamp = ctx.guild.created_at
        embed.set_author(name=ctx.guild.name)
        embed.set_thumbnail(url=ctx.guild.icon_url)

        lines = [
            f'\N{MAN} **Members:** {len(ctx.guild.members)}',
            f'\N{MILITARY MEDAL} **Roles:** {len(ctx.guild.roles)}',
            f'\N{BAR CHART} **Channel categories:** {len(ctx.guild.categories)}',
            f'\N{MEMO} **Text Channels:** {len(ctx.guild.text_channels)}',
            f'\N{STUDIO MICROPHONE} **Voice Channels:** {len(ctx.guild.voice_channels)}',
            f'\N{CLOCK FACE TWO OCLOCK} **Age:** {fancy_timedelta(ctx.guild.created_at)}',
            ''
        ]

        moderators = 0
        admins = 0
        bots = 0

        # Do a single loop instead of generator expressions
        for member in ctx.guild.members:
            if member.bot:
                bots += 1

            perms = member.permissions_in(ctx.channel)
            if perms.administrator:
                admins += 1
            elif perms.manage_messages:
                moderators += 1

        if bots:
            lines.append(f'\N{ROBOT FACE} **Bots:** {bots}')
        if moderators:
            lines.append(f'\N{CONSTRUCTION WORKER} **Moderators:** {moderators}')
        if admins:
            lines.append(f'\N{POLICE OFFICER} **Administrators:** {admins}')
        lines.append(f'\N{CROWN} **Owner:** {ctx.guild.owner.mention}')

        embed.description = '\n'.join(lines)

        await asyncio.gather(
            ctx.send(embed=embed),
            Reactions.SUCCESS.add(ctx.message),
        )