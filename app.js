import 'dotenv/config';
import {
  Client,
  GatewayIntentBits,
  Partials,
  PermissionFlagsBits,
} from 'discord.js';

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildBans,
    GatewayIntentBits.DirectMessages,
  ],
  partials: [Partials.Channel],
});

// In-memory punishment tracker: userId -> punishment level (integer >= 0)
const punishmentLevels = {};

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Resolve a member from a guild by user ID or exact username.
 * Returns a GuildMember or null.
 */
async function resolveMember(guild, query) {
  query = query.trim();
  // Strip <@…> mention syntax if pasted
  const mentionMatch = query.match(/^<@!?(\d+)>$/);
  if (mentionMatch) query = mentionMatch[1];

  // Try as a snowflake ID first
  if (/^\d+$/.test(query)) {
    try {
      return await guild.members.fetch(query);
    } catch {
      // fall through to username search
    }
  }

  // Search by exact username (case-insensitive)
  const members = await guild.members.fetch();
  return (
    members.find(
      (m) =>
        m.user.username.toLowerCase() === query.toLowerCase() ||
        m.user.tag.toLowerCase() === query.toLowerCase(),
    ) ?? null
  );
}

/**
 * Apply a punishment action based on the current level.
 * Levels 1–3: 5-min timeout
 * Levels 4–6: 15-min timeout
 * Levels 7–9: 60-min timeout
 * Levels 10–12: kick
 * Level 13+: permanent ban
 */
async function applyPunishment(member, level, reason) {
  const MIN = 60_000; // ms per minute
  if (level <= 3) {
    await member.timeout(5 * MIN, reason);
    return `muted for **5 minutes** (level ${level})`;
  } else if (level <= 6) {
    await member.timeout(15 * MIN, reason);
    return `muted for **15 minutes** (level ${level})`;
  } else if (level <= 9) {
    await member.timeout(60 * MIN, reason);
    return `muted for **60 minutes** (level ${level})`;
  } else if (level <= 12) {
    await member.kick(reason);
    return `**kicked** (level ${level})`;
  } else {
    await member.ban({ reason });
    return `**permanently banned** (level ${level})`;
  }
}

/**
 * Resolve a role from a guild by name or ID.
 */
function resolveRole(guild, query) {
  query = query.trim();
  return (
    guild.roles.cache.get(query) ??
    guild.roles.cache.find(
      (r) => r.name.toLowerCase() === query.toLowerCase(),
    ) ??
    null
  );
}

// ── Command handler ───────────────────────────────────────────────────────────

client.on('messageCreate', async (message) => {
  if (message.author.bot || !message.content.startsWith('!')) return;

  const args = message.content.slice(1).trim().split(/\s+/);
  const command = args.shift().toLowerCase();
  const { guild, member, channel } = message;

  try {
    // ── !say [message] ──────────────────────────────────────────────────────
    if (command === 'say') {
      const text = args.join(' ');
      if (!text) return channel.send('Usage: `!say [message]`');
      return channel.send(`<@${message.author.id}> ${text}`);
    }

    // ── !echo [channel] [message] ───────────────────────────────────────────
    if (command === 'echo') {
      if (!member.permissions.has(PermissionFlagsBits.Administrator)) {
        return channel.send('❌ You need the **Administrator** permission to use `!echo`.');
      }
      const channelArg = args.shift();
      const text = args.join(' ');
      if (!channelArg || !text) return channel.send('Usage: `!echo [channel] [message]`');

      // Accept #channel mention, channel ID, or channel name (with or without #)
      const mentionId = channelArg.match(/^<#(\d+)>$/)?.[1];
      const nameQuery = channelArg.replace(/^#/, '').toLowerCase();
      const targetChannel =
        guild.channels.cache.get(mentionId ?? channelArg) ??
        guild.channels.cache.find((c) => c.name.toLowerCase() === nameQuery);
      if (!targetChannel?.isTextBased()) return channel.send('❌ Channel not found or not a text channel.');

      await targetChannel.send(text);
      return message.author.send(`✅ Message sent to <#${targetChannel.id}>.`);
    }

    // ── !punish [user] [reason] ─────────────────────────────────────────────
    if (command === 'punish') {
      const needed = [PermissionFlagsBits.ModerateMembers, PermissionFlagsBits.KickMembers, PermissionFlagsBits.BanMembers];
      if (!needed.every((p) => member.permissions.has(p))) {
        return channel.send('❌ You need **Mute, Kick, and Ban** permissions to use `!punish`.');
      }
      const userArg = args.shift();
      const reason = args.join(' ') || 'No reason provided';
      if (!userArg) return channel.send('Usage: `!punish [user] [reason]`');

      const target = await resolveMember(guild, userArg);
      if (!target) return channel.send('❌ User not found.');

      punishmentLevels[target.id] = (punishmentLevels[target.id] ?? 0) + 1;
      const level = punishmentLevels[target.id];
      const outcome = await applyPunishment(target, level, reason);
      return channel.send(`🔨 <@${target.id}> has been ${outcome}. Reason: *${reason}*`);
    }

    // ── !regain [user] ──────────────────────────────────────────────────────
    if (command === 'regain') {
      const needed = [PermissionFlagsBits.ModerateMembers, PermissionFlagsBits.KickMembers, PermissionFlagsBits.BanMembers];
      if (!needed.every((p) => member.permissions.has(p))) {
        return channel.send('❌ You need **Mute, Kick, and Ban** permissions to use `!regain`.');
      }
      const userArg = args.shift();
      if (!userArg) return channel.send('Usage: `!regain [user]`');

      // For banned users, we may need to resolve by ID directly
      const userIdMatch = userArg.match(/^<@!?(\d+)>$/) ?? (/^\d+$/.test(userArg) ? [null, userArg] : null);
      const userId = userIdMatch ? userIdMatch[1] : null;

      const current = punishmentLevels[userId ?? userArg] ?? 0;
      if (current === 0) return channel.send('❌ This user\'s punishment level is already 0.');

      const newLevel = current - 1;

      // Unban if they were banned (level was 13+)
      if (current >= 13) {
        if (!userId) return channel.send('❌ Banned users must be identified by user ID or mention.');
        try {
          await guild.members.unban(userId, 'Punishment reduced via !regain');
        } catch {
          return channel.send('❌ Could not unban user — they may not be banned.');
        }
      }

      punishmentLevels[userId ?? userArg] = newLevel;
      return channel.send(
        `✅ Punishment level reduced to **${newLevel}**${current >= 13 ? ' and user has been unbanned' : ''}.`,
      );
    }

    // ── !dm [user] [message] ────────────────────────────────────────────────
    if (command === 'dm') {
      if (!member.permissions.has(PermissionFlagsBits.Administrator)) {
        return channel.send('❌ You need the **Administrator** permission to use `!dm`.');
      }
      const userArg = args.shift();
      const text = args.join(' ');
      if (!userArg || !text) return channel.send('Usage: `!dm [user] [message]`');

      const target = await resolveMember(guild, userArg);
      if (!target) return channel.send('❌ User not found.');

      try {
        await target.send(text);
        return channel.send(`✅ DM sent to <@${target.id}>.`);
      } catch {
        return channel.send('❌ Could not send DM — the user may have DMs disabled.');
      }
    }

    // ── !addrole [user] [role] ──────────────────────────────────────────────
    if (command === 'addrole') {
      if (!member.permissions.has(PermissionFlagsBits.ManageRoles)) {
        return channel.send('❌ You need the **Manage Roles** permission to use `!addrole`.');
      }
      const userArg = args.shift();
      const roleQuery = args.join(' ');
      if (!userArg || !roleQuery) return channel.send('Usage: `!addrole [user] [role]`');

      const target = await resolveMember(guild, userArg);
      if (!target) return channel.send('❌ User not found.');
      const role = resolveRole(guild, roleQuery);
      if (!role) return channel.send('❌ Role not found.');

      await target.roles.add(role);
      return channel.send(`✅ Added **${role.name}** to <@${target.id}>.`);
    }

    // ── !delrole [user] [role] ──────────────────────────────────────────────
    if (command === 'delrole') {
      if (!member.permissions.has(PermissionFlagsBits.ManageRoles)) {
        return channel.send('❌ You need the **Manage Roles** permission to use `!delrole`.');
      }
      const userArg = args.shift();
      const roleQuery = args.join(' ');
      if (!userArg || !roleQuery) return channel.send('Usage: `!delrole [user] [role]`');

      const target = await resolveMember(guild, userArg);
      if (!target) return channel.send('❌ User not found.');
      const role = resolveRole(guild, roleQuery);
      if (!role) return channel.send('❌ Role not found.');

      await target.roles.remove(role);
      return channel.send(`✅ Removed **${role.name}** from <@${target.id}>.`);
    }
  } catch (err) {
    console.error(`Error handling !${command}:`, err);
    channel.send('❌ Something went wrong. Check that the bot has the required permissions.').catch(() => {});
  }
});

client.once('ready', () => {
  console.log(`Logged in as ${client.user.tag}`);
});

client.login(process.env.DISCORD_TOKEN);
