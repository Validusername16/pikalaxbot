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
import traceback
import youtube_dl
import ctypes.util
from discord.ext import commands
from utils.botclass import PikalaxBOT
from utils.default_cog import Cog
import subprocess
import os
import time
import re
from concurrent.futures import ThreadPoolExecutor


class VoiceCommandError(commands.CommandError):
    """This is raised when an error occurs in a voice command."""


class cleaner_content(commands.clean_content):
    async def convert(self, ctx, argument):
        argument = await super().convert(ctx, argument)
        argument = re.sub(r'<a?:(\w+):\d+>', '\\1', argument)
        return argument


def connected_and_not_playing(ctx):
    vc = ctx.voice_client
    return vc is not None and vc.is_connected() and not vc.is_playing()


class EspeakParamsConverter(commands.Converter):
    def __init__(self, **valid_keys):
        """Converts key=value pairs to a 2ple
        valid_keys: name=type pairs
        """
        super().__init__()
        self.valid_keys = valid_keys

    async def convert(self, ctx, argument):
        if isinstance(argument, str):
            # Convert from a string
            key, value = argument.split('=')
            value = self.valid_keys[key](value)
        else:
            # Make sure this is an iterable of length 2
            key, value = argument
        return key, value


class EspeakAudioSource(discord.FFmpegPCMAudio):
    @staticmethod
    def call_espeak(msg, fname, **kwargs):
        args = ['espeak', '-w', fname]
        for flag, value in kwargs.items():
            args.extend([f'-{flag}', str(value)])
        args.append(msg)
        subprocess.check_call(args)

    def __init__(self, cog, msg, *args, **kwargs):
        self.fname = f'tmp_{time.time()}.wav'
        self.call_espeak(msg, self.fname, **cog.espeak_kw)
        super().__init__(self.fname, *args, **kwargs)

    def cleanup(self):
        super().cleanup()
        if os.path.exists(self.fname):
            os.remove(self.fname)


class YouTube(Cog):
    __ytdl_format_options = {
        'format': 'bestaudio/best',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
    }
    __ffmpeg_options = {
        'before_options': '-nostdin -loglevel quiet',
        'options': '-vn'
    }
    espeak_kw = {}
    voice_chans = {}
    config_attrs = 'espeak_kw', 'voice_chans'
    __espeak_valid_keys = {
        'a': int,
        's': int,
        'v': str,
        'p': int,
        'g': int,
        'k': int
    }

    def __local_check(self, ctx):
        return self.ready

    def load_opus(self):
        if not discord.opus.is_loaded():
            opus_name = ctypes.util.find_library('libopus')
            if opus_name is None:
                self.bot.logger.error('Failed to find the Opus library.')
            else:
                discord.opus.load_opus(opus_name)
        return discord.opus.is_loaded()

    def __init__(self, bot: PikalaxBOT):
        super().__init__(bot)
        self.ready = False
        self.connections = {}

        with open(os.devnull, 'w') as DEVNULL:
            for executable in ('ffmpeg', 'avconv'):
                try:
                    subprocess.check_call([executable, '-h'], stdout=DEVNULL, stderr=DEVNULL)
                except FileNotFoundError:
                    continue
                self.ffmpeg = executable
                self.__ffmpeg_options['executable'] = executable
                break
            else:
                raise discord.ClientException('ffmpeg or avconv not installed')

        self.executor = ThreadPoolExecutor()
        self.__ytdl_player = youtube_dl.YoutubeDL(self.__ytdl_format_options)

    async def on_ready(self):
        if self.load_opus():
            self.bot.logger.info('Loaded opus')
            for guild, chan in self.voice_chans.items():
                ch = self.bot.get_channel(chan)
                if isinstance(ch, discord.VoiceChannel):
                    try:
                        await ch.connect()
                    except asyncio.TimeoutError:
                        self.bot.logger.error('Failed to connect to voice channel %s (connection timed out)', ch.name)
                    except discord.ClientException:
                        self.bot.logger.error('Failed to connect to voice channel %s (duplicate connection)', ch.name)
                    else:
                        self.bot.logger.info('Connected to voice channel %s', ch.name)

            self.ready = True

    @commands.group()
    # @commands.is_owner()
    async def pikavoice(self, ctx: commands.Context):
        """Commands for interacting with the bot in voice channels"""
        if ctx.invoked_subcommand is None:
            raise commands.CommandInvokeError('Invalid subcommand')

    @pikavoice.command()
    @commands.is_owner()
    async def chan(self, ctx: commands.Context, ch: discord.VoiceChannel):
        """Join a voice channel on the current server."""

        # All errors shall be communicated to the user, and also
        # passed to the bot's on_command_error handler.
        async with ctx.channel.typing():
            if ch is None:
                raise VoiceCommandError('Channel not found')
            if not ctx.me.permissions_in(ch).connect:
                raise commands.BotMissingPermissions(['connect'])
            if ch.guild != ctx.guild:
                raise VoiceCommandError('Guild mismatch')
            if ctx.guild.id in self.voice_chans:
                if ch.id == self.voice_chans[ctx.guild.id]:
                    raise VoiceCommandError('Already connected to that channel')
                vcl: discord.VoiceClient = ctx.guild.voice_client
                if vcl is None:
                    raise VoiceCommandError('Guild does not support voice connections')
                if vcl.is_connected():
                    await vcl.move_to(ch)
                else:
                    await ch.connect()
            else:
                await ch.connect()
            self.voice_chans[ctx.guild.id] = ch.id
            self.commit()
            await ctx.send('Joined the voice channel!')

    @pikavoice.command()
    @commands.check(connected_and_not_playing)
    async def say(self, ctx: commands.Context, *, msg: cleaner_content(fix_channel_mentions=True,
                                                                       escape_markdown=False)):
        """Use eSpeak to say the message aloud in the voice channel."""
        ctx.guild.voice_client.play(EspeakAudioSource(self, msg, executable=self.ffmpeg,
                                                      before_options='-loglevel quiet'),
                                    after=lambda e: print('Player error: %s' % e) if e else None)

    @commands.command()
    async def pikasay(self, ctx, *, msg: cleaner_content(fix_channel_mentions=True,
                                                         escape_markdown=False)):
        """Use eSpeak to say the message aloud in the voice channel."""
        await ctx.invoke(self.say, msg=msg)

    @pikavoice.command()
    async def stop(self, ctx: commands.Context):
        """Stop all playing audio"""
        vclient: discord.VoiceClient = ctx.guild.voice_client
        if vclient.is_playing():
            vclient.stop()

    @commands.command()
    async def pikashutup(self, ctx):
        """Stop all playing audio"""
        await ctx.invoke(self.stop)

    @pikavoice.command()
    async def params(self, ctx, *kwargs: EspeakParamsConverter(**__espeak_valid_keys)):
        f"""Update pikavoice params.

        Syntax:
        {self.bot.command_prefix}pikavoice params a=amplitude
        g=gap k=emphasis p=pitch s=speed v=voice"""
        params = dict(self.espeak_kw)
        for key, value in kwargs:
            params[key] = (str if key == 'v' else int)(value)
        try:
            EspeakAudioSource.call_espeak('Test', 'tmp.wav', **params)
        except subprocess.CalledProcessError:
            await ctx.send('Parameters could not be updated')
        else:
            self.espeak_kw = params
            self.commit()
            await ctx.send('Parameters successfully updated')
        finally:
            os.remove('tmp.wav')

    @commands.command()
    async def pikaparams(self, ctx, *kwargs: EspeakParamsConverter(**__espeak_valid_keys)):
        f"""Update pikavoice params.

        Syntax:
        {self.bot.command_prefix}pikaparams a=amplitude
        g=gap k=emphasis p=pitch s=speed v=voice"""
        await ctx.invoke(self.params, *kwargs)

    @params.error
    @pikaparams.error
    async def pikaparams_error(self, ctx: commands.Context, exc: BaseException):
        if isinstance(exc, commands.BadArgument):
            view = ctx.view
            view.index = 0
            if view.skip_string(f'{ctx.prefix}{ctx.invoked_with}'):
                converter = EspeakParamsConverter(**self.__espeak_valid_keys)
                while not view.eof:
                    view.skip_ws()
                    arg = view.get_word()
                    try:
                        k, v = await converter.convert(ctx, arg)
                    except (KeyError, TypeError, ValueError):
                        await ctx.send(f'{ctx.author.mention}: Argument "{arg}" raised {exc.__class__.__name__}: {exc}',
                                       delete_after=10)
            else:
                self.bot.log_tb(ctx, exc)

    @commands.command()
    @commands.check(connected_and_not_playing)
    async def ytplay(self, ctx: commands.Context, url):
        raise NotImplemented


def setup(bot: PikalaxBOT):
    bot.add_cog(YouTube(bot))


def teardown(bot: PikalaxBOT):
    for vc in bot.voice_clients:  # type: discord.VoiceClient
        bot.loop.create_task(vc.disconnect())