**Discord Quote Bot**

This bot allows users to save, manage, and share memorable quotes from your Discord server. It provides features for adding quotes via reactions and a manual command, robust searching, and displaying a weekly automated quote.

**Features:**

1. **Quote Saving:**

   - **Reaction-Based:** Users can save a Discord message as a quote by reacting to the message with a designated emoji (configurable, defaults to 💬). 
   - **Manual Addition:**  A `/manual_add` slash command allows users to add quotes by providing a direct Discord message link. This might be useful for really old messages.
   - **Bot Message Prevention:** The bot will not add quotes from messages authored by other bots.

2. **Quote Retrieval:**

   - `/randomquote`: Displays a random quote from the database. The quote is presented in an embedded message, with the author's name linked to the original message on Discord.
   - **Author Variety (Toggleable):**  By default, the bot avoids showing quotes from the same author twice in a row in the same channel when using `/randomquote`. This can be disabled in the configuration.

3. **Quote Searching:**

   - ```
     /search term
     ```

     : Searches for quotes containing the specified 

     ```
     term
     ```

     .

     - **Fuzzy Matching:** Uses fuzzy matching to find quotes even if the search term contains minor typos.
     - Results are displayed in a dropdown menu for easy selection.

   - `/search_author author_name`: Searches specifically for quotes by a given `author_name`. Also employs fuzzy searching. Results are presented in a dropdown.

4. **Quote Deletion:**

   - A quote can be deleted by:
     - The user who originally added the quote to the bot.
     - The author of the original quoted message.
     - Users with a specific, designated admin role (configurable, defaults to "Quote Moderator").
   - Deletion is triggered by the `/deletequote` command, providing the message link

5. **Scheduled Quote of the Week:**

   - Every Monday at 12:00 PM UTC, the bot automatically posts a random quote to a designated channel (configurable).

**Installation Guide:**

**Prerequisites:**

- **Python 3.8+:**  Make sure you have Python 3.8 or a newer version installed.  Download from [python.org](https://www.google.com/ur<0>l?sa=E&source=gmail&q=https://www.python.org/).
- Discord Bot Token:
  - Go to the [Discord Developer Portal](https://www.google.com/url?sa=E&source=gmail&q=https://discord.com/developers/applications).
  - Create a new application.
  - Go to the "Bot" section and add a bot.
  - Copy the bot token (keep this secret!).

**Steps:**

1. **Download the Code:** Obtain the code (e.g., by cloning a Git repository or downloading a zip file) for these four files:

   - `bot.py`
   - `config.py`
   - `database.py`
   - `utils.py`

   

2. **Install Dependencies:** Open a terminal or command prompt in the directory where you saved the files and run:

   Bash

   ```
   pip install discord.py aiosqlite fuzzywuzzy python-dateutil python-Levenshtein
   pip install --upgrade certifi
   ```

   

3. **Configure the Bot:**

   - Open the `config.py` file.

   - **`BOT_TOKEN`:** Replace `"YOUR_BOT_TOKEN_HERE"` with your actual bot token from the Discord Developer Portal.

   - **`DATABASE_FILE`:** (Optional) Change the database file name if desired (defaults to `quotes.db`).

   - `REACTION_EMOJI`:

       Set the emoji to use for saving quotes:

     - **Standard Emoji:** Use the emoji character directly (e.g., `REACTION_EMOJI = "👍"`).
     - **Custom Emoji:** Use the *integer* ID of the custom emoji (e.g., `REACTION_EMOJI = 123456789012345678`).  You can get the ID by typing `\:your_emoji_name:` in Discord.

     

   - **`ADMIN_ROLE_NAME`:**  Set the name of the Discord role that will have permission to delete any quote (e.g., `ADMIN_ROLE_NAME = "Quote Moderator"`).  Make sure this role exists on your server.

   - **`WEEKLY_QUOTE_CHANNEL_ID`:** Replace `123456789012345678` with the *numeric ID* of the channel where you want the weekly quote to be posted. You can get a channel ID by enabling Developer Mode in Discord (Settings -> App Settings -> Advanced) and then right-clicking on the channel and selecting "Copy ID".

   - **`AUTHOR_REPEAT_PREVENTION`:** Set to True (default) to prevent same author twice in a row. False allows.

   

4. **Run the Bot:**

   - Open a terminal or command prompt in the directory where you saved the files.
   - Run the command: `python bot.py`

5. **Invite the Bot to Your Server:**

   

   - Go to the Discord Developer Portal, select your application.
   - Go to "OAuth2" -> "URL Generator".
   - Select the "bot" scope.
   - Select the following permissions:
     - `Read Messages/View Channels`
     - `Send Messages`
     - `Embed Links`
     - `Read Message History`
     - `Add Reactions`
     - `Manage Messages` (needed for reaction-based deletion if implemented, and to delete with `/deletequote`).
   - Copy the generated URL and paste it into your browser.  Follow the prompts to invite the bot to your server.

   

6. **Initial Setup/Sync**

   - After starting the bot, you may want to run `/search` or `/randomquote` at least once. This ensures all slash commands have synced to your discord server.

   

**Usage:**

- **Adding Quotes**:
  - **Reaction:** React to a message with the configured `REACTION_EMOJI`.
  - **Manual:** Use the `/manual_add <message_link>` command.  Get the message link by right-clicking on a message and selecting "Copy Message Link".
- **Viewing Random Quotes:** Use the `/randomquote` command.
- **Searching Quotes**:
  - `/search <term>`: Search for quotes containing a specific term.
  - `/search_author <author_name>`: Search for quotes by a specific author.
- **Deleting Quotes**
  - `/deletequote <message_link>`: Deletes a quote given a valid message link.
- **Weekly Quote:** The bot will automatically post a random quote every Monday at 12:00 PM UTC to the configured channel.



**Troubleshooting:**

- Bot Doesn't Respond:
  - Make sure the bot is running (check your terminal for errors).
  - Make sure the bot token in `config.py` is correct.
  - Make sure the bot has been invited to your server with the correct permissions.
- Reaction doesn't work on messages sent before bot startup:
  - Use `/manual_add` command.
