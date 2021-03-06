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

import asyncio
import discord
import aiohttp
import random
from discord.ext import commands
from utils.data import data
from cogs import ClientSessionCog, has_client_session


class HMM:
    def __init__(self, transition, emission):
        self.transition = transition
        self.emission = emission
        self.state = 0

    @property
    def n_states(self):
        return len(self.transition)

    def emit(self):
        res = self.emission[self.state]
        self.state, = random.choices(range(self.n_states), weights=self.transition[self.state])
        return res

    def get_chain(self, length, start=0, end=-1):
        self.state = start
        for i in range(length):
            yield self.emit()
            if self.state == end:
                break


class Meme(ClientSessionCog):
    _nebby = HMM(
        [[0, 1, 0, 0, 0],
         [1, 2, 1, 0, 0],
         [0, 0, 1, 1, 0],
         [0, 0, 0, 1, 9],
         [0, 0, 0, 0, 1]],
        'pew! '
    )

    def __unload(self):
        task = self.bot.loop.create_task(self.cs.close())
        asyncio.wait([task], timeout=60)

    @commands.command()
    @commands.check(has_client_session)
    async def archeops(self, ctx, subj1: str = '', subj2: str = ''):
        """Generates a random paragraph using <arg1> and <arg2> as subject keywords, using the WatchOut4Snakes frontend.
        """
        data = {'Subject1': subj1, 'Subject2': subj2}
        r = await self.cs.post('http://www.watchout4snakes.com/wo4snakes/Random/RandomParagraph', data=data)
        res = await r.text()
        await ctx.send(res)

    @commands.command()
    async def riot(self, ctx, *args):
        """Riots (for some reason)"""
        resp = ' '.join(args).upper()
        if 'DANCE' in resp:
            await ctx.send(f'♫ ┌༼ຈل͜ຈ༽┘ ♪ {resp} RIOT ♪ └༼ຈل͜ຈ༽┐♫')
        else:
            await ctx.send(f'ヽ༼ຈل͜ຈ༽ﾉ {resp} RIOT ヽ༼ຈل͜ຈ༽ﾉ')

    @commands.command()
    async def nebby(self, ctx):
        """Pew!"""
        emission = ''.join(self._nebby.get_chain(100, end=4)).title()
        await ctx.send(emission)

    @commands.command()
    async def yolonome(self, ctx):
        """Happy birthday, Waggle!"""
        await ctx.send(f'{ctx.author.mention} used Metronome!\n'
                       f'Waggling a finger allowed it to use {data.random_move_name()}!')

    @commands.command()
    async def olden(self, ctx):
        await ctx.send('https://vignette.wikia.nocookie.net/twitchplayspokemoncrystal/images/5/5f/'
                       'Serious_%22OLDEN%22_Times.png/revision/latest?cb=20160820193335')
      
    @commands.command()
    async def song(self, ctx, *args):
        """Copypasta based on the Donger Song"""
        resp = ' '.join(args)
        await ctx.send(f"I like to raise my {resp} I do it all the time ヽ༼ຈل͜ຈ༽ﾉ and every time its lowered┌༼ຈل͜ຈ༽┐ I cry and start to whine ┌༼@ل͜@༽┐But never need to worry ༼ ºل͟º༽ my {resp}'s staying strong ヽ༼ຈل͜ຈ༽ﾉA {resp} saved is a {resp} earned so sing the {resp} song! ᕦ༼ຈل͜ຈ༽ᕤ")

    @commands.command()
    async def rip(self, ctx, *args):
        """Pays respects to <stuff>"""
        resp = ' '.join(args)
        await ctx.send(f'RIP {resp}. Press F to pay your respects.")
                       
def setup(bot):
    bot.add_cog(Meme(bot))
