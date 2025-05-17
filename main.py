import os
import asyncio
import time
import datetime
from datetime import datetime as dt
import requests
from discord import Client
from discord.errors import HTTPException
from dotenv import load_dotenv
from collections import defaultdict

# Global collection tracking
token_collections = defaultdict(int)
collect_again_messages = []
failed_collections = []  # Track failed collections

load_dotenv()  # Load from .env

# Token configuration with multiple tokens support
MASTER_TOKENS = [t.strip() for t in os.getenv("MASTER_TOKEN", "").split(",") if t.strip()]
TOKENS_5K = [t.strip() for t in os.getenv("TOKEN_5K", "").split(",") if t.strip()]
TOKENS_15K = [t.strip() for t in os.getenv("TOKEN_15K", "").split(",") if t.strip()]
TOKENS_30K = [t.strip() for t in os.getenv("TOKEN_30K", "").split(",") if t.strip()]
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "1369318379218796605"))

START_TIME = time.time()

# Combine all tokens and create a mapping for their types
TOKEN_TYPE_MAP = {
    token: "master" for token in MASTER_TOKENS
}
TOKEN_TYPE_MAP.update({
    token: "5k" for token in TOKENS_5K
})
TOKEN_TYPE_MAP.update({
    token: "15k" for token in TOKENS_15K
})
TOKEN_TYPE_MAP.update({
    token: "30k" for token in TOKENS_30K
})

TOKENS = list(TOKEN_TYPE_MAP.keys())
COMMISSION_USER_ID = int(os.getenv("COMMISSION_USER_ID", "1236292707371057216"))  # Default to @aloramiaa if not specified
CLIENT_TIMEOUT = 120  # Timeout in seconds

async def execute_command_with_retry(command, channel, **kwargs):
    max_retries = 3
    base_delay = 2

    for attempt in range(max_retries):
        try:
            await command.__call__(channel=channel, **kwargs)
            return True
        except HTTPException as e:
            if e.status == 429:
                retry_after = e.response.headers.get('Retry-After', base_delay)
                retry_after = float(retry_after)
                print(f"Rate limited. Waiting {retry_after} seconds...")
                await asyncio.sleep(retry_after + 1)  # Add 1 second buffer
            else:
                raise
        except Exception as e:
            print(f"Error executing command: {e}")
            if attempt == max_retries - 1:
                return False
            await asyncio.sleep(base_delay * (attempt + 1))
    return False

async def send_webhook_update(success_count, total_count, error_messages=None):
    end_time = time.time()
    duration = round(end_time - START_TIME, 2)
    current_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate total collections by token type
    total_5k = sum(amount for token, amount in token_collections.items() if TOKEN_TYPE_MAP.get(token) == "5k")
    total_15k = sum(amount for token, amount in token_collections.items() if TOKEN_TYPE_MAP.get(token) == "15k")
    total_30k = sum(amount for token, amount in token_collections.items() if TOKEN_TYPE_MAP.get(token) == "30k")
    collection_details = []
    if total_5k > 0:
        collection_details.append(f"5k Tokens: :europa_rp~2:{total_5k:,}")
    if total_15k > 0:
        collection_details.append(f"15k Tokens: :europa_rp~2:{total_15k:,}")
    if total_30k > 0:
        collection_details.append(f"30k Tokens: :europa_rp~2:{total_30k:,}")
    
    # Calculate success rate percentage
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0
    status_color = "\u001b[2;32m" if success_rate > 85 else "\u001b[2;33m" if success_rate > 60 else "\u001b[2;31m"
    
    embed = {
        "title": "╔══・👑 Europa Farm Report ・══╗",
        "description": f"```ansi\n\u001b[2;36m┌─────────────── Stats Overview ───────────────┐\u001b[0m\n\u001b[2;37m│\u001b[0m Success Rate: {status_color}{success_rate:.1f}%\u001b[0m\n\u001b[2;37m│\u001b[0m Session Duration: \u001b[2;33m{duration:.1f}s\u001b[0m\n\u001b[2;37m│\u001b[0m Active Tokens: \u001b[2;36m{total_count}\u001b[0m\n\u001b[2;36m└───────────────────────────────────────────┘\u001b[0m```",
        "color": 0x2b2d31,  # Discord dark theme color
        "fields": [
            {
                "name": "📊 Collection Status",
                "value": f"```ansi\n{status_color}✓ {success_count}/{total_count}\u001b[0m accounts processed\n\u001b[2;37m⮑\u001b[0m Current Session: \u001b[2;36m{dt.now().strftime('%I:%M %p')}\u001b[0m```",
                "inline": True
            },
            {
                "name": "⚡ Performance",
                "value": f"```ansi\n\u001b[2;33m⌛ {(duration/total_count):.1f}s\u001b[0m per account\n\u001b[2;37m⮑\u001b[0m Started: \u001b[2;36m{dt.fromtimestamp(START_TIME).strftime('%I:%M %p')}\u001b[0m```",
                "inline": True
            }
        ],
        "footer": {
            "text": f"Europa Farm Bot • Session {current_time}"
        }
    }

    # Add collection details if any
    if collection_details:
        # Calculate total amount across all token types
        total_amount = total_5k + total_15k + total_30k
        collection_header = f"\u001b[2;36m┌─────────── Collection Analytics ───────────┐\u001b[0m\n"
        collection_details_formatted = []
        
        if total_5k > 0:
            collection_details_formatted.append(f"\u001b[2;37m│\u001b[0m 5k Tokens   ➜ :europa_rp~2:\u001b[2;33m{total_5k:,}\u001b[0m")
        if total_15k > 0:
            collection_details_formatted.append(f"\u001b[2;37m│\u001b[0m 15k Tokens  ➜ :europa_rp~2:\u001b[2;33m{total_15k:,}\u001b[0m")
        if total_30k > 0:
            collection_details_formatted.append(f"\u001b[2;37m│\u001b[0m 30k Tokens  ➜ :europa_rp~2:\u001b[2;33m{total_30k:,}\u001b[0m")
        
        collection_footer = f"\u001b[2;37m│\u001b[0m Total      ➜ :europa_rp~2:\u001b[2;32m{total_amount:,}\u001b[0m\n\u001b[2;36m└────────────────────────────────────────┘\u001b[0m"
        
        embed["fields"].append({
            "name": "💰 Collection Analytics",
            "value": f"```ansi\n{collection_header}{chr(10).join(collection_details_formatted)}\n{collection_footer}```",
            "inline": False
        })

    # Add collect again messages if any
    if collect_again_messages:
        formatted_delays = []
        for msg in collect_again_messages:
            # Remove the ```username part and ending ```
            parts = msg.replace("```", "").split("\n", 1)
            if len(parts) > 1:
                username = parts[0].strip()
                cooldowns = parts[1].strip().split("\n")
                
                # Format each cooldown line with proper indentation
                cooldown_lines = []
                for cooldown in cooldowns:
                    if cooldown.startswith("General Cooldown:"):
                        cooldown_lines.append(f"\u001b[2;37m│\u001b[0m {username}: {cooldown}")
                    else:
                        cooldown_lines.append(f"\u001b[2;37m│\u001b[0m {username} | {cooldown}")
                formatted_delays.extend(cooldown_lines)
        
        if formatted_delays:
            cooldown_header = "\u001b[2;36m┌─────────── Collection Cooldowns ───────────┐\u001b[0m\n"
            cooldown_footer = "\u001b[2;36m└────────────────────────────────────────┘\u001b[0m"
            
            embed["fields"].append({
                "name": "⌛ Collection Cooldowns",
                "value": f"```ansi\n{cooldown_header}{chr(10).join(formatted_delays)}\n{cooldown_footer}```",
                "inline": False
            })
    
    # Add failed collections if any
    if failed_collections:
        fails_header = "\u001b[2;36m┌─────────── Failed Operations ───────────┐\u001b[0m\n"
        formatted_fails = [f"\u001b[2;37m│\u001b[0m ❌ {fail}" for fail in failed_collections]
        fails_footer = "\u001b[2;36m└────────────────────────────────────────┘\u001b[0m"
        
        embed["fields"].append({
            "name": "⚠️ Error Report",
            "value": f"```ansi\n{fails_header}{chr(10).join(formatted_fails)}\n{fails_footer}```",
            "inline": False
        })
    
    if error_messages:
        formatted_errors = [f"❯ {error}" for error in error_messages]
        embed["fields"].append({
            "name": "⚠️ Error Log",
            "value": f"```ansi\n\u001b[2;33m{chr(10).join(formatted_errors)}\u001b[0m```",
            "inline": False
        })
    
    payload = {
        "embeds": [embed]
    }
    
    try:
        requests.post(WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"Failed to send webhook: {e}")

async def run_client(token):
    client = Client()
    done = asyncio.Event()
    success = False
    error_message = None
    collected_amount = 0
    message_received = asyncio.Event()  # Event to track message receipt
    command_start_time = time.time()  # Track command execution time

    def log_message(user, action, details="", level="INFO"):
        timestamp = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        colors = {
            "INFO": "\033[92m",  # Green
            "WARN": "\033[93m",  # Yellow
            "ERROR": "\033[91m",  # Red
            "DEBUG": "\033[94m",  # Blue
            "SUCCESS": "\033[92m",  # Green
        }
        reset_color = "\033[0m"
        
        color = colors.get(level, colors["INFO"])
        print(f"{color}[{timestamp}] [{level}] [{user}] {action} {details}{reset_color}")

    def get_response_type(self, description):
        """Helper function to identify the type of bot response"""
        if not description:
            return "unknown"
        if "<:stopwatch:" in description and "You can next work" in description:
            return "work_cooldown"
        if "<:xmark:" in description and "You can collect income again" in description:
            return "collect_delay"
        if "Role income successfully collected!" in description:
            return "collection_success"
        if "Successfully transferred" in description:
            return "payment_confirm"
        if "Deposited" in description:
            return "deposit_confirm"
        if "❌" in description:
            return "failed_collection"
        return "unrelated"

    @client.event
    async def on_message(message):
        nonlocal collected_amount
        if message.channel.id == CHANNEL_ID:  # Use the channel ID from environment
            # Only process messages from UnbelievaBoat bot
            if message.author.id != 292953664492929025:  # UnbelievaBoat's ID
                return
                
            # More detailed logging for all incoming messages
            log_message(client.user, "DEBUG", f"Received message from UnbelievaBoat", "DEBUG")
                
            # Check message in multiple ways
            is_response_for_user = False
            message_content = message.content
            embed_author_name = None
            embed_description = None

            # Get content from embeds if they exist
            if message.embeds:
                embed = message.embeds[0]  # We only need to check the first embed
                if embed.author:
                    embed_author_name = embed.author.name
                if embed.description:
                    embed_description = embed.description
                
                # Log all embeds for debugging
                if embed_author_name and embed_description:
                    # Log the full embed message content
                    log_message(client.user, "DEBUG", f"Received embed from {embed_author_name}:\n{embed_description}", "DEBUG")
                    
                # For collection response, check if the message is for this user
                if embed_author_name and embed_description:
                    # Only process if the message is for this user
                    if str(client.user) == embed_author_name:
                        log_message(client.user, "DEBUG", f"Processing embed for {client.user}", "DEBUG")
                        
                        # Check for various response types
                        if "<:stopwatch:" in embed_description and "You can next work" in embed_description:
                            is_response_for_user = True
                            message_received.set()
                            return
                        elif "You can collect income again" in embed_description:
                            is_response_for_user = True
                            collected_amount = 0
                            
                            # Parse delay times with proper formatting
                            formatted_message = []
                            
                            # First try to get the general cooldown from the first line
                            first_line = embed_description.split('\n')[0]
                            if "You can collect income again" in first_line:
                                formatted_message.append(f"General Cooldown: {first_line.split('in')[-1].strip()}")
                            
                            for line in embed_description.split('\n'):
                                # Skip empty lines or the header
                                if not line.strip() or "You can collect income again" in line:
                                    continue
                                    
                                try:
                                    # Check if this is a role delay line in any format
                                    if ' - @' in line and '(cash) in' in line:
                                        # Extract role number (e.g., "1 - ")
                                        role_num = line.split(' - ')[0].strip()
                                        
                                        # Extract role name
                                        role_name = line.split(' - @')[1].split('(cash)')[0].strip()
                                        
                                        # Extract delay time
                                        if 'in' in line:
                                            delay_time = line.split('in')[-1].strip()
                                        else:
                                            delay_time = "unknown time"
                                        
                                        # Try to extract amount - first check for emoji format
                                        if ':europa_rp~2:' in line:
                                            amount_str = line.split(':europa_rp~2:')[1].split('(cash)')[0].strip()
                                        else:
                                            # Extract amount as the last number before (cash)
                                            parts = line.split('(cash)')[0].strip().split()
                                            amount_str = next((part for part in reversed(parts) 
                                                             if part.replace(',', '').isdigit()), '0')
                                        
                                        # Format the message
                                        formatted_message.append(
                                            f"{role_num} - @{role_name} - {amount_str} available in {delay_time}"
                                        )
                                except Exception as e:
                                    log_message(client.user, "ERROR", f"Failed to parse delay line: {line} - {str(e)}", "DEBUG")
                                    continue
                        
                            collect_again_messages.append(f"```{client.user}\n" + "\n".join(formatted_message) + "```")
                            
                            # Get first role's delay using new parsing method
                            first_line = next((line for line in embed_description.split('\n') if '<@&' in line and ':europa_rp~2:' in line), None)
                            if first_line:
                                try:
                                    timestamp_str = first_line.split('<t:')[1].split(':R>')[0].strip()
                                    # Convert Unix timestamp to readable format
                                    readable_time = dt.fromtimestamp(int(timestamp_str)).strftime("%Y-%m-%d %H:%M:%S")
                                    log_message(client.user, "COLLECT DELAY", f"Collection available at {readable_time}", "WARN")
                                except Exception as e:
                                    log_message(client.user, "ERROR", f"Failed to parse first delay: {str(e)}", "DEBUG")
                            message_received.set()
                            return
                        elif ("Role income successfully collected!" in embed_description) or ("<:check:" in embed_description and "Role income successfully collected!" in embed_description):
                            is_response_for_user = True
                            log_message(client.user, "DEBUG", f"Found collection success message!", "DEBUG")
                            cash_amounts = []
                            
                            # Parse successful collection amounts for the new format
                            for line in embed_description.split('\n'):
                                # Skip empty lines and the success message line
                                if not line.strip() or "Role income successfully collected!" in line:
                                    continue
                                    
                                try:
                                    # New format: `1` - <@&ROLEID> <:europa_rp:1144393670053875772>25,000 (cash)
                                    if ('`' in line or ' - <@&') and '<:europa_rp:' in line and '(cash)' in line:
                                        # Extract the amount between the emoji and (cash)
                                        emoji_id = '1144393670053875772'  # The specific Europa RP emoji ID
                                        amount_str = line.split(f'<:europa_rp:{emoji_id}>')[1].split('(cash)')[0].strip()
                                        # Clean and parse the amount
                                        amount = int(amount_str.replace(',', ''))
                                        cash_amounts.append(amount)
                                        log_message(client.user, "DEBUG", f"Parsed amount (new format): {amount:,}", "DEBUG")
                                        continue

                                    # Fallback to old format with :europa_rp~2:
                                    elif ':europa_rp~2:' in line and '(cash)' in line:
                                        amount_str = line.split(':europa_rp~2:')[1].split('(cash)')[0].strip()
                                        amount = int(amount_str.replace(',', ''))
                                        cash_amounts.append(amount)
                                        log_message(client.user, "DEBUG", f"Parsed amount (old format): {amount:,}", "DEBUG")
                                        continue
                                    
                                except Exception as e:
                                    log_message(client.user, "ERROR", f"Failed to parse amount from line: {line} - {str(e)}", "DEBUG")
                                    continue
                            
                            collected_amount = sum(cash_amounts)
                            token_collections[token] = collected_amount
                            log_message(client.user, "COLLECTED", f"💸 {collected_amount:,} cash from {len(cash_amounts)} roles", "SUCCESS")
                            message_received.set()
                            return
                        elif "<:check:" in embed_description and "Deposited" in embed_description:
                            is_response_for_user = True
                            message_received.set()
                            return
                        elif "<:xmark:" in embed_description and "You don't have any money to deposit!" in embed_description:
                            is_response_for_user = True
                            message_received.set()
                            return

            # Process regular messages if needed
            if message_content:
                if str(client.user) in message_content and "You can collect income again" in message_content:
                    is_response_for_user = True
                    collected_amount = 0                            # Format each line of the message for better readability
                    formatted_message = []
                    for line in message_content.split('\n'):
                        if not line.strip():  # Skip empty lines
                            continue
                            
                        # First line is usually the general cooldown message
                        if "You can collect income again" in line:
                            cooldown = line.split("in")[-1].strip() if "in" in line else "unknown time"
                            formatted_message.append(f"General Cooldown: {cooldown}")
                            continue
                            
                        # Role-specific cooldown lines
                        if ' - @' in line and '(cash)' in line:
                            try:
                                # Extract role number (e.g., "1 - ")
                                role_num = line.split(' - ')[0].strip()
                                
                                # Extract role name
                                role_info = line.split(' - @')[1]
                                role_name = role_info.split('(cash)')[0].strip()
                                
                                # Extract amount - look for the number before (cash)
                                amount = "0"
                                parts = role_info.split('(cash)')[0].strip().split()
                                for part in reversed(parts):
                                    if part.replace(',', '').isdigit():
                                        amount = part
                                        break
                                
                                # Extract delay time
                                delay = line.split('in')[-1].strip() if 'in' in line else "unknown time"
                                
                                formatted_message.append(f"{role_num} - @{role_name} - {amount} available in {delay}")
                            except Exception as e:
                                # If parsing fails, just use the original line but clean it up
                                clean_line = line.strip()
                                if clean_line:
                                    formatted_message.append(clean_line)
                    
                    collect_again_messages.append(f"```{client.user}\n" + "\n".join(formatted_message) + "```")
                    log_message(client.user, "COLLECT DELAY", f"Roles available:\n{message_content}", "WARN")
                    message_received.set()

    @client.event
    async def on_ready():
        nonlocal success, error_message, collected_amount
        try:
            log_message(client.user, "LOGGED IN", "✓")
            channel = client.get_channel(CHANNEL_ID)
            log_message(client.user, "CHANNEL", f"ID: {CHANNEL_ID}")

            application_commands = await channel.application_commands()
            deposit_command = None
            collect_command = None
            work_command = None

            for command in application_commands:
                if command.id == 901118136529588275:
                    deposit_command = command
                if command.id == 901118136529588278:
                    collect_command = command
                if command.id == 901118136529588281:
                    work_command = command

            await asyncio.sleep(2)

            # Execute work command and wait for response
            log_message(client.user, "COMMAND", "Executing work command", "DEBUG")
            message_received.clear()
            if await execute_command_with_retry(work_command, channel):
                try:
                    await asyncio.wait_for(message_received.wait(), timeout=10)
                    log_message(client.user, "RESPONSE", "Work command response received", "DEBUG")
                except asyncio.TimeoutError:
                    log_message(client.user, "WARN", "No response from work command, continuing with collection", "WARN")
                finally:
                    # Reset for next command regardless of work response
                    message_received.clear()
                    await asyncio.sleep(2)
                    
                # Now execute collect command and wait for its response
                log_message(client.user, "COMMAND", "Executing collect command", "DEBUG")
                if await execute_command_with_retry(collect_command, channel):
                    # Wait for bot response with timeout
                    try:
                        log_message(client.user, "WAITING", "Waiting for bot response...", "DEBUG")
                        await asyncio.wait_for(message_received.wait(), timeout=5)  # Reduced timeout to 5 seconds
                        log_message(client.user, "RESPONSE", f"Bot response received, collected amount: {collected_amount}", "DEBUG")
                        
                    except asyncio.TimeoutError:
                        log_message(client.user, "WARN", "No response received for collection, trying to recover from recent messages", "WARN")
                        # Check if we can find the collection in the embed by retrieving recent messages
                        try:
                            # Try to get the most recent messages in the channel
                            messages = [msg async for msg in channel.history(limit=10)]
                            log_message(client.user, "DEBUG", f"Retrieved {len(messages)} recent messages to check for collection", "DEBUG")
                            
                            for msg in messages:
                                if msg.author.id == 292953664492929025 and msg.embeds:  # UnbelievaBoat's ID
                                    for embed in msg.embeds:
                                        # Check if this embed is for the current user
                                        if embed.author and str(client.user) == embed.author.name:
                                            log_message(client.user, "DEBUG", f"Found message for current user", "DEBUG")
                                            
                                            # Check if it's a collection message
                                            if embed.description and "Role income successfully collected!" in embed.description:
                                                log_message(client.user, "DEBUG", f"Found collection message in history", "DEBUG")
                                                                    # Process this message as our collection message
                                                cash_amounts = []
                                                for line in embed.description.split('\n'):
                                                    try:
                                                        # New format with specific emoji ID and role ID format <@&ROLEID>
                                                        if ('`' in line or ' - <@&') and '<:europa_rp:1144393670053875772>' in line and '(cash)' in line:
                                                            amount_str = line.split('<:europa_rp:1144393670053875772>')[1].split('(cash)')[0].strip()
                                                            amount = int(amount_str.replace(',', ''))
                                                            cash_amounts.append(amount)
                                                            log_message(client.user, "DEBUG", f"Recovered amount (new format): {amount:,}", "DEBUG")
                                                            continue
                                                        
                                                        # Fallback to old format
                                                        elif ':europa_rp~2:' in line and '(cash)' in line:
                                                            amount_str = line.split(':europa_rp~2:')[1].split('(cash)')[0].strip()
                                                            amount = int(amount_str.replace(',', ''))
                                                            cash_amounts.append(amount)
                                                            log_message(client.user, "DEBUG", f"Recovered amount (old format): {amount:,}", "DEBUG")
                                                            continue
                                                    except Exception as e:
                                                        log_message(client.user, "ERROR", f"Failed to parse recovered amount: {e}", "DEBUG")
                                                        continue
                                                
                                                if cash_amounts:
                                                    collected_amount = sum(cash_amounts)
                                                    token_collections[token] = collected_amount
                                                    log_message(client.user, "RECOVERED", f"Found collection: :europa_rp~2:{collected_amount:,}", "SUCCESS")
                                                    break  # Stop processing once we find a valid collection
                                        
                                        # If we still haven't found a collection amount, check for deposit messages
                                        if collected_amount == 0 and embed.author and str(client.user) == embed.author.name:
                                            if embed.description and "Deposited" in embed.description:
                                                # If we find a deposit message and didn't detect collection, try to recover from deposit amount
                                                try:
                                                    if ':europa_rp~2:' in embed.description and 'to your bank' in embed.description:
                                                        deposit_str = embed.description.split(':europa_rp~2:')[1].split('to')[0].strip()
                                                        deposit_amount = int(deposit_str.replace(',', ''))
                                                        if deposit_amount > 0:
                                                            collected_amount = deposit_amount
                                                            token_collections[token] = collected_amount
                                                            log_message(client.user, "RECOVERED", f"Estimated collection from deposit: 💸{collected_amount:,}", "SUCCESS")
                                                            break  # Stop processing once we find a valid deposit
                                                except Exception as e:
                                                    log_message(client.user, "ERROR", f"Failed to parse deposit amount: {e}", "DEBUG")
                        except Exception as e:
                            log_message(client.user, "ERROR", f"Failed to recover collection amount: {e}", "DEBUG")
                    
                    # Add a small delay to ensure all messages are processed
                    await asyncio.sleep(1)
                    
                    # Get token type before processing collection
                    token_type = TOKEN_TYPE_MAP.get(token)
                    
                    # Log the final collection status
                    if collected_amount > 0:
                        log_message(client.user, "COLLECTION STATUS", f"Final collection amount: 💸{collected_amount:,}", "SUCCESS")
                        
                        # Only process commissions if we collected an amount
                        if token_type == "5k":
                            commission = int(collected_amount * 0.25)  # Calculate 25% commission
                            log_message(client.user, "COMMISSION", f"💸 Sending {commission:,} (25% of {collected_amount:,})", "INFO")
                            await channel.send(f"-pay <@{COMMISSION_USER_ID}> {commission}")
                            await asyncio.sleep(2)  # Small delay after sending payment
                        elif token_type == "15k":
                            commission = int(collected_amount * 0.3333)  # Calculate 33.33% commission
                            log_message(client.user, "COMMISSION", f":europa_rp~2: Sending {commission:,} (33.33% of {collected_amount:,})", "INFO")
                            await channel.send(f"-pay <@{COMMISSION_USER_ID}> {commission}")
                            await asyncio.sleep(2)  # Small delay after sending payment
                        elif token_type == "30k":
                            commission = int(collected_amount * 0.30)  # Calculate 30% commission
                            log_message(client.user, "COMMISSION", f":europa_rp~2: Sending {commission:,} (30% of {collected_amount:,})", "INFO")
                            await channel.send(f"-pay <@{COMMISSION_USER_ID}> {commission}")
                            await asyncio.sleep(2)  # Small delay after sending payment
                        elif token_type == "master":
                            # No commission for master tokens, deposit will be handled later
                            log_message(client.user, "COMMISSION", f":europa_rp~2: No commission (master token)", "INFO")
                    else:
                        log_message(client.user, "COLLECTION STATUS", "No collection detected", "WARN")
                        log_message(client.user, "COMMISSION", "No collection detected, skipping commission", "WARN")
                    
                    # After commission handling, proceed with deposit only if this is not a master token
                    # or if it's a master token with no collection (we can deposit right away)
                    if token_type != "master" or collected_amount == 0:
                        log_message(client.user, "DEPOSIT", "Depositing remaining balance", "INFO")
                        
                        # Execute deposit command
                        if await execute_command_with_retry(deposit_command, channel, amount="all"):
                            execution_time = round(time.time() - command_start_time, 2)
                            log_message(client.user, "COMPLETED", f"✓ All tasks finished in {execution_time}s", "SUCCESS")
                            success = True
                        else:
                            log_message(client.user, "ERROR", "Failed to execute deposit command", "ERROR")
                            failed_collections.append(f"{client.user} - Failed to execute deposit command")
                    else:
                        # For master tokens with collection, deposit at the end
                        log_message(client.user, "DEPOSIT DELAY", "Master token deposit will occur after all commissions", "INFO")
                        await asyncio.sleep(2)  # Small delay before deposit
                        
                        # Now execute deposit for master token
                        log_message(client.user, "DEPOSIT", "Depositing master token balance", "INFO")
                        if await execute_command_with_retry(deposit_command, channel, amount="all"):
                            execution_time = round(time.time() - command_start_time, 2)
                            log_message(client.user, "COMPLETED", f"✓ Master token tasks finished in {execution_time}s", "SUCCESS")
                            success = True
                        else:
                            log_message(client.user, "ERROR", "Failed to execute master token deposit command", "ERROR")
                            failed_collections.append(f"{client.user} - Failed to execute master token deposit command")

        except Exception as e:
            error_message = f"Error with {client.user}: {str(e)}"
            log_message(client.user, "ERROR", f"Exception: {str(e)}", "ERROR")
            log_message(client.user, "DEBUG", f"Error occurred after {round(time.time() - command_start_time, 2)}s of execution", "DEBUG")
            failed_collections.append(f"{client.user} - Exception: {str(e)}")
        finally:
            try:
                await client.close()
            except Exception as e:
                log_message(client.user, "DEBUG", f"Error during client cleanup: {str(e)}", "DEBUG")
            done.set()

    try:
        await asyncio.wait_for(client.start(token), timeout=CLIENT_TIMEOUT)
    except asyncio.TimeoutError:
        error_message = f"[TIMEOUT] Token ending after {CLIENT_TIMEOUT} seconds."
        log_message(client.user, "TIMEOUT", f"Client timeout after {CLIENT_TIMEOUT}s", "WARN")
        failed_collections.append(f"{client.user} - Client timeout after {CLIENT_TIMEOUT}s")
    except Exception as e:
        error_message = f"[ERROR] Unexpected error: {str(e)}"
        log_message(client.user, "ERROR", f"Unexpected error: {str(e)}", "ERROR")
        failed_collections.append(f"{client.user} - Unexpected error: {str(e)}")
    
    return success, error_message

async def main():
    if not TOKENS:
        raise ValueError("No tokens provided in environment variables.")

    results = await asyncio.gather(*(run_client(token) for token in TOKENS), return_exceptions=True)
    
    success_count = sum(1 for result in results if isinstance(result, tuple) and result[0])
    error_messages = [
        result[1] for result in results 
        if isinstance(result, tuple) and result[1] is not None
    ]
    
    await send_webhook_update(success_count, len(TOKENS), error_messages if error_messages else None)

if __name__ == "__main__":
    asyncio.run(main())
