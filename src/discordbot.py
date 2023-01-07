import re
from typing import Tuple

from discord.ext import commands
from discord.ext.commands.context import Context
from globals_ import *
from twitterStream import *


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
            await stream.update_handles_from_database()
            stream.custom_filter()
        except UserLimitReached:
            await channel.send("Users limit reached")


class Tracker(commands.Cog):
    def __init__(self, bot: "DiscordBot") -> None:
        self.bot = bot

    @commands.hybrid_command(description="Add a new user to the database")
    async def add_user(self, ctx, handle: str, question: str):

        await ctx.defer()
        handle, user_id = process_handles(handle)

        await self.bot.stream.add_handle(handle)
        self.bot.stream.custom_filter()

        # Add handle to the database
        CURSOR.execute(
            "INSERT INTO users (id, handle, question) VALUES (?, ?, ?)",
            (user_id, handle, question),
        )
        cnx.commit()
        await ctx.send(f"Tracking {handle} for question: {question}")

    @commands.hybrid_command(description="Remove a user from the database.")
    async def remove_user(self, ctx, handle):

        await ctx.defer()
        try:
            handle, user_id = process_handles(handle)

        except HandleAlreadyExist as e:
            handle, user_id = e.handle, e.user_id
            await self.bot.stream.remove_handle(handle)
            self.bot.stream.custom_filter()
            # Remove handle from the database
            CURSOR.execute("DELETE FROM users WHERE id = ?", (user_id,))
            cnx.commit()
            await ctx.send(f"Stopped tracking {handle}")

        else:
            raise UserNotTracked

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
        msg = ""
        for user in users:
            handle = user[1]
            question = user[2]
            msg += f"{handle}: {question}\n"

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
        print(f"{self.user} has connected to Discord!")

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
        print(exception)
        await self.channel.send(
            embed=create_error_embed(ctx.message.content, exception)
        )