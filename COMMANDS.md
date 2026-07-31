# Commands

Both slash commands and `?` prefix commands are supported. Commands fail if users do not have the required Discord permissions.

- `?help` / `/help` - Print a list of commands.
- `?say [message]` / `/say message:[message]` - Say the message with the caller's mention at the beginning so people cannot impersonate the bot.
- `?echo [channel] [message]` / `/echo channel:[channel] message:[message]` (requires `administrator`) - Echo the message into the selected text channel.
- `?punish [user] <reason>` / `/punish user:[user] reason:<reason>` (requires moderate members, kick members, and ban members) - Increase the user's punishment status by one and apply the matching action:
  - Levels 1-3: mute for 5 minutes.
  - Levels 4-6: mute for 15 minutes.
  - Levels 7-9: mute for 60 minutes.
  - Levels 10-12: kick.
  - Levels 13+: permanent ban.
- `?regain [user]` / `/regain user:[user]` (requires moderate members, kick members, and ban members) - Decrease punishment status by one. If the previous level was a ban level, unban the user.
- `?dm [user] [message]` / `/dm user:[user] message:[message]` - DM the user a message.
- `?addrole [user] [role]` / `/addrole user:[user] role:[role]` (requires manage roles) - Add the user to the role.
- `?delrole [user] [role]` / `/delrole user:[user] role:[role]` (requires manage roles) - Remove the user from the role.
