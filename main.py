import os
import asyncio
import time
import datetime
import requests
from discord import Client
from discord.errors import HTTPException
from dotenv import load_dotenv

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
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    embed = {
        "title": "🤖 Farm Bot Status Update",
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
            "text": "Farm Bot by @aloramiaa"
        }
    }
    
    if error_messages:
        embed["fields"].append({
            "name": "❌ Errors",
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

    @client.event
    async def on_ready():
        nonlocal success, error_message
        try:
            print(f"[{client.user}] Logged in")
            channel_id = 1369318379218796605
            channel = client.get_channel(channel_id)

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

            if await execute_command_with_retry(work_command, channel):
                await asyncio.sleep(5)
                if await execute_command_with_retry(collect_command, channel):
                    await asyncio.sleep(5)
                    
                    token_type = TOKEN_TYPE_MAP.get(token)
                    if token_type == "5k":
                        await channel.send(f"-pay <@{COMMISSION_USER_ID}> 5000")
                        await asyncio.sleep(2)
                    elif token_type == "15k":
                        await channel.send(f"-pay <@{COMMISSION_USER_ID}> 15000")
                        await asyncio.sleep(2)
                    
                    await execute_command_with_retry(deposit_command, channel, amount="all")
                    await asyncio.sleep(2)
                    success = True

        except Exception as e:
            error_message = f"Error with {client.user}: {str(e)}"
            print(error_message)
        finally:
            await client.close()
            done.set()

    try:
        await asyncio.wait_for(client.start(token), timeout=CLIENT_TIMEOUT)
    except asyncio.TimeoutError:
        error_message = f"[TIMEOUT] Token ending after {CLIENT_TIMEOUT} seconds."
        print(error_message)
    except Exception as e:
        error_message = f"[ERROR] Unexpected error: {str(e)}"
        print(error_message)
    
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
