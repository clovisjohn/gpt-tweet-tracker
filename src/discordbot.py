import re
from typing import Tuple, List, Dict

from discord.ext import commands
from discord.ext.commands.context import Context
from .globals_ import CURSOR, cnx, TWITTER_CLIENT, TWITTER_HANDLE_REGEX, MAX_MESSAGE_LENGTH, DISCORD_CHANNEL_ID, handle_exist, InvalidHandle, HandleAlreadyExist, UserLimitReached, InvalidList, UserNotTracked
from .twitterStream import *

from . import discord_logger


intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
intents.presences = False


def process_handles(handle: str) -> Tuple[str, int]:
    """
    Process a list of Twitter handles and return a list of valid handles.

    Parameters
    ----------
    handle : str
    The handle to process

    Returns
    -------
    tuple[str,int]
    A tuple containing the handle and the id of a user.

    Raises
    ------
    InvalidHandle
    If the handle is invalid
    
    HandleAlreadyExist
    If the handle already exists in the database

    """

    handle = handle.lower()
    if not re.match(TWITTER_HANDLE_REGEX, handle):
        raise InvalidHandle

    user = TWITTER_CLIENT.get_user(username=handle)

    if user.data is None:
        raise InvalidHandle

    if handle_exist(user.data.id):
        raise HandleAlreadyExist(handle, user.data.id)

    return handle, user.data.id

def process_twitter_list( list_id : str ) -> List[Dict] :
    """
    Process a Twitter list and return a list of valid handles.
    
    Parameters
    ----------
    list_id : str
    The ID of the list to process
    
    Returns
    -------
    list[dict]
    A list of users
    
    Raises
    ------
    InvalidList
    If the list id is invalid
    """
    
    # check if twitter list is vallid
    try:
        twitter_list = TWITTER_CLIENT.get_list(id=list_id)
    except tweepy.errors.BadRequest:
        raise InvalidList
        
    if twitter_list.data is None:
        raise InvalidList
        
    # get list members
    members = tweepy.Paginator(TWITTER_CLIENT.get_list_members, id=list_id).flatten()
    return [m for m in members]


def create_start_message() -> discord.embeds.Embed:
    """
    Create a message to send to the user when they start the bot.

    Returns
    -------
    discord.embeds.Embed
    """

    embed = discord.embeds.Embed(
        title="Hello World!",
        description="The bot is now online and ready to serve you.",
        color=0x0000FF,
    )
    embed.set_thumbnail(url="https://i.imgur.com/GyWdKAx.jpg")
    embed.add_field(
        name="Commands",
        value="!help or /help - Shows a list of available commands",
        inline=False,
    )
    return embed


async def load_database(stream: MyStreamListener, channel: discord.channel.TextChannel) -> None:
    """
    Load the database of Twitter handles being tracked by the bot.

    Parameters
    ----------
    stream : tweepy.Stream
    The Twitter stream object.

    channel : discord.channel.TextChannel
    The channel to send the message to.

    Returns
    -------
    None
    """

    CURSOR.execute("SELECT COUNT(*) FROM users")
    count = CURSOR.fetchone()[0]
    if count > 0:
        try:
            CURSOR.execute("SELECT handle FROM users")
            handles = [handle[0] for handle in CURSOR.fetchall()]
            await stream.load_handles_from_list(handles)
            stream.custom_filter()
        except UserLimitReached:
            await channel.send("Users limit reached")
            
    stream.custom_filter()


class Tracker(commands.Cog):
    def __init__(self, bot: "DiscordBot") -> None:
        self.bot = bot

    @commands.hybrid_command(description="Add a new user to the database")
    async def add_user(self, ctx, handle: str, question: str):

        await ctx.defer()
        handle, user_id = process_handles(handle)
        await self.bot.stream.add_handle(handle)

        # Add handle to the database
        CURSOR.execute(
            "INSERT INTO users (id, handle, question) VALUES (?, ?, ?)",
            (user_id, handle, question),
        )
        cnx.commit()
        await ctx.send(f"Tracking {handle} for question: {question}")

    @commands.hybrid_command(description="Add users from a twitter list to the database")
    async def bulk_add(self,ctx,list_id : str, question: str):
        await ctx.defer()
        
        members = process_twitter_list(list_id)
        valid_members=[]
        for member in members:
            # Check if some users are not already in the database
            if not handle_exist(member.id):
                valid_members.append(member)
        
        
        if(len(valid_members)==0):
            await ctx.send("All users are already in the database")
            return
        
        CURSOR.execute("SELECT handle FROM users")
        handles = CURSOR.fetchall()

        handles.extend([m.username for m in valid_members])
        await self.bot.stream.load_handles_from_list(handles)
        
        # Add handles to the database
        for member in valid_members:
            CURSOR.execute(
                "INSERT INTO users (id, handle, question) VALUES (?, ?, ?)",
                (member.id, member.username, question),
            )
            cnx.commit()
            
        await ctx.send(f"Tracking {len(valid_members)} users for question: {question}")
        
        
    @commands.hybrid_command(description="Remove a user from the database.")
    async def remove_user(self, ctx, handle):

        await ctx.defer()
        try:
            handle, user_id = process_handles(handle)

        except HandleAlreadyExist as e:
            handle, user_id = e.handle, e.user_id
            await self.bot.stream.remove_handle(handle)

            # Remove handle from the database
            CURSOR.execute("DELETE FROM users WHERE id = ?", (user_id,))
            cnx.commit()
            await ctx.send(f"Stopped tracking {handle}")

        else:
            raise UserNotTracked


        
    @commands.hybrid_command(description="Remove all users from a twitter list from the database")
    async def bulk_remove(self,ctx,list_id : str):
        await ctx.defer()
        
        members = process_twitter_list(list_id)
        valid_members=[]
        for member in members:
            # Filter users who are not in the database
            if handle_exist(member.id):
                valid_members.append(member)
        
        
        if(len(valid_members)==0):
            await ctx.send("No users from this list is in the database")
            return
        
        CURSOR.execute("SELECT handle FROM users")
        handles = CURSOR.fetchall()

        valid_handles = [m.username for m in valid_members]
        updated_list = [handle for handle in handles if handle not in valid_handles]
        await self.bot.stream.load_handles_from_list(updated_list)
        
        # Add handles to the database
        for member in valid_members:
            CURSOR.execute("DELETE FROM users WHERE id = ?", (member.id,))
            cnx.commit()

        await ctx.send(f"Stopped tracking {len(valid_members)} users")
      
    @commands.hybrid_command(
        description="Lists all the users being tracked and their respective questions "
    )
    async def list(self, ctx):
        await ctx.defer()
        CURSOR.execute("SELECT * FROM users")
        users = CURSOR.fetchall()
        await ctx.send(f"Currently tracking {len(users)} users")

        if len(users) == 0:
            return

        # Print list of handles and questions in Discord channel
        msg_list=[]
        msg = ""
        for user in users:
            handle = user[1]
            question = user[2]
            if len(msg) + len(f"{handle}: {question}\n") >= MAX_MESSAGE_LENGTH:
                msg_list.append(msg)
                msg=""
            msg += f"{handle}: {question}\n"
            
        msg_list.append(msg)
        for msg in msg_list:
            await ctx.send(msg)

        

    @commands.hybrid_command(description="Start the bot")
    async def start(self, ctx):
        # Start the bot
        await ctx.send("Starting bot")
        self.bot.stream = MyStreamListener(self.bot.channel, CURSOR)
        await load_database(self.bot.stream, self.bot.channel)

    @commands.hybrid_command(description="Stop the bot")
    async def stop(self, ctx):
        # Stop the bot
        await ctx.send("Stopping bot")
        self.bot.stream.disconnect()

    @commands.hybrid_command(name="help", description="Show help for the bot")
    async def help(self, ctx):
        # Print list of commands in Discord channel
        embed = discord.embeds.Embed(
            title="Commands", description="List of available commands", color=0x0000FF
        )
        embed.set_thumbnail(url="https://i.imgur.com/GyWdKAx.jpg")
        for command in self.bot.commands:
            embed.add_field(
                name=f"!{command.name} - ", value=f"{command.description}", inline=False
            )

        await ctx.send(embed=embed)


class DiscordBot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs, help_command=None)
        self.channel = None
        self.stream = None

    async def setup_hook(self) -> None:
        tracker = Tracker(self)
        await self.add_cog(tracker)

    async def on_ready(self) -> None:
        #print(f"{self.user} has connected to Discord!")
        discord_logger.info(f"{self.user} has connected to Discord!")

        if self.channel is None:
            self.channel = self.get_channel(DISCORD_CHANNEL_ID)
            MY_GUILD = self.channel.guild
            self.tree.copy_global_to(guild=MY_GUILD)
            await self.tree.sync(guild=MY_GUILD)
            await self.channel.send(embed=create_start_message())

        if self.stream is None:
            self.stream = MyStreamListener(self.channel, CURSOR)
            await load_database(self.stream, self.channel)

    async def on_command_error(self, ctx: Context, exception: Exception) -> None:
        #print(exception)
        discord_logger.exception(exception)
        await self.channel.send(
            embed=create_error_embed(ctx.message.content, exception)
        )