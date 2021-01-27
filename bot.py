import discord
import asyncio
import pymongo
import os

from dotenv import load_dotenv
from pymongo import MongoClient
from discord.ext import commands

load_dotenv()
TOKEN = os.environ.get('TOKEN')
intents = discord.Intents.default()
intents.members = True
client = commands.Bot(command_prefix='', case_insensitive=True, help_command=None, intents=intents, owner_id=235810177436221440)

CON = os.environ.get('DB_CON')
cluster = MongoClient(CON)
db = cluster['hooven']
guilds_info = db['guilds_info']


async def heartbeat():
    await client.wait_until_ready()
    await asyncio.sleep(1)
    while True:
        latency = (client.latency * 100).__round__(0)
        print(f'[BOT] Current latency: {latency}ms.')
        await asyncio.sleep(900)


def get_guild_info(guild_id):
    guild_info = guilds_info.find_one({'_id': guild_id})
    if guild_info is not None:
        print('[DB] Got guild info from db.')
        return guild_info


def insert_guild_info(guild_id, channel, message):
    guilds_info.insert_one({'_id': guild_id, 'welcomeChannel': channel, 'welcomeMessage': message})
    print(f'[DB] Inserted guild info for guild_id: {guild_id}')


def delete_guild_info(guild_id):
    guilds_info.delete_one({'_id': guild_id})
    print(f'[DB] Removed guild info for guild_id: {guild_id}')


def update_guild_info(guild_id, channel=None, message=None):
    if channel is not None and message is not None:
        guilds_info.update_one(filter={'_id': guild_id},
                               update={'$set': {'welcomeChannel': channel, 'welcomeMessage': message}})
    elif channel is not None:
        guilds_info.update_one(filter={'_id': guild_id},
                               update={'$set': {'welcomeChannel': channel}})
    elif message is not None:
        guilds_info.update_one(filter={'_id': guild_id},
                               update={'$set': {'welcomeMessage': message}})
    print(f'[DB] Updated guild info for guild_id: {guild_id}')


@client.event
async def on_ready():
    print(f'[BOT] {client.user.name} is ready in {len(client.guilds)} guilds.')


@client.event
async def on_member_join(member: discord.Member):
    guild_info = get_guild_info(member.guild.id)
    welcome_channel = guild_info['welcomeChannel']
    welcome_message = guild_info['welcomeMessage']

    if '{user}' in welcome_message:
        welcome_message = welcome_message.replace('{user}', member.mention)

    await client.get_channel(int(welcome_channel)).send(welcome_message)


@client.event
async def on_guild_join(guild):
    print(f'[BOT] Joined {guild.name}. Total guilds: {len(client.guilds)}')
    channel = guild.system_channel.id
    if channel is None:
        channel = guild.text_channels[0].id
    message = 'Welcome to the server, {user}!'
    insert_guild_info(guild.id, channel, message)


@client.event
async def on_guild_remove(guild):
    print(f'[BOT] Left {guild.name}. Total guilds: {len(client.guilds)}')
    delete_guild_info(guild.id)


@client.command()
@commands.is_owner()
async def _reset_guild_info(ctx):
    channel = ctx.guild.system_channel.id
    if channel is None:
        channel = ctx.guild.text_channels[0].id
    message = 'Welcome to the server, {user}!'
    update_guild_info(ctx.guild.id, channel, message)
    await ctx.send(f'Reset guild_info for this guild!')


@client.command(name='Welcome_message')
async def _welcome_message(ctx, *, message):
    update_guild_info(ctx.guild.id, message=message)
    await ctx.send(f'Updated welcome message to `{message}`')


@client.command(name='Welcome_channel')
async def _welcome_channel(ctx, channel: discord.TextChannel):
    update_guild_info(ctx.guild.id, channel= channel.id)
    await ctx.send(f'Updated welcome channel to {channel.mention}')


client.loop.create_task(heartbeat())
client.run(TOKEN)
