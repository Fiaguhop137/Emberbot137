# Meow Bot on Replit

Meow Bot is a Python Discord bot. The Replit workflow runs `python bot.py`.

## Required secrets

Set these in Replit Secrets:

| Secret | Where to find it |
|---|---|
| `DISCORD_TOKEN` | Discord Developer Portal → Your App → Bot |
| `APP_ID` | Discord Developer Portal → Your App → General Information (optional for runtime) |
| `PUBLIC_KEY` | Discord Developer Portal → Your App → General Information (optional for runtime) |

## Discord setup

- Enable the message content intent for the bot if you want `?` prefix commands.
- Invite the bot with `bot` and `applications.commands` scopes.
- Slash commands are synchronized automatically when the bot starts.

## Project structure

```
├── AGENTS.md        # Contributor and agent instructions
├── bot.py           # Discord bot entrypoint and command handlers
├── COMMANDS.md      # Command reference
├── requirements.txt # Python dependencies
└── .env.sample      # Template for required environment variables
```
