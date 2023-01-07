import openai
import tweepy
import tweepy.asynchronous
import datetime
import discord
import traceback
from globals_ import *


async def check_tweet_for_match(tweet, question):
    # Use OpenAI API to check tweet for match with question
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"{question}\n{tweet}",
        max_tokens=2048,
        temperature=0.5,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    # Extract answer from API response
    answer = response['choices'][0]['text'].strip().lower()
    return ["yes" in answer, answer]


    

class MyStreamListener(tweepy.asynchronous.AsyncStreamingClient):
    def __init__(self, channel, cursor,**kwargs):
        super().__init__(bearer_token=TWITTER_BEARER_TOKEN,wait_on_rate_limit=True, **kwargs)
        self.channel = channel
        self.cursor = cursor
    
    async def update_rules(self,rules):
        await self.delete_rules(rules)
        await self.add_rules(rules)
        
    
    def custom_filter(self):
        self.disconnect()
        self.task=None
        self.filter(expansions=["author_id"],user_fields=["username", "name",'profile_image_url'],)


    async def update_handles_from_database(self):

        # delete existing rules
        rules = (await self.get_rules()).data
        print(type(rules))
        if rules is not None:
            await self.delete_rules(rules)
        
        # add new rules to track tweets from users in database 
        self.cursor.execute('''SELECT handle FROM users''')
        handles = self.cursor.fetchall()
        
        #merge handles into twitter search query to track users corresponding to handles of 512 characters maximum and add these strings to a list.
        query = ""
        query_list = []
        for handle in handles:
            if len(query) + len(handle[0]) > 510:
                query_list.append(query)
                query = ""
                if len(query_list) == 5:
                    raise UserLimitReached

            query += f'from:{handle[0]} OR '
        
        #add last query to list
        query_list.append(query)
         
        #add rules to twitter stream
        for query in query_list:
            query = query.rstrip(' OR ')
            temp_rule =  tweepy.StreamRule(query)
            await self.add_rules(temp_rule)
            
        print((await self.get_rules()).data)
             
             

         
         
    async def add_handle(self,handle):
        
        #if there are no rules, add a new rule
        rules = (await self.get_rules()).data
        if rules is None or len(rules) == 0:
            temp_rule =  tweepy.StreamRule(f'from:{handle}')
            await self.add_rules(temp_rule)
            print((await self.get_rules()).data)
            return None

        for rule in rules:
            #check if there is room to add a new handle
            if len(rule.value) + len(handle) < 510:
                new_query = rule.value + f' OR from:{handle}'
                new_rule = tweepy.StreamRule(value=new_query,id=rule.id)
                await self.update_rules(new_rule)
                print((await self.get_rules()).data)
                return None
               
        #if there is no room to add a new handle, check if there is room to add a new rule
        if len(rules) < 5:
                temp_rule =  tweepy.StreamRule(f'from:{handle}')
                await self.add_rules(temp_rule)
                print((await self.get_rules()).data)
                return None
                
        #else, raise UserLimitReached
        print((await self.get_rules()).data)
        raise UserLimitReached
        
    
    
    async def remove_handle(self,handle):
        #remove handle from all rules
        rules = (await self.get_rules()).data
        print(type(rules))
        for rule in rules:
            if f'from:{handle}' in rule.value:
                await self.delete_rules(rule)
                new_query = rule.value.replace(f'from:{handle} OR ','')
                new_query = new_query.replace(f'from:{handle}','')
                new_query = new_query.rstrip(' OR ')
                new_rule = tweepy.StreamRule(value=new_query,id=rule.id)
                print(await self.add_rules(new_rule))
                print((await self.get_rules()).data)
                return;
            
        

    
   
    async def on_response(self, response):
        tweet = response.data
        user = response.includes['users'][0]
        username = user.username
        
        # Get question for tweet author from database
        self.cursor.execute('''SELECT question FROM users WHERE handle=?''', (username,))
        question = self.cursor.fetchone()[0]

        match = await check_tweet_for_match(tweet.text, question)

        print(f"{tweet.text} {question} {str(match[0])} {match[1]}")   

        if match[0]:
        
            # If tweet matches question, send tweet in Discord channel
            await self.channel.send("New tweet")
            # create dsicord embed of the tweet
            embed = discord.Embed(title=f"{user.name} (@{user.username})", url=f"https://twitter.com/{user.username}/status/{tweet.id}", description=tweet.text, color=0x1DA1F2)
            embed.set_author(name="Tweet Match", url="https://twitter.com", icon_url="https://abs.twimg.com/icons/apple-touch-icon-192x192.png")
            embed.set_thumbnail(url=user.profile_image_url)
            embed.add_field(name="Question", value=question, inline=False)
            embed.add_field(name="Answer", value=match[1], inline=False)
            embed.add_field(name="Match", value=match[0], inline=False)
            embed = discord.Embed(timestamp=tweet.created_at)
            embed.set_footer(text="Tweet Match", icon_url="https://abs.twimg.com/icons/apple-touch-icon-192x192.png")
            
            await self.channel.send(embed=embed)


    async def on_connect(self):
        print("Connection to Twitter successful!")
        
    async def on_connection_error(self):
        print("Connection to Twitter failed.")

    async def on_disconnect(self):
        print("Disconnected from Twitter.")

    async def on_errors(self, errors):
        print(errors)
        
    async def on_exception(self, exception):
        print(''.join(traceback.format_exception(type(exception), value=exception, tb=exception.__traceback__)))
        self.channel.send(embed=create_error_embed(exception))
