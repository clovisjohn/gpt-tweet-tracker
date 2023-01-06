import discord
from discord import app_commands
from discord.ext import commands
from globals_ import *
from twitterStream import *


intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
intents.presences = False

    
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
        self.stream = None
        
    @commands.hybrid_command()
    async def add_user(self,ctx, handle: str, question: str):
    
        # Check if handle already exists in the database
        if await handle_exist(handle):
            await ctx.send('Handle already exists in database')
            return
    
        try:
            await self.stream.add_handle(handle)
            self.stream.custom_filter()
            CURSOR.execute("INSERT INTO users VALUES (?, ?)", (handle, question))
            cnx.commit()
            await ctx.send(f"Tracking {handle} for question: {question}")
        except UserLimitReached :
            await ctx.send("Users limit reached")
    
        
    @commands.hybrid_command()
    async def remove_user(self,ctx, handle: str):

        # Check if handle already exists in the database
        if not (await handle_exist(handle)):
            await ctx.send(f"User is not currently tracked")
            return
    
        await self.stream.remove_handle(handle)
        self.stream.custom_filter()
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
        self.stream = MyStreamListener(self.channel,CURSOR)
        await load_database(self.stream,self.channel)
    
    
    @commands.hybrid_command()
    async def stop(self,ctx):
        # Stop the bot
        await ctx.send('Stopping bot')
        self.stream.disconnect()


class DiscordBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel = None
        self.stream = None

        
        
    async def setup_hook(self):
        tracker = Tracker(self)
        tracker.stream = self.stream
        tracker.channel = self.channel
        await self.add_cog(Tracker(self))
        
        

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        self.channel = self.get_channel(DISCORD_CHANNEL_ID)
        
        if self.channel is None:
            self.channel = self.get_channel(DISCORD_CHANNEL_ID)
            MY_GUILD = self.channel.guild
            self.tree.copy_global_to(guild=MY_GUILD)
            await self.tree.sync(guild=MY_GUILD)
            
        if self.stream is None:
            self.stream = MyStreamListener(self.channel,CURSOR)
            await load_database(self.stream,self.channel)

        