#
# cogs/settings/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .core import SettingsCog

def setup(bot):
    '''
    Setup for bot to add cog
    '''

    cog = SettingsCog(bot)
    bot.add_cog(cog)
