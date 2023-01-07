from discord.ext import commands
import discord
import datetime
import openai
import tweepy.asynchronous
import sqlite3
import dotenv
import os

# Load environment variables from a .env file
dotenv.load_dotenv()

# Get the Twitter Bearer Token from the environment variables
TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN")

# Get the OpenAI API key from the environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Set up connection to OpenAI API
openai.api_key = OPENAI_API_KEY

# Get the Discord Bot Token from the environment variables
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

# Get the Discord Channel ID from the environment variables
DISCORD_CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID"))

# Connect to the SQLite database
cnx = sqlite3.connect('gpt_tweet_tracker.db')
CURSOR = cnx.cursor()

#create table containing twitter user id and string of twitter handles
CURSOR.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, handle TEXT, question TEXT )''')

TWITTER_CLIENT = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)


TWITTER_HANDLE_REGEX = r"^[a-zA-Z0-9_]{1,15}$"



class UserLimitReached(Exception):
    ...
    pass

class HandleProcessingException(Exception):
    ...
    pass

class InvalidHandle(HandleProcessingException):
    ...
    pass

class HandleAlreadyExist(HandleProcessingException):
    def __init__(self, handle,user_id):
        self.handle = handle
        self.user_id = user_id


def create_error_embed(excep):
    embed = discord.Embed(title="Error", description="An error occurred. Please try again.", color=0xFF0000, timestamp=datetime.datetime.now())
    embed.set_author(name="Tweet Match", url="https://twitter.com", icon_url="https://abs.twimg.com/icons/apple-touch-icon-192x192.png")
    embed.add_field(name="Type", value=type(excep).__name__, inline=False)
    embed.add_field(name="Message", value=str(excep), inline=False)
    return embed

def handle_exist(userID):
    # Check if handle exists in the database
    CURSOR.execute("SELECT COUNT(*) FROM users WHERE id = ?", (userID,))
    count = CURSOR.fetchone()[0]
    return count > 0
