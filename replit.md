# Discord Getting Started App

A rock-paper-scissors Discord bot from Discord's official [getting started guide](https://discord.com/developers/docs/getting-started). Built with Node.js and Express.

## Running the app

```
node app.js
```

The workflow **Start application** is configured to run this automatically on port 3000.

## Required secrets

Set these in Replit Secrets (already configured):

| Secret | Where to find it |
|---|---|
| `APP_ID` | Discord Developer Portal → Your App → General Information |
| `DISCORD_TOKEN` | Discord Developer Portal → Your App → Bot |
| `PUBLIC_KEY` | Discord Developer Portal → Your App → General Information |

## Discord setup

1. **Interactions Endpoint URL** — In the Discord Developer Portal under your app's General Information, set the Interactions Endpoint URL to:
   ```
   https://<your-replit-dev-domain>/interactions
   ```

2. **Register slash commands** — Run once to install commands to your Discord app:
   ```
   npm run register
   ```

## Project structure

```
├── app.js        # Main Express server — handles Discord interactions
├── commands.js   # Slash command definitions + registration script
├── game.js       # Rock-paper-scissors game logic
├── utils.js      # Utility functions and enums
├── examples/     # Standalone feature-specific sample apps
└── .env.sample   # Template for required environment variables
```

## User preferences

<!-- Add your preferences here -->
