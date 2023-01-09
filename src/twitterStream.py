import traceback
from sqlite3 import Cursor
from typing import List,Union

import tweepy
import tweepy.asynchronous
from globals_ import *
from tweepy.streaming import StreamResponse


async def check_tweet_for_match(tweet_text: str, question: str) -> List[Union[bool, str]]:
    """
    Checks if the tweet text contains the question

    Parameters
    ----------
    tweet_text : str
    The text of the tweet

    question : str
    The question to check for

    Returns
    -------
    list[bool,str]
    A list containing a boolean value indicating if the tweet text match the question and the gpt3 answer

    """

    # Construct the query by combining the question and tweet text
    query = GPT_QUERY_BASE.format(tweet=tweet_text, question=question)

    # Use OpenAI API to check tweet for match with question
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=query,
        max_tokens=2048,
        temperature=0.5,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    # Extract answer from API response
    answer = response["choices"][0]["text"].strip().lower()

    # Return a list indicating if "yes" is in the answer and the answer itself
    return ["yes" in answer, answer]


class MyStreamListener(tweepy.asynchronous.AsyncStreamingClient):
    def __init__(self, channel: discord.channel.TextChannel, cursor: Cursor, **kwargs) -> None:
        super().__init__(
            bearer_token=TWITTER_BEARER_TOKEN, wait_on_rate_limit=True, **kwargs
        )
        self.channel = channel
        self.cursor = cursor

    async def update_rules(self, rules):
        """
        Updates the rules of the twitter stream

        Parameters
        ----------
        rules : list[tweepy.StreamRule]
        The rules to update
        """

        await self.delete_rules(rules)
        await self.add_rules(rules)

    def custom_filter(self) -> None:
        self.disconnect()
        self.task = None
        self.filter(
            expansions=["author_id"],
            user_fields=["username", "name", "profile_image_url"],
        )

    async def update_handles_from_database(self) -> None:
        """
        Updates the handles in the twitter stream to match the handles in the database

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        rules = (await self.get_rules()).data
        # print(type(rules))
        if rules is not None:
            await self.delete_rules(rules)

        self.cursor.execute("SELECT handle FROM users")
        handles = self.cursor.fetchall()

        query = ""
        query_list = []
        for handle in handles:
            # If the handle would cause the query to exceed 510 characters, add the current query to the list and reset the query
            if len(query) + len(handle[0]) > 510:
                query_list.append(query)
                query = ""
                # If the number of queries exceeds the maximum number allowed by Twitter's API, raise an exception
                if len(query_list) == 5:
                    raise UserLimitReached

            query += f"from:{handle[0]} OR "

        # Add the final query to the list
        query_list.append(query)

        # Add each query as a stream rule
        for query in query_list:
            query = query.rstrip(" OR ")
            temp_rule = tweepy.StreamRule(query)
            await self.add_rules(temp_rule)

        # print((await self.get_rules()).data)

    async def add_handle(self, handle: str) -> None:
        """
        Adds a handle to the twitter stream

        Parameters
        ----------
        handle : str
        The handle to add

        Returns
        -------
        None
        """

        rules = (await self.get_rules()).data

        # If there are no current rules, create a new rule with the handle
        if rules is None or len(rules) == 0:
            temp_rule = tweepy.StreamRule(f"from:{handle}")
            await self.add_rules(temp_rule)
            # print((await self.get_rules()).data)
            return None

        for rule in rules:
            # If the handle can be added to the current rule without exceeding 510 characters, update the rule with the handle
            if len(rule.value) + len(handle) < 510:
                new_query = rule.value + f" OR from:{handle}"
                new_rule = tweepy.StreamRule(value=new_query, id=rule.id)
                await self.update_rules(new_rule)
                # print((await self.get_rules()).data)
                return None

        # If the handle cannot be added to any of the current rules, create a new rule with the handle
        if len(rules) < 5:
            temp_rule = tweepy.StreamRule(f"from:{handle}")
            await self.add_rules(temp_rule)
            # print((await self.get_rules()).data)
            return None

        # print((await self.get_rules()).data)
        # If the number of queries exceeds the maximum number allowed by Twitter's API, raise an exception
        raise UserLimitReached

    async def remove_handle(self, handle: str) -> None:
        """
        Removes a handle from the twitter stream

        Parameters
        ----------
        handle : str
        The handle to remove

        Returns
        -------
        None
        """

        rules = (await self.get_rules()).data
        # print(type(rules))
        for rule in rules:
            # If the rule contains the handle, update the rule with the handle removed
            if f"from:{handle}" in rule.value:
                await self.delete_rules(rule)
                new_query = rule.value.replace(f"from:{handle} OR ", "")
                new_query = new_query.replace(f"from:{handle}", "")
                new_query = new_query.rstrip(" OR ")
                new_rule = tweepy.StreamRule(value=new_query, id=rule.id)
                print(await self.add_rules(new_rule))
                # print((await self.get_rules()).data)
                return

    async def on_response(self, response: StreamResponse) -> None:
        tweet = response.data
        user = response.includes["users"][0]

        # print(response)

        # Get question for tweet author from database
        self.cursor.execute("""SELECT question FROM users WHERE id=?""", (user.id,))
        question = self.cursor.fetchone()[0]

        match = await check_tweet_for_match(tweet.text, question)

        # print(f"{tweet.text} {question} {str(match[0])} {match[1]}")

        # If the tweet text match the question, create and send an embed with the tweet and answer data
        if match[0]:

            await self.channel.send("New tweet")
            embed = discord.embeds.Embed(
                title=f"{user.name} (@{user.username})",
                url=f"https://twitter.com/{user.username}/status/{tweet.id}",
                description=tweet.text,
                color=0x1DA1F2,
                timestamp=tweet.created_at,
            )
            embed.set_author(
                name="Tweet Match",
                url="https://twitter.com",
                icon_url="https://abs.twimg.com/icons/apple-touch-icon-192x192.png",
            )
            embed.set_thumbnail(url=user.profile_image_url)
            embed.add_field(name="Question", value=question, inline=False)
            embed.add_field(name="Answer", value=match[1], inline=False)
            embed.add_field(name="Match", value=match[0], inline=False)
            embed.timestamp = tweet.created_at
            embed.set_footer(
                text="Tweet Match",
                icon_url="https://abs.twimg.com/icons/apple-touch-icon-192x192.png",
            )
            await self.channel.send(embed=embed)

    async def on_connect(self) -> None:
        print("Connection to Twitter successful!")

    async def on_connection_error(self):
        print("Connection to Twitter failed.")

    async def on_disconnect(self) -> None:
        print("Disconnected from Twitter.")

    async def on_errors(self, errors):
        print(errors)

    async def on_exception(self, exception):
        print(
            "".join(
                traceback.format_exception(
                    type(exception), value=exception, tb=exception.__traceback__
                )
            )
        )
        await self.channel.send(embed=create_error_embed(exception))
