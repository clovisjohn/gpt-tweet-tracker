import discord
import re
from discord import app_commands
from discord.ext import commands
from globals_ import *
from twitterStream import *


intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
intents.presences = False

def create_start_message():
    embed = discord.Embed(title='Hello World!', description='The bot is now online and ready to serve you.', color=0x0000ff)
    embed.set_thumbnail(url='https://i.imgur.com/GyWdKAx.jpg')
    embed.add_field(name='Commands', value='!help - Shows a list of available commands', inline=False)
    return embed

def to_lower(string):
    return string.lower()
    
async def load_database(stream,channel):
    # Execute a COUNT statement to count the number of rows in the table
    CURSOR.execute("SELECT COUNT(*) FROM users")
    count = CURSOR.fetchone()[0]
    if count > 0:
        try:
            await stream.update_handles_from_database()
            stream.custom_filter()
        except UserLimitReached:
            await channel.send("Users limit reached")



class Tracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.hybrid_command()
    async def add_user(self,ctx, handle: to_lower, question: str):
    
        if not re.match(TWITTER_HANDLE_REGEX, handle):
            await ctx.send("Invalid handle")
            return;
        
        # Check if handle already exists in the database
        if await handle_exist(handle):
            await ctx.send('Handle already exists in database')
            return
    
        try:
            await self.bot.stream.add_handle(handle)
            self.bot.stream.custom_filter()
            CURSOR.execute("INSERT INTO users VALUES (?, ?)", (handle, question))
            cnx.commit()
            await ctx.send(f"Tracking {handle} for question: {question}")
        except UserLimitReached :
            await ctx.send("Users limit reached")
    
        
    @commands.hybrid_command()
    async def remove_user(self,ctx, handle: to_lower):
        
        if not re.match(TWITTER_HANDLE_REGEX, handle):
            await ctx.send("Invalid handle")
            return
        
        # Check if handle already exists in the database
        if not (await handle_exist(handle)):
            await ctx.send(f"User is not currently tracked")
            return
    
        await self.bot.stream.remove_handle(handle)
        self.bot.stream.custom_filter()
        CURSOR.execute("DELETE FROM users WHERE handle = ?", (handle,))
        cnx.commit()
        await ctx.send(f"Stopped tracking {handle}")


    @commands.hybrid_command()
    async def list(self,ctx):
        CURSOR.execute("SELECT * FROM users")
        users = CURSOR.fetchall()
        await ctx.send(f"Currently tracking {len(users)} users")
        
        # Print list of handles and questions in Discord channel
        msg=""
        for user in users:
            handle = user[0]
            question = user[1]
            msg += f"{handle}: {question}\n"
        await ctx.send(msg)

    @commands.hybrid_command()
    async def start(self,ctx):
        # Start the bot
        await ctx.send('Starting bot')
        self.bot.stream = MyStreamListener(self.bot.channel,CURSOR)
        await load_database(self.bot.stream,self.bot.channel)
    
    
    @commands.hybrid_command()
    async def stop(self,ctx):
        # Stop the bot
        await ctx.send('Stopping bot')
        self.bot.stream.disconnect()


class DiscordBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel = None
        self.stream = None

        
        
    async def setup_hook(self):
        tracker = Tracker(self)
        await self.add_cog(tracker)
        
        

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        
        if self.channel is None:
            self.channel = self.get_channel(DISCORD_CHANNEL_ID)
            MY_GUILD = self.channel.guild
            self.tree.copy_global_to(guild=MY_GUILD)
            await self.tree.sync(guild=MY_GUILD)
            
        if self.stream is None:
            self.stream = MyStreamListener(self.channel,CURSOR)
            await load_database(self.stream,self.channel)
            
        await self.channel.send(embed=create_start_message())

        