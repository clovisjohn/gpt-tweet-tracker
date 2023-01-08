# gpt-tweet-tracker

A Discord bot that can track Twitter handles and notify you when they tweet a message that matches a specified question.

## Requirements

- Python 3.7 or higher
- The packages listed in `requirements.txt`
- A Discord bot account and token
- A Twitter Bearer Token
- An OpenAI API key

## Setup

1. Clone the repository and install the required packages:
```
git clone https://github.com/YOUR_USERNAME/Discord-Tweet-Match
pip install -r requirements.txt
```

	
2. Create a `.env` file in the root directory of the project and add the following variables:

| Variable                  | What it is                                                            |
| ------------------------- | ----------------------------------------------------------------------|
| TWITTER_BEARER_TOKEN      | Your  twitter bearer token                        |
| OPENAI_API_KEY       | Your  OpenAI api key                                                |
| DISCORD_BOT_TOKEN | The token of the discord bot that you will use           |
| DISCORD_CHANNEL_ID  | The id of the channel where the bot will send tweets                                        |
	
	
3. Run the bot:
```
python main.py
```

## Commands
```
!start - Start the bot
!stop - Stop the bot
!list - Lists all the users being tracked and their respective questions
!remove_user - Remove a user from the database.
!add_user - Add a new user to the database
!help - Show help for the bot
```

## Question to filter tweets

The question should be a valid GPT-3 query in the [Prompt Format](https://beta.openai.com/docs/api-reference/completions/create#prompt-format) specified in the OpenAI API documentation. It should be a question that can be answered with Yes or No.

Here are a few examples of prompts that you might use with this module:

- `"Is this tweet relevant to my interests?"`: This prompt could be used to filter tweets based on relevance to a certain topic or theme.
- `"Is this tweet appropriate for all audiences?"`: This prompt could be used to filter out tweets that might be inappropriate or offensive.
- `"Does this tweet contain useful information?"`: This prompt could be used to filter out tweets that might be spam or low-quality content.
