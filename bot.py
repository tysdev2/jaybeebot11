import json
import discord
from discord.ext import commands, tasks
import asyncio
import os
import time
import datetime
import sqlite3


client = commands.Bot(command_prefix="!", intents=discord.Intents.all(), help_command=None, application_id=1107323344338047106)


@client.event
async def on_ready():
    print(f"[!] {time.strftime('%Y-%m-%d - %H:%M')}: Jaybee Fiverr Bot")
    print(f"[!] {client.user} - {client.user.id}")



@client.event
async def on_guild_join(guild: discord.Guild):
    await client.tree.sync(guild=guild)



@client.event
async def setup_hook():
    logs = await client.tree.sync()
    print(f"[!] Synced {len(logs)} commands")
    try:
        conn = sqlite3.connect(f"Data/users.db")
        curs = conn.cursor()
        run = f"CREATE TABLE IF NOT EXISTS users (id integer PRIMARY KEY, points integer, invites integer);"
        curs.execute(run)
        conn.commit()
        curs.close()
        print("[!] Users Database connected")
    except Exception as exc:
        print(exc)
        quit()




async def loadcogs():
    for files in os.listdir(f'Commands'):
        if files.endswith(".py"):
            await client.load_extension(f'Commands.{files[:-3]}')




async def startup():
    async with client:
        with open("Data/config.json", "r+", encoding="utf-8") as f:
            config = json.load(f)
            token = config["token"]
            client.waiting = {}
            await loadcogs()
            await client.start(token)





asyncio.run(startup())