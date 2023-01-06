import os
import discord
from discord.ext import commands
import openai
import tweepy
import tweepy.asynchronous
import sqlite3
import dotenv
from utils import *

# Get the Discord Bot Token from the environment variables
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

# Get the Discord Channel ID from the environment variables
DISCORD_CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID"))

# Connect to the Discord API using discord.py

intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
intents.presences = False

client = commands.Bot(command_prefix='!',intents=intents)
channel = None


# Connect to the SQLite database
cnx = sqlite3.connect('gpt_tweet_tracker.db')
cursor = cnx.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (handle TEXT, question TEXT)")

#Create stream 
stream = None

async def handle_exist(handle):
    # Check if handle exists in the database
    cursor.execute("SELECT COUNT(*) FROM users WHERE handle = ?", (handle,))
    count = cursor.fetchone()[0]
    return count > 0
    
async def load_database():
    # Execute a COUNT statement to count the number of rows in the table
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    if count > 0:
        try:
            await stream.update_handles_from_database()
            stream.custom_filter()
        except UserLimitReached:
            await channel.send("Users limit reached")

# Set up command handling
@client.command()
async def add_user(ctx, handle: str, question: str):
    
    # Check if handle already exists in the database
    if await handle_exist(handle):
        await ctx.send('Handle already exists in database')
        return
    
    try:
        await stream.add_handle(handle)
        stream.custom_filter()
        cursor.execute("INSERT INTO users VALUES (?, ?)", (handle, question))
        cnx.commit()
        await ctx.send(f"Tracking {handle} for question: {question}")
    except UserLimitReached :
        await ctx.send("Users limit reached")
    
        
@client.command()
async def remove_user(ctx, handle: str):

    # Check if handle already exists in the database
    if not (await handle_exist(handle)):
        await ctx.send(f"User is not currently tracked")
        return
    
    await stream.remove_handle(handle)
    stream.custom_filter()
    cursor.execute("DELETE FROM users WHERE handle = ?", (handle,))
    cnx.commit()
    await ctx.send(f"Stopped tracking {handle}")


@client.command()
async def list(ctx):
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    await ctx.send(f"Currently tracking {len(users)} users")
        
    # Print list of handles and questions in Discord channel
    msg=""
    for user in users:
        handle = user[0]
        question = user[1]
        msg += f"{handle}: {question}\n"
    await ctx.send(msg)

@client.command()
async def start(ctx):
    global stream
    # Start the bot
    await ctx.send('Starting bot')
    stream = MyStreamListener(channel,cursor)
    await load_database()
    
    
@client.command()
async def stop(ctx):
    # Stop the bot
    await ctx.send('Stopping bot')
    stream.disconnect()
        
      
@client.event
async def on_ready():
    global stream
    global channel
    print(f'{client.user} has connected to Discord!')
    channel = client.get_channel(DISCORD_CHANNEL_ID)
    if stream is None:
        stream = MyStreamListener(channel,cursor)
        await load_database()
        



# Run the bot
client.run(DISCORD_BOT_TOKEN)

