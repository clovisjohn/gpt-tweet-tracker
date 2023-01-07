from discord.ext import commands
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
CURSOR.execute("CREATE TABLE IF NOT EXISTS users (handle TEXT, question TEXT)")

TWITTER_HANDLE_REGEX = r"^[a-zA-Z0-9_]{1,15}$"

class UserLimitReached(Exception):
    ...
    pass

def create_error_embed(self,excep):
    embed = discord.Embed(title="Error", description="An error occurred. Please try again.", color=0xFF0000)
    embed.set_author(name="Tweet Match", url="https://twitter.com", icon_url="https://abs.twimg.com/icons/apple-touch-icon-192x192.png")
    embed.add_field(name="Type", value=type(excep).__name__, inline=False)
    embed.add_field(name="Message", value=str(excep), inline=False)
    embed = discord.Embed(timestamp=datetime.datetime.now())
    embed.set_footer(text="Tweet Match", icon_url="https://abs.twimg.com/icons/apple-touch-icon-192x192.png")
    return embed

async def handle_exist(handle):
    # Check if handle exists in the database
    CURSOR.execute("SELECT COUNT(*) FROM users WHERE handle = ?", (handle,))
    count = CURSOR.fetchone()[0]
    return count > 0
