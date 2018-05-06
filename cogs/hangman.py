import asyncio
import discord
import random
from utils.data import data
from discord.ext import commands
from bot import PikalaxBOT


class HangmanGame():
    def __init__(self, bot, attempts=8):
        self.bot = bot
        self._attempts = attempts
        self.reset()

    def reset(self):
        self._running = False
        self._state = ''
        self._solution = ''
        self._incorrect = []
        self.attempts = 0
        self._message = None

    @property
    def state(self):
        return ' '.join(self._state)

    @property
    def incorrect(self):
        return ', '.join(self._incorrect)

    @property
    def running(self):
        return self._running

    @running.setter
    def running(self, state):
        self._running = state

    def show(self):
        return f'```Puzzle: {self.state}\n' \
               f'Incorrect: [{self.incorrect}]\n' \
               f'Remaining: {self.attempts:d}```'

    async def start(self, ctx: commands.Context):
        if self.running:
            await ctx.author.send(f'Hangman is already running in {ctx.channel.mention}.')
        else:
            self._solution = random.choice(data.pokemon)
            self._state = ['_' for c in self._solution]
            self.attempts = self._attempts
            self._incorrect = []
            self.running = True
            await ctx.send(f'Hangman has started! You have {self.attempts:d} attempts to guess '
                           f'correctly before the man dies!')
            self._message = await ctx.send(f'{self.show()}')  # type: discord.Message

    async def end(self, ctx: commands.Context, failed=False, aborted=False):
        if self.running:
            await self._message.edit(content=f'{self.show()}')
            if aborted:
                await ctx.send(f'Game terminated by {ctx.author.mention}.\n'
                               f'Solution: {self._solution}')
            elif failed:
                await ctx.send(f'You were too late, the man has hanged to death.\n'
                               f'Solution: {self._solution}')
            else:
                await ctx.send(f'{ctx.author.mention} has solved the puzzle!\n'
                               f'Solution: {self._solution}')
            self.reset()
        else:
            await ctx.author.send(f'Hangman is not running in {ctx.channel.mention}.')

    async def guess(self, ctx: commands.Context, guess: str):
        if self.running:
            guess = guess.upper()
            if guess in self._incorrect or guess in self._state:
                await ctx.author.send(f'Character or solution already guessed: {guess}')
            elif len(guess) == 1:
                found = False
                for i, c in enumerate(self._solution):
                    if c == guess:
                        self._state[i] = guess
                        found = True
                if found:
                    if ''.join(self._state) == self._solution:
                        await self.end(ctx)
                else:
                    self._incorrect.append(guess)
                    self.attempts -= 1
            else:
                if self._solution == guess:
                    self._state = list(self._solution)
                    await self.end(ctx)
                else:
                    self._incorrect.append(guess)
                    self.attempts -= 1
            if self.running:
                await self._message.edit(content=f'{self.show()}')
                if self.attempts == 0:
                    await self.end(ctx, True)
        else:
            await ctx.author.send(f'Hangman is not running in {ctx.channel.mention}.')


class Hangman():
    def __init__(self, bot):
        self.bot = bot
        self.channels = {}

    @commands.group(pass_context=True)
    async def hangman(self, ctx):
        f"""Play Hangman"""
        if ctx.invoked_subcommand is None:
            await ctx.send(f'Incorrect hangman subcommand passed. Try {ctx.prefix}help game')
        if ctx.channel.id not in self.channels:
            self.channels[ctx.channel.id] = HangmanGame(self.bot)

    @hangman.command()
    async def start(self, ctx):
        """Start a game in the current channel"""
        await self.channels[ctx.channel.id].start(ctx)

    @hangman.command()
    async def guess(self, ctx, guess):
        """Make a guess, if you dare"""
        await self.channels[ctx.channel.id].guess(ctx, guess)

    @hangman.command()
    async def end(self, ctx):
        """End the game as a loss (owner only)"""
        if self.bot.is_owner(ctx.author):
            await self.channels[ctx.channel.id].end(ctx, aborted=True)


def setup(bot: PikalaxBOT):
    bot.add_cog(Hangman(bot))
