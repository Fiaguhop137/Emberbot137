> NOTE: both slash and `!` are allowed. Commands fail if users don't have the required permissions to use the command.

- `!help` - Print a list of commands.
- `!say [message]` (no required permissions): Say the message, but include a user mention at the beginning so people can't impersonate the bot. Also only applies to the current channel.
`!echo [channel] [message]` (requires `administrator`): Echo the message into the channel. Only available to people with
`!punish [user] [reason]` (requires mute, kick, and ban): Increase the users punishment status by one. Using this new punishment status:
- If 1,2,3: Mute for 5 minutes
- If 4,5,6: Mute for 15 minutes
- If 7,8,9: Mute for 60 minutes
- If 10,11,12: Kick
- If 13: Ban permanently
- `!regain [user]` (requires mute, kick, and ban): Decrease punishment status by one (return an error if already 0) and don't do any action. Unban them if banned.
- `!dm [user] [message]` (requires administrator): DM the user a message.
- `!addrole [userid or complete username] [role]` (requires manage roles): Add the user to the role
- `!delrole [userid or complete username] [role]` (requires manage roles): Remove the user from the role
