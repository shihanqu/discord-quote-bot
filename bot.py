#!/usr/bin/env python3
# v1.2
import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, time, timezone

from config import BOT_TOKEN, REACTION_EMOJI, ADMIN_ROLE_NAME, AUTHOR_REPEAT_PREVENTION
import database

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# In-memory dictionary to track last shown author per channel
last_shown_authors = {}

RECURRING_QUOTES = [
    {
        "name": "weekly_monday_quote",
        "time": time(hour=12, minute=0, second=0, tzinfo=timezone.utc),
        "day": 0,
        "channel_id": 123456789012345678,  # Replace with your actual channel ID
        "message": "Happy Monday friends"
    },
    {
        "name": "wednesday_quote",
        "time": time(hour=15, minute=30, second=0, tzinfo=timezone.utc),
        "day": 2,
        "channel_id": 123456789012345678,
        "message": "Hump Day Wisdom"
    },
]

async def format_quote_embed(quote):
    """Helper function to create a quote embed, including attachments if present."""
    if not quote:
        return None
    quote_id, message_id, guild_id, channel_id, author_id, author_name, content, jump_url, adder_user_id, added_at = quote

    embed = discord.Embed(
        description=content if content else "[Image-only quote]",
        color=discord.Color.blurple()
    )
    embed.set_author(name=author_name, url=jump_url)

    guild = bot.get_guild(guild_id)
    if guild:
        channel = guild.get_channel(channel_id)
        if channel:
            try:
                message = await channel.fetch_message(message_id)
                if message.attachments:
                    for attachment in message.attachments:
                        if attachment.content_type.startswith('image/'):
                            embed.set_image(url=attachment.url)
                            break
            except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
                print(f"Failed to fetch message for attachment: {e}")

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
    for recurring_quote in RECURRING_QUOTES:
        task = getattr(tasks, recurring_quote["name"])
        task.start()

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        print(f"Guild not found: {payload.guild_id}")
        return
    channel = guild.get_channel(payload.channel_id)
    if not channel:
        print(f"Channel not found: {payload.channel_id}")
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.NotFound:
        print(f"Message not found: {payload.message_id}")
        return
    except discord.Forbidden:
        print(f"Bot lacks permission to fetch message: {payload.message_id}")
        return
    except discord.HTTPException as e:
        print(f"HTTP error fetching message: {payload.message_id} - {e}")
        return

    if message.author.bot:
        print(f"Ignoring reaction on bot message: {message.id}")
        return

    if isinstance(REACTION_EMOJI, int):  # Custom Emoji
        if payload.emoji.id == REACTION_EMOJI:
            existing_quote = await database.get_quote_by_message_id(message.id)
            if existing_quote is None:
                await database.add_quote(message.id, guild.id, channel.id, message.author.id, message.author.name,
                                         message.content, message.jump_url, payload.user_id)
                print(f"Quote added: {message.content}")
                embed = await format_quote_embed(await database.get_quote_by_message_id(message.id))
                if embed:
                    await channel.send("Immortalized", embed=embed)
            else:
                print("Quote already exists")
    elif isinstance(REACTION_EMOJI, str):  # Standard Emoji
        if payload.emoji.name == REACTION_EMOJI:
            existing_quote = await database.get_quote_by_message_id(message.id)
            if existing_quote is None:
                await database.add_quote(message.id, guild.id, channel.id, message.author.id, message.author.name,
                                         message.content, message.jump_url, payload.user_id)
                print(f"Quote added: {message.content}")
                embed = await format_quote_embed(await database.get_quote_by_message_id(message.id))
                if embed:
                    await channel.send("Quote added yabish!", embed=embed)
            else:
                print("Quote already exists")
    else:
        print("Emoji configuration error")

@bot.tree.command(name="randomquote", description="Displays a random quote.")
async def randomquote(interaction: discord.Interaction):
    quote = None
    channel_id = interaction.channel_id
    if AUTHOR_REPEAT_PREVENTION:
        last_author = last_shown_authors.get(channel_id)
        print(f"Last shown author in channel {channel_id}: {last_author}")
        if last_author:
            available_count = await database.get_available_quotes_count(last_author, channel_id)
            print(f"Quotes available excluding author {last_author} in channel {channel_id}: {available_count}")
            quote = await database.get_random_quote_not_by_author(last_author, channel_id)
            if quote is None:
                print(f"No quotes found excluding author {last_author} in channel {channel_id}, falling back")
                quote = await database.get_random_quote()
        else:
            quote = await database.get_random_quote()
    else:
        quote = await database.get_random_quote()

    if quote:
        quote_id, message_id, guild_id, _, author_id, author_name, content, jump_url, _, _ = quote
        last_shown_authors[channel_id] = author_id  # Update last shown author
        print(f"Selected quote: {quote}")
        embed = await format_quote_embed(quote)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("No quotes found!", ephemeral=True)

@bot.tree.command(name="search", description="Searches for quotes containing a specific term.")
@app_commands.describe(term="The term to search for.")
async def search(interaction: discord.Interaction, term: str):
    quotes = await database.get_quotes_by_search_term(term)
    if not quotes:
        await interaction.response.send_message("No quotes found matching that term.", ephemeral=True)
        return

    options = []
    for quote in quotes[:25]:
        quote_id, message_id, guild_id, channel_id, author_id, author_name, content, jump_url, adder_user_id, added_at = quote
        label = (content or "[Image-only quote]")[:100]  # Ensure label is never empty or too long
        if len(label) < 1:  # Edge case fallback
            label = "[Empty Quote]"
        options.append(discord.SelectOption(label=label, value=str(message_id)))

    select = discord.ui.Select(placeholder="Select a quote", options=options)

    async def select_callback(interaction: discord.Interaction):
        selected_message_id = int(select.values[0])
        quote = await database.get_quote_by_message_id(selected_message_id)
        embed = await format_quote_embed(quote)
        await interaction.channel.send(embed=embed)
        await interaction.response.edit_message(content="Quote displayed to the channel!", view=None)

    select.callback = select_callback
    view = discord.ui.View()
    view.add_item(select)
    await interaction.response.send_message("Search Results:", view=view, ephemeral=True)

@bot.tree.command(name="search_author", description="Searches for quotes by selecting an author from a dropdown.")
async def search_author(interaction: discord.Interaction):
    authors = await database.get_all_unique_authors()
    if not authors:
        await interaction.response.send_message("No authors found in the quote database.", ephemeral=True)
        return

    options = []
    for author_id, author_name in authors[:25]:
        options.append(discord.SelectOption(label=author_name, value=str(author_id)))

    select = discord.ui.Select(placeholder="Select an author", options=options)

    async def select_callback(interaction: discord.Interaction):
        selected_author_id = int(select.values[0])
        quotes = await database.get_quotes_by_author_id(selected_author_id)
        if not quotes:
            await interaction.response.edit_message(content="No quotes found for this author.", view=None)
            return

        quote_options = []
        for quote in quotes[:25]:
            quote_id, message_id, guild_id, channel_id, author_id, author_name, content, jump_url, adder_user_id, added_at = quote
            label = (content or "[Image-only quote]")[:100]  # Ensure label is never empty or too long
            if len(label) < 1:
                label = "[Empty Quote]"
            quote_options.append(discord.SelectOption(label=label, value=str(message_id)))

        quote_select = discord.ui.Select(placeholder="Select a quote", options=quote_options)

        async def quote_select_callback(interaction: discord.Interaction):
            selected_message_id = int(quote_select.values[0])
            quote = await database.get_quote_by_message_id(selected_message_id)
            embed = await format_quote_embed(quote)
            await interaction.channel.send(embed=embed)
            await interaction.response.edit_message(content="Quote displayed to the channel!", view=None)

        quote_select.callback = quote_select_callback
        quote_view = discord.ui.View()
        quote_view.add_item(quote_select)
        await interaction.response.edit_message(content="Quotes by selected author:", view=quote_view)

    select.callback = select_callback
    view = discord.ui.View()
    view.add_item(select)
    await interaction.response.send_message("Select an author:", view=view, ephemeral=True)

@bot.tree.command(name="deletequote", description="Delete a quote that you added or authored, or if you have the admin role.")
@app_commands.describe(message_link="The link to the original message of the quote.")
async def deletequote(interaction: discord.Interaction, message_link: str):
    try:
        message_id = int(message_link.split('/')[-1])
    except (ValueError, IndexError):
        await interaction.response.send_message(
            "Invalid message link format. Please provide a valid Discord message link.", ephemeral=True)
        return

    quote = await database.get_quote_by_message_id(message_id)
    if not quote:
        await interaction.response.send_message("Quote not found.", ephemeral=True)
        return

    quote_id, message_id, guild_id, channel_id, author_id, author_name, content, jump_url, adder_user_id, added_at = quote
    is_admin = any(role.name == ADMIN_ROLE_NAME for role in interaction.user.roles)
    if interaction.user.id == adder_user_id or interaction.user.id == author_id or is_admin:
        await database.delete_quote(message_id)
        await interaction.response.send_message("Quote deleted successfully!", ephemeral=True)
    else:
        await interaction.response.send_message("You don't have permission to delete this quote.", ephemeral=True)

@bot.tree.command(name="manual_add", description="Manually add a quote using a message link.")
@app_commands.describe(message_link="The link to the Discord message.")
async def manual_add(interaction: discord.Interaction, message_link: str):
    try:
        link_parts = message_link.split('/')
        guild_id = int(link_parts[-3])
        channel_id = int(link_parts[-2])
        message_id = int(link_parts[-1])

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
        await interaction.response.send_message(
            "Invalid message link format. Please provide a valid Discord message link.", ephemeral=True)
        return
    except discord.NotFound:
        await interaction.response.send_message("Message not found. Make sure the bot is in that server and channel.",
                                                ephemeral=True)
        return
    except discord.Forbidden:
        await interaction.response.send_message("Bot lacks permission to access that message.", ephemeral=True)
        return
    except discord.HTTPException as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
        return

    if message.author.bot:
        await interaction.response.send_message("Cannot add quotes from bots.", ephemeral=True)
        return

    existing_quote = await database.get_quote_by_message_id(message.id)
    if existing_quote:
        await interaction.response.send_message("That quote has already been added.", ephemeral=True)
        return

    await database.add_quote(
        message.id, message.guild.id, message.channel.id, message.author.id,
        message.author.name, message.content, message.jump_url, interaction.user.id
    )

    embed = await format_quote_embed(await database.get_quote_by_message_id(message.id))
    if embed:
        await interaction.response.send_message("Quote added!", embed=embed)

# Commented out test command (confirmed working)
# @bot.tree.command(name="test_recurring_quote", description="Test a recurring quote message in the current channel.")
# async def test_recurring_quote(interaction: discord.Interaction):
#     config = RECURRING_QUOTES[0]  # Picks "Happy Monday FRAG friends" by default
#     quote = await database.get_random_quote()
#     embed = await format_quote_embed(quote)
#     if embed:
#         await interaction.channel.send(config["message"], embed=embed)
#     else:
#         await interaction.channel.send("No quotes found to test!")
#     await interaction.response.send_message("Triggered a test recurring quote!", ephemeral=True)

def create_recurring_quote_task(config):
    @tasks.loop(time=config["time"])
    async def recurring_quote_task():
        now = datetime.now(timezone.utc)
        if now.weekday() == config["day"]:
            channel = bot.get_channel(config["channel_id"])
            if channel:
                quote = await database.get_random_quote()
                embed = await format_quote_embed(quote)
                if embed:
                    await channel.send(config["message"], embed=embed)

    recurring_quote_task.__name__ = config["name"]
    return recurring_quote_task

for recurring_quote in RECURRING_QUOTES:
    setattr(tasks, recurring_quote["name"], create_recurring_quote_task(recurring_quote))

bot.run(BOT_TOKEN)
