import datetime
import os
import sqlite3

import discord
import dotenv
import openai
import tweepy.asynchronous
from discord.ext import commands

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
cnx = sqlite3.connect("gpt_tweet_tracker.db")
CURSOR = cnx.cursor()

# create table containing twitter user id, twitter handles and questions
CURSOR.execute(
    """CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, handle TEXT, question TEXT )"""
)

TWITTER_CLIENT = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)

# Regular expression for validating Twitter handles. A Twitter
TWITTER_HANDLE_REGEX = r"^[a-zA-Z0-9_]{1,15}$"


class HandleProcessingException(commands.BadArgument):
    """
    Custom exception class for handling errors that occur when processing Twitter handles.
    """

    def __init__(self, message: str) -> None:
        super().__init__("There was an error processing the handle: " + message)


class UserLimitReached(Exception):
    """
    Exception raised when the number of Twitter handles being tracked by the bot has reached the maximum allowed number
    """

    def __init__(self):
        super().__init__("Users limit reached")


class InvalidHandle(HandleProcessingException):
    """
    Exception raised when a Twitter handle is invalid.
    """

    def __init__(self):
        super().__init__("Invalid handle")


class HandleAlreadyExist(HandleProcessingException):
    """
    Exception raised when a Twitter handle is already being tracked by the bot.
    """

    def __init__(self, handle: str, user_id: int) -> None:
        super().__init__("Handle already exists in database")
        self.handle = handle
        self.user_id = user_id


class UserNotTracked(HandleProcessingException):
    """
    Exception raised when a Twitter handle is not being tracked by the bot.
    """

    def __init__(self):
        super().__init__("User is not currently tracked")


def create_error_embed(user_message: str, excep: HandleAlreadyExist) -> discord.embeds.Embed:
    """
    Create an embed containing the error message and the user's message.
    """
    embed = discord.embeds.Embed(
        title="Error",
        description=f"An error occurred  when trying to process \n{user_message}.",
        color=0xFF0000,
        timestamp=datetime.datetime.now(),
    )
    embed.set_author(
        name="Tweet Match",
        url="https://twitter.com",
        icon_url="https://abs.twimg.com/icons/apple-touch-icon-192x192.png",
    )
    embed.add_field(name="Type", value=type(excep).__name__, inline=False)
    embed.add_field(name="Message", value=str(excep), inline=False)
    return embed


def handle_exist(userID: int) -> bool:
    """
    Check if a Twitter handle is already being tracked by the bot.
    """
    CURSOR.execute("SELECT COUNT(*) FROM users WHERE id = ?", (userID,))
    count = CURSOR.fetchone()[0]
    return count > 0
