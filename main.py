from globals_ import *
from discordbot import * 


client = DiscordBot(
    command_prefix='!',
    activity=discord.Game(name=f"!help"),
    intents=intents
    )
    
    
# Run the bot
if __name__ == "__main__":
    client.run(DISCORD_BOT_TOKEN)


