# Emberbot137

Emberbot137 is a Python bot powered by `discord.py`.
The bot supports both `~` prefix commands and synchronized Discord slash commands.

## Features

- `~help` and `/help` display the command list.
- `~say` and `/say` send a message with the caller mentioned.
- `~echo` and `/echo` let administrators post to a selected channel.
- `~addrole`, `/addrole`, `~delrole`, and `/delrole` manage member roles.

## Project structure

```
├── AGENTS.md        -> contributor and agent instructions
├── .env.sample      -> sample environment variables
├── bot.py           -> Python bot entrypoint and command handlers
├── COMMANDS.md      -> command reference
├── requirements.txt -> Python dependencies
├── README.md
└── .gitignore
```

## Requirements

- Python 3.11 or newer is recommended.
- A Discord application with a bot token.
- Bot permissions for the commands you plan to use, including message content intent for `?` prefix commands.

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.sample` to `.env` and fill in your bot token:

```bash
cp .env.sample .env
```

## Run

```bash
python bot.py
```

Slash commands are synchronized automatically when the bot becomes ready. Global command updates can take time to appear in Discord.

## Configuration

Required environment variables:

- `DISCORD_TOKEN`: Discord bot token.

Optional environment variables:

- `APP_ID`: Discord application ID, kept for hosting platforms that expose it.
- `PUBLIC_KEY`: Discord public key, kept for compatibility with existing deployment settings.
