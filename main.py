from globals_ import *
from discordbot import * 


client = DiscordBot(command_prefix='!',intents=intents)
        

# Run the bot
if __name__ == "__main__":
    try:
        client.run(DISCORD_BOT_TOKEN)
    except: 
        err_type, error, traceback = sys.exc_info()
        print(error)
        client.channel.send(embed=create_error_embed(error))

