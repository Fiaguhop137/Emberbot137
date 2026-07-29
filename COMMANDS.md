# Discord App Commands

## `/test`

A basic smoke-test command. Replies with "hello world" and a random emoji.

| Property | Value |
|---|---|
| Type | Slash command |
| Options | None |
| Works in | Guild channels, DMs, Group DMs |

---

## `/challenge`

Challenge another user to a game of rock-paper-scissors (with a twist — there are 7 objects, not 3).

| Property | Value |
|---|---|
| Type | Slash command |
| Options | `object` (required) |
| Works in | Guild channels, Group DMs |

### Options

| Name | Type | Required | Description |
|---|---|---|---|
| `object` | String (choices) | ✅ | The object you want to play |

### Available objects

| Object | Description | Beats |
|---|---|---|
| 🪨 Rock | sedimentary, igneous, or perhaps even metamorphic | Virus, Computer, Scissors |
| 🤠 Cowboy | yeehaw~ | Scissors, Wumpus, Rock |
| ✂️ Scissors | careful ! sharp ! edges !! | Paper, Computer, Virus |
| 🦠 Virus | genetic mutation, malware, or something inbetween | Cowboy, Computer, Wumpus |
| 💻 Computer | beep boop beep bzzrrhggggg | Cowboy, Paper, Wumpus |
| 🟣 Wumpus | the purple Discord fella | Paper, Rock, Scissors |
| 📄 Paper | versatile and iconic | Virus, Cowboy, Rock |

---

## Registering commands

Run this once to install commands globally to your Discord app:

```
npm run register
```

Commands are defined in [`commands.js`](./commands.js). After adding or changing a command, re-run `npm run register` to push the update to Discord.
