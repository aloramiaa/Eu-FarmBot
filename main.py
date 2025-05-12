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
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://ptb.discord.com/api/webhooks/1365286807620554812/ag7FP-itIJOypb5XfrwJpUKQaP4yIdY02QK6R8Ri_BMpQTG6xTwuRJzMXfMUtE8hwaVn")

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

TOKENS = list(TOKEN_TYPE_MAP.keys())
COMMISSION_USER_ID = 1236292707371057216  # @aloramiaa
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
    collection_details = []
    if total_5k > 0:
        collection_details.append(f"5k Tokens: 💸{total_5k:,}")
    if total_15k > 0:
        collection_details.append(f"15k Tokens: 💸{total_15k:,}")
    
    embed = {
        "title": "🏦 Farm Collection Report",
        "color": 0x00ff00 if not error_messages else 0xff0000,
        "fields": [
            {
                "name": "Status",
                "value": f"✅ Successfully processed: {success_count}/{total_count} accounts",
                "inline": True
            },
            {
                "name": "Runtime",
                "value": f"⏱️ {duration} seconds",
                "inline": True
            },
            {
                "name": "Timestamp",
                "value": f"🕒 {current_time}",
                "inline": True
            }
        ],
        "footer": {
            "text": f"Farm Collection Bot • {current_time}"
        }
    }

    # Add collection details if any
    if collection_details:
        embed["fields"].append({
            "name": "💰 Total Collections",
            "value": "\n".join(collection_details),
            "inline": False
        })

    # Add collect again messages if any
    if collect_again_messages:
        embed["fields"].append({
            "name": "⏳ Collection Delays",
            "value": "\n".join(collect_again_messages),
            "inline": False
        })
    
    # Add failed collections if any
    if failed_collections:
        embed["fields"].append({
            "name": "❌ Failed Collections",
            "value": "\n".join(failed_collections),
            "inline": False
        })
    
    if error_messages:
        embed["fields"].append({
            "name": "⚠️ Errors",
            "value": "\n".join(error_messages),
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
        if message.channel.id == 1369318379218796605:  # Your channel ID
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
                    log_message(client.user, "DEBUG", f"Embed - Author: {embed_author_name}, First line: {embed_description.split('\n')[0] if embed_description else 'None'}", "DEBUG")
                    
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
                        elif "<:xmark:" in embed_description and "You can collect income again" in embed_description:
                            is_response_for_user = True
                            collected_amount = 0
                            
                            # Parse delay times with proper formatting
                            formatted_message = []
                            for line in embed_description.split('\n'):
                                if '<@&' in line and '💸' in line and '(cash)' in line:
                                    try:
                                        # Extract role number (e.g., "1 - ")
                                        role_num = line.split(' - ')[0].strip()
                                        
                                        # Extract amount between 💸 and (cash)
                                        amount_str = line.split('💸')[1].split('(cash)')[0].strip()
                                        
                                        # Extract timestamp from Discord format <t:1234567890:R>
                                        timestamp_str = line.split('<t:')[1].split(':R>')[0].strip()
                                        
                                        # Convert Unix timestamp to readable format
                                        readable_time = dt.fromtimestamp(int(timestamp_str)).strftime("%Y-%m-%d %H:%M:%S")
                                        
                                        formatted_message.append(f"{role_num} - available at {readable_time} - 💸{amount_str}")
                                    except Exception as e:
                                        log_message(client.user, "ERROR", f"Failed to parse delay line: {line} - {str(e)}", "DEBUG")
                                        continue
                        
                            collect_again_messages.append(f"```{client.user}\n" + "\n".join(formatted_message) + "```")
                            
                            # Get first role's delay using new parsing method
                            first_line = next((line for line in embed_description.split('\n') if '<@&' in line and '💸' in line), None)
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
                            
                            # Parse successful collection amounts for format with backticks
                            for line in embed_description.split('\n'):
                                if '`' in line and '💸' in line and '(cash)' in line:
                                    try:
                                        amount_str = line.split('💸')[1].split('(cash)')[0].strip()
                                        amount = int(amount_str.replace(',', ''))
                                        cash_amounts.append(amount)
                                        log_message(client.user, "DEBUG", f"Parsed amount (format 1): {amount:,}", "DEBUG")
                                    except Exception as e:
                                        log_message(client.user, "ERROR", f"Failed to parse amount from line: {line} - {str(e)}", "DEBUG")
                                        continue
                            
                            # Parse successful collection amounts for format with @ symbol
                            if not cash_amounts:
                                for line in embed_description.split('\n'):
                                    if '@' in line and '💸' in line and '(cash)' in line:
                                        try:
                                            amount_str = line.split('💸')[1].split('(cash)')[0].strip()
                                            amount = int(amount_str.replace(',', ''))
                                            cash_amounts.append(amount)
                                            log_message(client.user, "DEBUG", f"Parsed amount (format 2): {amount:,}", "DEBUG")
                                        except Exception as e:
                                            log_message(client.user, "ERROR", f"Failed to parse amount from line: {line} - {str(e)}", "DEBUG")
                                            continue
                            
                            collected_amount = sum(cash_amounts)
                            token_collections[token] = collected_amount
                            log_message(client.user, "COLLECTED", f"💰 {collected_amount:,} cash from {len(cash_amounts)} roles", "SUCCESS")
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
                    collected_amount = 0
                    # Format each line of the message for better readability
                    formatted_message = []
                    for line in message_content.split('\n'):
                        if line.strip():  # Only process non-empty lines
                            if '(cash) in' in line and '<t:' in line:
                                try:
                                    # Extract parts
                                    parts = line.split('|')
                                    if len(parts) == 2:
                                        role_num = parts[0].strip()
                                        income_info = parts[1].strip()
                                        
                                        # Extract timestamp if present
                                        if '<t:' in income_info:
                                            timestamp_str = income_info.split('<t:')[1].split(':R>')[0].strip()
                                            readable_time = dt.fromtimestamp(int(timestamp_str)).strftime("%Y-%m-%d %H:%M:%S")
                                            income_info = income_info.replace(f"<t:{timestamp_str}:R>", readable_time)
                                        
                                        formatted_message.append(f"{role_num} | {income_info}")
                                except Exception:
                                    # If parsing fails, just use the original line
                                    formatted_message.append(line.strip())
                            else:
                                # This is the header line or other info
                                formatted_message.append(line.strip())
                    
                    collect_again_messages.append(f"```{client.user}\n" + "\n".join(formatted_message) + "```")
                    log_message(client.user, "COLLECT DELAY", f"➜ Roles available in: {message_content.strip()}", "WARN")
                    message_received.set()

    @client.event
    async def on_ready():
        nonlocal success, error_message, collected_amount
        try:
            log_message(client.user, "LOGGED IN", "✓")
            channel_id = 1369318379218796605
            channel = client.get_channel(channel_id)
            log_message(client.user, "CHANNEL", f"ID: {channel_id}")

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
                                                    if ('`' in line or '@' in line) and '💸' in line and '(cash)' in line:
                                                        try:
                                                            amount_str = line.split('💸')[1].split('(cash)')[0].strip()
                                                            amount = int(amount_str.replace(',', ''))
                                                            cash_amounts.append(amount)
                                                            log_message(client.user, "DEBUG", f"Recovered amount: {amount:,}", "DEBUG")
                                                        except Exception as e:
                                                            log_message(client.user, "ERROR", f"Failed to parse recovered amount: {e}", "DEBUG")
                                                            continue
                                                
                                                if cash_amounts:
                                                    collected_amount = sum(cash_amounts)
                                                    token_collections[token] = collected_amount
                                                    log_message(client.user, "RECOVERED", f"Found collection: 💸{collected_amount:,}", "SUCCESS")
                                                    break  # Stop processing once we find a valid collection
                                        
                                        # If we still haven't found a collection amount, check for deposit messages
                                        if collected_amount == 0 and embed.author and str(client.user) == embed.author.name:
                                            if embed.description and "Deposited" in embed.description:
                                                # If we find a deposit message and didn't detect collection, try to recover from deposit amount
                                                try:
                                                    if '💸' in embed.description and 'to your bank' in embed.description:
                                                        deposit_str = embed.description.split('💸')[1].split('to')[0].strip()
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
                    
                    # Log the final collection status
                    if collected_amount > 0:
                        log_message(client.user, "COLLECTION STATUS", f"Final collection amount: 💸{collected_amount:,}", "SUCCESS")
                    else:
                        log_message(client.user, "COLLECTION STATUS", "No collection detected", "WARN")
                    
                    # Only proceed with payment if we collected an amount
                    token_type = TOKEN_TYPE_MAP.get(token)
                    if collected_amount > 0:
                        # Reset event for payment response
                        message_received.clear()
                        
                        if token_type == "5k":
                            commission = int(collected_amount * 0.25)  # Calculate 25% commission
                            log_message(client.user, "COMMISSION", f"💸 Sending {commission:,} (25% of {collected_amount:,})", "INFO")
                            await channel.send(f"-pay <@{COMMISSION_USER_ID}> {commission}")
                            await asyncio.sleep(2)  # Small delay after sending payment
                            
                        elif token_type == "15k":
                            commission = int(collected_amount * 0.3333)  # Calculate 33.33% commission
                            log_message(client.user, "COMMISSION", f"💸 Sending {commission:,} (33.33% of {collected_amount:,})", "INFO")
                            await channel.send(f"-pay <@{COMMISSION_USER_ID}> {commission}")
                            await asyncio.sleep(2)  # Small delay after sending payment
                        elif token_type == "master":
                            # No commission for master tokens
                            log_message(client.user, "COMMISSION", f"💸 No commission (master token)", "INFO")
                        else:
                            log_message(client.user, "COMMISSION", "No collection detected, skipping commission", "WARN")
                        
                        # After payment is processed, then do deposit
                        log_message(client.user, "DEPOSIT", "Depositing remaining balance", "INFO")
                        
                        if await execute_command_with_retry(deposit_command, channel, amount="all"):
                            execution_time = round(time.time() - command_start_time, 2)
                            log_message(client.user, "COMPLETED", f"✓ All tasks finished in {execution_time}s", "SUCCESS")
                            success = True
                        else:
                            log_message(client.user, "ERROR", "Failed to execute deposit command", "ERROR")
                            failed_collections.append(f"{client.user} - Failed to execute deposit command")

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
