# PikalaxBOT - A Discord bot in discord.py
# Copyright (C) 2018  PikalaxALT
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import aiohttp
import asyncio
from utils.botclass import PikalaxBOT, LoggingMixin


def has_client_session(ctx):
    return ctx.cog.cs is not None


class Cog(LoggingMixin):
    config_attrs = tuple()

    def __init__(self, bot):
        super().__init__()
        self.bot: PikalaxBOT = bot
        self.fetch()

    def fetch(self):
        self.log_debug(f'Fetching {self.__class__.__name__}')
        for attr in self.config_attrs:
            self.log_debug(attr)
            val = getattr(self.bot.settings, attr)
            if isinstance(val, list):
                val = set(val)
            setattr(self, attr, val)

    def commit(self):
        with self.bot.settings as settings:
            for attr in self.config_attrs:
                self.log_debug(attr)
                val = getattr(self, attr)
                if isinstance(val, set):
                    val = list(val)
                setattr(settings, attr, val)


class ClientSessionCog(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.cs: aiohttp.ClientSession = None
        self.bot.loop.create_task(self.get_cs())

    def __unload(self):
        task = self.bot.loop.create_task(self.cs.close())
        asyncio.wait([task], timeout=60)

    async def get_cs(self):
        await self.bot.wait_until_ready()
        self.cs = aiohttp.ClientSession(raise_for_status=True, loop=self.bot.loop)
