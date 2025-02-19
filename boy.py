import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, time, timedelta, timezone
import dateutil.parser


from config import BOT_TOKEN, REACTION_EMOJI, ADMIN_ROLE_NAME, WEEKLY_QUOTE_CHANNEL_ID, AUTHOR_REPEAT_PREVENTION
import database
import utils

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def format_quote_embed(quote):
    """Helper function to create a quote embed."""
    if not quote:
        return None
    quote_id, message_id, guild_id, channel_id, author_id, author_name, content, jump_url, adder_user_id, added_at = quote
    embed = discord.Embed(description=content, color=discord.Color.blurple())
    embed.set_author(name=author_name, url=jump_url)
    return embed


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    await database.create_tables()
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)
    print("------")

    # --- Fetch recent messages in each channel ---
    print("Fetching recent messages...")
    for guild in bot.guilds:
        for channel in guild.text_channels:  # Only text channels
            if channel.permissions_for(guild.me).read_message_history:  # check permissions
                try:
                    async for message in channel.history(limit=200):  # Fetch up to 200 recent messages
                        pass  # We just need to iterate to load them into the cache
                    print(f"  Fetched messages in {channel.name} (Guild: {guild.name})")
                except discord.Forbidden:
                    print(f"  No permission to read message history in {channel.name} (Guild: {guild.name})")
                except Exception as e:
                    print(f"  Error fetching messages in {channel.name} (Guild: {guild.name}): {e}")
    print("Message fetching complete.")
    # --- End of message fetching ---
    weekly_quote.start()

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    message = reaction.message
    print(f"Attempting to fetch message: {message.id} in channel: {message.channel.id}")  # add this
    try:
        message = await message.channel.fetch_message(message.id)
        print(f"Successfully fetched message: {message.id}")  # add this
    except discord.NotFound:
        print(f"Message not found: {message.id}")
        return
    except discord.Forbidden:
        print(f"Bot lacks permission to fetch message: {message.id}")
        return
    except discord.HTTPException as e:
        print(f"HTTP error fetching message: {message.id} - {e}")
        return

    # --- ADD BOT CHECK HERE ---
    if message.author.bot:
        print(f"Ignoring reaction on bot message: {message.id}")
        return  # Exit if the message author is a bot

    # Check if REACTION_EMOJI is an integer (custom emoji ID) or a string (standard emoji)
    if isinstance(REACTION_EMOJI, int):
        # Custom emoji: Use bot.get_emoji()
        if reaction.emoji == bot.get_emoji(REACTION_EMOJI):
            existing_quote = await database.get_quote_by_message_id(message.id)

            if existing_quote is None:
                await database.add_quote(
                    message.id, message.guild.id, message.channel.id, message.author.id,
                    message.author.name, message.content, message.jump_url, user.id
                )
                print(f"Quote added: {message.content}")
                embed = await format_quote_embed(await database.get_quote_by_message_id(message.id))
                if embed:
                    await message.channel.send("Quote added!", embed=embed)

            else:
                print(f"Quote already exists: {message.content}")
    elif isinstance(REACTION_EMOJI, str):
        # Standard emoji: Compare directly as strings
        if str(reaction.emoji) == REACTION_EMOJI:
            existing_quote = await database.get_quote_by_message_id(message.id)

            if existing_quote is None:
                await database.add_quote(
                    message.id, message.guild.id, message.channel.id, message.author.id,
                    message.author.name, message.content, message.jump_url, user.id
                )
                print(f"Quote added: {message.content}")
                embed = await format_quote_embed(await database.get_quote_by_message_id(message.id))
                if embed:
                   await message.channel.send("Quote added!", embed=embed)
            else:
                print(f"Quote already exists: {message.content}")

    else:
        print(f"Error: REACTION_EMOJI in config.py is of unexpected type: {type(REACTION_EMOJI)}")

@bot.tree.command(name="randomquote", description="Displays a random quote.")
async def randomquote(interaction: discord.Interaction):
    if AUTHOR_REPEAT_PREVENTION:
        last_author = await database.get_last_author(interaction.channel_id)
        if last_author:
            quote = await database.get_random_quote_not_by_author(last_author, interaction.channel_id)
        if not last_author or not quote: #if no last author or no quote found without last author, just get any random quote.
           quote = await database.get_random_quote()
    else:
        quote = await database.get_random_quote()

    embed = await format_quote_embed(quote)
    if embed:
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("No quotes found!", ephemeral=True)

@bot.tree.command(name="search", description="Searches for quotes containing a specific term.")
@app_commands.describe(term="The term to search for.")
async def search(interaction: discord.Interaction, term: str):
    print(f"Search command triggered. Term: {term}")  # Debug print

    quotes = await database.get_quotes_by_search_term(term)
    print(f"Initial database results: {quotes}")  # Debug print

    if not quotes:
        await interaction.response.send_message("No quotes found matching that term.", ephemeral=True)
        return

    fuzzy_results = utils.fuzzy_search(term, quotes, key=lambda q: q[6], threshold=50) # q[6] is the content
    print(f"Fuzzy search results: {fuzzy_results}")  # Debug print

    if not fuzzy_results:
        await interaction.response.send_message("No quotes found matching that term.", ephemeral=True)
        return

    options = []
    for quote, score in fuzzy_results[:25]: #limit to 25 options
        quote_id, message_id, guild_id, channel_id, author_id, author_name, content, jump_url, adder_user_id, added_at = quote
        label = content[:100]
        if len(content) > 100:
            label += "..."
        options.append(discord.SelectOption(label=label, value=str(message_id)))

    select = discord.ui.Select(placeholder="Select a quote", options=options)

    async def select_callback(interaction: discord.Interaction):
        selected_message_id = int(select.values[0])
        quote = await database.get_quote_by_message_id(selected_message_id)
        embed = await format_quote_embed(quote)
        await interaction.response.edit_message(embed=embed, view=None)


    select.callback = select_callback
    view = discord.ui.View()
    view.add_item(select)
    await interaction.response.send_message("Search Results:", view=view, ephemeral=True)
@bot.tree.command(name="search_author", description="Searches for quotes by a specific author.")
@app_commands.describe(author_name="The name of the author to search for.")
async def search_author(interaction: discord.Interaction, author_name: str):
    quotes = await database.get_quotes_by_author(author_name)
    if not quotes:
        await interaction.response.send_message("No quotes found by that author.", ephemeral=True)
        return

    fuzzy_results = utils.fuzzy_search(author_name, quotes, key=lambda q: q[5], threshold=60) # q[5] is author name

    if not fuzzy_results:
            await interaction.response.send_message("No quotes found by that author.", ephemeral=True)
            return
    options = []

    for quote, score in fuzzy_results[:25]:
      quote_id, message_id, guild_id, channel_id, author_id, author_name, content, jump_url, adder_user_id, added_at = quote
      label = content[:100]
      if len(content) > 100:
        label += "..."
      options.append(discord.SelectOption(label=f"{author_name}: {label}", value=str(message_id)))

    select = discord.ui.Select(placeholder="Select a quote", options=options)

    async def select_callback(interaction: discord.Interaction):
      selected_message_id = int(select.values[0])
      quote = await database.get_quote_by_message_id(selected_message_id)
      embed = await format_quote_embed(quote)
      await interaction.response.edit_message(embed=embed, view=None)

    select.callback = select_callback
    view = discord.ui.View()
    view.add_item(select)
    await interaction.response.send_message("Search Results:", view=view, ephemeral=True)

@bot.tree.command(name="manual_add", description="Manually add a quote using a message link.")
@app_commands.describe(message_link="The link to the Discord message.")
async def manual_add(interaction: discord.Interaction, message_link: str):
    try:
        # Extract guild, channel, and message IDs from the link
        link_parts = message_link.split('/')
        guild_id = int(link_parts[-3])
        channel_id = int(link_parts[-2])
        message_id = int(link_parts[-1])

        # Get the guild, channel, and message objects
        guild = bot.get_guild(guild_id)
        if not guild:
            await interaction.response.send_message("Invalid message link: Could not find the server.", ephemeral=True)
            return

        channel = guild.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message("Invalid message link: Could not find the channel.", ephemeral=True)
            return

        message = await channel.fetch_message(message_id)

    except (ValueError, IndexError):
        await interaction.response.send_message("Invalid message link format. Please provide a valid Discord message link.", ephemeral=True)
        return
    except discord.NotFound:
        await interaction.response.send_message("Message not found.  Make sure the bot is in that server and channel.", ephemeral=True)
        return
    except discord.Forbidden:
        await interaction.response.send_message("Bot lacks permission to access that message.", ephemeral=True)
        return
    except discord.HTTPException as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
        return

    # --- ADD BOT CHECK HERE ---
    if message.author.bot:
        await interaction.response.send_message("Cannot add quotes from bots.", ephemeral=True)
        return

    # Check if the quote is already in the database
    existing_quote = await database.get_quote_by_message_id(message.id)
    if existing_quote:
        await interaction.response.send_message("That quote has already been added.", ephemeral=True)
        return

    # Add the quote to the database
    await database.add_quote(
        message.id, message.guild.id, message.channel.id, message.author.id,
        message.author.name, message.content, message.jump_url, interaction.user.id
    )

    # Send confirmation message with the quote embed
    embed = await format_quote_embed(await database.get_quote_by_message_id(message.id))
    if embed:
        await interaction.response.send_message("Quote added!", embed=embed)

@bot.tree.command(name="deletequote", description="Delete a quote that you added or authored, or if you have the admin role.")
@app_commands.describe(message_link="The link to the original message of the quote.")
async def deletequote(interaction: discord.Interaction, message_link: str):
    try:
      # Extract message ID from the jump URL.  Robust handling of different URL formats.
        message_id = int(message_link.split('/')[-1])
    except (ValueError, IndexError):
        await interaction.response.send_message("Invalid message link format. Please provide a valid Discord message link.", ephemeral=True)
        return

    quote = await database.get_quote_by_message_id(message_id)
    if not quote:
        await interaction.response.send_message("Quote not found.", ephemeral=True)
        return

    quote_id, message_id, guild_id, channel_id, author_id, author_name, content, jump_url, adder_user_id, added_at = quote
    # Check if the user has permission to delete the quote
    is_admin = any(role.name == ADMIN_ROLE_NAME for role in interaction.user.roles)
    if interaction.user.id == adder_user_id or interaction.user.id == author_id or is_admin :
        await database.delete_quote(message_id)
        await interaction.response.send_message("Quote deleted successfully!", ephemeral=True)
    else:
        await interaction.response.send_message("You don't have permission to delete this quote.", ephemeral=True)

@tasks.loop(time=time(hour=12, minute=0, second=0, tzinfo=timezone.utc)) # 12:00 PM UTC
async def weekly_quote():
    now = datetime.now(timezone.utc)
    if now.weekday() == 0:  # Check if it's Monday (0 = Monday, 6 = Sunday)
        channel = bot.get_channel(WEEKLY_QUOTE_CHANNEL_ID)
        if channel:
            quote = await database.get_random_quote()
            embed = await format_quote_embed(quote)
            if embed:
                await channel.send(embed=embed)

# --- Run the Bot ---
bot.run(BOT_TOKEN)
