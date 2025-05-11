# Farm Bot

A Discord farming bot that runs automatically every 10 minutes through GitHub Actions.

## Security First!
⚠️ **IMPORTANT**: This is a public repository. Never commit your tokens or sensitive information!

## Setup

1. Clone the repository
2. Copy `.env.sample` to `.env` for local development:
   ```bash
   cp .env.sample .env
   ```
3. Add your tokens to GitHub Secrets:
   - Go to your repository Settings > Secrets and Variables > Actions
   - Add the following secrets:
     - `MASTER_TOKEN`: Your master tokens (no commission), comma-separated
     - `TOKEN_5K`: Your 5K commission tokens, comma-separated
     - `TOKEN_15K`: Your 15K commission tokens, comma-separated
     - `WEBHOOK_URL`: Your Discord webhook URL

## Local Development
1. Add your tokens to the local `.env` file (never commit this file!)
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the bot:
   ```bash
   python main.py
   ```

## Features

- Multiple token support with comma separation
- Different commission levels (Master, 5K, 15K)
- Webhook notifications with runtime statistics
- Automatic retries on rate limits
- Detailed error reporting
