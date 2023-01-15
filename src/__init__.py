import os, sys, logging 

# Setup logging handlers
file_handler = logging.FileHandler(filename="app.log")
stream_handler = logging.StreamHandler()

dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')

file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)


# Setup tweepy logging
tweepy_logger = logging.getLogger("tweepy")
tweepy_logger.setLevel(logging.DEBUG)

tweepy_logger.addHandler(file_handler)
tweepy_logger.addHandler(stream_handler)

#Set up discord logging
discord_logger = logging.getLogger("discord")
discord_logger.setLevel(logging.DEBUG)

discord_logger.addHandler(file_handler)