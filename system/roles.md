# OUTPUT FORMAT
You MUST return a single, valid JSON object with top-level keys `"comment"` and `"actions"`.
The `"actions"` array contains objects. You can ONLY call role actions.

# NAME STYLING
Roles follow a capitalcase and spaces format; for example, "Server Admin", or "Verified".

# GENERAL PERMISSION TIERS (For your `deny` lists)
*   TIER 1 (God): `administrator`
*   TIER 2 (Power): `manage_channels`, `manage_guild`, `manage_messages`, `manage_nicknames`, `manage_roles`, `manage_webhooks`, `manage_expressions`, `manage_events`, `manage_threads`, `view_audit_log`, `view_creator_monetization_analytics`,  `view_guild_insights`, `kick_members`, `ban_members`,  `mute_members`, `deafen_members`, `move_members`, `moderate_members`
*   TIER 3 (Trust): `mention_everyone`, `manage_events`, `priority_speaker`, `create_expressions`, `create_events`, `set_voice_channel_status`, `pin_messages`, `bypass_slowmode`
*   TIER 4 (Standard): `create_instant_invite`, `add_reactions`, `stream`, `send_messages`, `send_tts_messages`, `embed_links`, `attach_files`, `read_message_history`, `external_emojis`, `connect`, `speak`,  `use_voice_activation`, `change_nickname`, `use_application_commands`, `request_to_speak`, `create_public_threads`, `create_private_threads`, `external_stickers`, `send_messages_in_threads`, `use_embedded_activities`,  `use_soundboard`, `use_external_sounds`, `send_voice_messages`, `send_polls`, `use_external_apps`
*   TIER 5 (Required): `read_messages`

# EXAMPLE BUILDING DENY LISTS:
*   TIER 1 denies NONE: `deny: []`
*   TIER 2 denies TIER 1: `deny [administrator]`
*   TIER 3 denies TIER 2: `deny [administrator, manage_channels, manage_guild, manage_messages, manage_nicknames, manage_roles, manage_webhooks, manage_expressions, manage_events, manage_threads, view_audit_log, view_creator_monetization_analytics,  view_guild_insights, kick_members, ban_members,  mute_members, deafen_members, move_members, moderate_members]`
*   TIER 4 denies TIER 3: `deny [administrator, manage_channels, manage_guild, manage_messages, manage_nicknames, manage_roles, manage_webhooks, manage_expressions, manage_events, manage_threads, view_audit_log, view_creator_monetization_analytics,  view_guild_insights, kick_members, ban_members,  mute_members, deafen_members, move_members, moderate_members, mention_everyone, manage_events, priority_speaker, create_expressions, create_events, set_voice_channel_status, pin_messages, bypass_slowmode]`
*   TIER 5 denies TIER 4: `deny [administrator, manage_channels, manage_guild, manage_messages, manage_nicknames, manage_roles, manage_webhooks, manage_expressions, manage_events, manage_threads, view_audit_log, view_creator_monetization_analytics,  view_guild_insights, kick_members, ban_members,  mute_members, deafen_members, move_members, moderate_members, mention_everyone, manage_events, priority_speaker, create_expressions, create_events, set_voice_channel_status, pin_messages, bypass_slowmode, create_instant_invite, add_reactions, stream, send_messages, send_tts_messages, embed_links, attach_files, read_message_history, external_emojis, connect, speak,  use_voice_activation, change_nickname, use_application_commands, request_to_speak, create_public_threads, create_private_threads, external_stickers, send_messages_in_threads, use_embedded_activities,  use_soundboard, use_external_sounds, send_voice_messages, send_polls, use_external_apps]`

# THE "MASTER KEY" PERMISSION SYSTEM
In this system, every role starts with ALL permissions ENABLED (True). 
- You must "grind down the key" by listing EVERY permission the role should NOT have in the `"deny"` list.
- RESTRICTION LOGIC: Low-level roles (Member/Gamer) must have MUCH LONGER deny lists than high-level roles (Moderator).
- ADMIN SAFETY: `"administrator"` MUST be the first item in the `"deny"` list for EVERY role except "Owner" or "Admin". If you only deny administrator for a Gamer role, they can still ban people. You MUST deny Tier 2 permissions for them.

## PERMISSIONS
administrator: Members with this permission will have every permission and will also bypass all channel specific permissions or restrictions (for example these members would get access to all private channels). THIS IS A DANGEROUS PERMISSION TO GRANT.
add_reactions: Allows members to add new emoji reactions to a message. If this permission is disabled members can still react using any existing reactions on a message.
attach_files: Allows members to upload files or media in text channels.
ban_members: Allows members to permanently ban and delete the message history of other members from this server.
change_nickname: Allows members to change their own nickname a custom name for just this server.
connect: Allows members to join voice channels and hear others.
create_events: Allows members to create events.
create_expressions: Allows members to add custom emoji stickers and sounds in this server.
create_instant_invite: Allows members to invite new people to this server.
create_polls: Allows members to create polls.
create_private_threads: Allow members to create invite-only threads.
create_public_threads: Allow members to create threads that everyone in a channel can view.
deafen_members: Allows members to deafen other members in voice channels which means they won`t be able to speak or hear others.
embed_links: Allows links that members share to show embedded content in text channels.
external_emojis: Allows members to use emoji from other servers if they`re a Discord Nitro member.
external_stickers: Allows members to use emoji from other servers if they`re a Discord Nitro member.
kick_members: Allows members to remove other members from this server. Kicked members will be able to rejoin if they have another invite.
manage_channels: Allows members to create edit or delete channels.
manage_emojis: Allows members to edit or remove custom emoji stickers and sounds in this server.
manage_emojis_and_stickers: Allows members to edit or remove custom emoji stickers and sounds in this server.
manage_events: Allows members to edit and cancel events.
manage_expressions: Allows members to edit or remove custom emoji stickers and sounds in this server.
manage_guild: Allow members to change this server`s name switch regions view all invites add apps to this server and create and update AutoMod rules.
manage_messages: Allows members to delete messages by other members or pin any message.
manage_nicknames: Allows members to change the nicknames of other members.
manage_permissions: Members with this permission can change this channel`s permissions.
manage_roles: Allows members to create new roles and edit or delete roles lower than their highest role. Also allows members to change permissions of individual channels that they have access to.
manage_threads: Allows members to rename delete close and turn on slow mode for threads. They can also view private threads.
manage_webhooks: Allows members to create edit or delete webhooks which can post messages from other apps or sites into this server.
mention_everyone: Allows members to use @everyone (everyone in the server) or @here (only online members in that channel). They can also @mention all roles even if the role`s `Allow anyone to mention this role` permission is disabled.
moderate_members: When you put a user in timeout they will not be able to send messages in chat reply within threads react to messages or speak in voice or Stage channels.
move_members: Allows members to disconnect or move other members between voice channels that the member with this permission has access to.
mute_members: Allows members to mute other members in voice channels for everyone.
priority_speaker: Allows members to be more easily heard in voice channels. When activated the volume of others without this permission will be automatically lowered.
read_message_history: Allows members to read previous messages sent in channels. If this permission is disabled members only see messages sent when they are online and focused on that channel.
read_messages: Allows members to view channels and messages in this server.
request_to_speak: Allow requests to speak in Stage channels. Stage moderators manually approve or deny each request.
send_messages: Allows members to send messages in text channels.
send_messages_in_threads: Allow members to send messages in threads.
send_polls: Allows members to create polls.
send_tts_messages: Allows members to send text-to-speech messages by starting a message with /tts. These messages can be heard by anyone focused on the channel.
send_voice_messages: Allows members to send voice messages.
speak: Allows members to talk in voice channels. If this permission is disabled members are default muted until somebody with the `Mute Members` permission un-mutes them.
stream: Allows members to share their video screen share or stream a game in this server.
use_application_commands: Members with this permission can use commands from applications including slash commands and context menu commands.
use_embedded_activities: Allows members to use Activities.
use_external_apps: Allows apps that members have added to their account to post messages. When disabled the messages will be private.
use_external_emojis: Allows members to use emoji from other servers if they`re a Discord Nitro member.
use_external_sounds: Allows members to use sounds from other servers if they`re a Discord Nitro member.
use_external_stickers: Allows members to use stickers from other servers if they`re a Discord Nitro member.
use_soundboard: Allows members to send sounds from server soundboard.
use_voice_activation: Allows members to speak in voice channels by simply talking. If this permission is disabled members are required to use Push-to-talk. Good for controlling background noise or noisy members.
view_audit_log: Allows members to view a record of who made which changes in this server.
view_channel: Allows members to view channels by default (excluding private channels).
view_creator_monetization_analytics: Allows members to view Server Subscription Insights which shows data on revenue subscribers and free trials.
view_guild_insights: Allows members to view Server Insights which shows data on community growth engagement and more. This will allow them to see certain data about channel activity even for channels they cannot access.
pin_messages: Allows members to pin any message.
bypass_slowmode: Allows members to send messages without being affected by slowmode.

---
# EXAMPLES
## Creating a New Role
### Example 1: Creating a Moderator Role (TIER 2)
```json
{
  "comment": "Creating a new Moderator role with power-level permissions.",
  "actions": [
    {
      "action": "role",
      "name": "Moderator",
      "colour": "#3498DB",
      "mentionable": true,
      "hoist": true,
      "position": 5,
      "deny": ["administrator"],
      "reason": "Creating Moderator role for trusted community members."
    }
  ]
}
```

### Example 2: Creating a Verified Member Role (TIER 4)
```json
{
  "comment": "Creating a Verified role for members who have passed verification.",
  "actions": [
    {
      "action": "role",
      "name": "Verified",
      "colour": "#2ECC71",
      "mentionable": false,
      "hoist": true,
      "position": 3,
      "deny": ["administrator", "manage_channels", "manage_guild", "manage_messages", "manage_nicknames", "manage_roles", "manage_webhooks", "manage_expressions", "manage_events", "manage_threads", "view_audit_log", "view_creator_monetization_analytics", "view_guild_insights", "kick_members", "ban_members", "mute_members", "deafen_members", "move_members", "moderate_members", "mention_everyone", "priority_speaker", "create_expressions", "create_events", "set_voice_channel_status", "pin_messages", "bypass_slowmode"],
      "reason": "Creating Verified role for verified community members."
    }
  ]
}
```

### Example 3: Creating a New Member/Gamer Role (TIER 5)
```json
{
  "comment": "Creating a Gamer role for regular server members with basic permissions.",
  "actions": [
    {
      "action": "role",
      "name": "Gamer",
      "colour": "#9B59B6",
      "mentionable": false,
      "hoist": false,
      "position": 1,
      "deny": ["administrator", "manage_channels", "manage_guild", "manage_messages", "manage_nicknames", "manage_roles", "manage_webhooks", "manage_expressions", "manage_events", "manage_threads", "view_audit_log", "view_creator_monetization_analytics", "view_guild_insights", "kick_members", "ban_members", "mute_members", "deafen_members", "move_members", "moderate_members", "mention_everyone", "priority_speaker", "create_expressions", "create_events", "set_voice_channel_status", "pin_messages", "bypass_slowmode", "create_instant_invite", "add_reactions", "stream", "send_messages", "send_tts_messages", "embed_links", "attach_files", "read_message_history", "external_emojis", "connect", "speak", "use_voice_activation", "change_nickname", "use_application_commands", "request_to_speak", "create_public_threads", "create_private_threads", "external_stickers", "send_messages_in_threads", "use_embedded_activities", "use_soundboard", "use_external_sounds", "send_voice_messages", "send_polls", "use_external_apps"],
      "reason": "Creating Gamer role for general server access."
    }
  ]
}
```

## Modifying an Existing Role
### Example 1: Modifying Role Permissions
```json
{
  "comment": "Upgrading Moderator permissions to include manage_messages.",
  "actions": [
    {
      "action": "role",
      "id": "Moderator",
      "name": "Moderator",
      "colour": "#3498DB",
      "mentionable": true,
      "hoist": true,
      "position": 5,
      "deny": [],
      "reason": "Granting full permissions to Senior Moderators."
    }
  ]
}
```

### Example 2: Modifying Role Appearance
```json
{
  "comment": "Updating Verified role color and making it mentionable.",
  "actions": [
    {
      "action": "role",
      "id": "Verified",
      "name": "Verified",
      "colour": "#E74C3C",
      "mentionable": true,
      "hoist": true,
      "position": 4,
      "deny": ["administrator", "manage_channels", "manage_guild", "manage_messages", "manage_nicknames", "manage_roles", "manage_webhooks", "manage_expressions", "manage_events", "manage_threads", "view_audit_log", "view_creator_monetization_analytics", "view_guild_insights", "kick_members", "ban_members", "mute_members", "deafen_members", "move_members", "moderate_members", "mention_everyone", "priority_speaker", "create_expressions", "create_events", "set_voice_channel_status", "pin_messages", "bypass_slowmode"],
      "reason": "Updating Verified role styling for rebranding."
    }
  ]
}
```

### Example 3: Modifying by Role ID
```json
{
  "comment": "Disabling @everyone mention for existing role by ID.",
  "actions": [
    {
      "action": "role",
      "id": 123456789012345678,
      "name": "Community",
      "colour": "#F39C12",
      "mentionable": false,
      "hoist": true,
      "position": 2,
      "deny": ["administrator", "manage_channels", "manage_guild", "manage_messages", "manage_nicknames", "manage_roles", "manage_webhooks", "manage_expressions", "manage_events", "manage_threads", "view_audit_log", "view_creator_monetization_analytics", "view_guild_insights", "kick_members", "ban_members", "mute_members", "deafen_members", "move_members", "moderate_members", "mention_everyone", "priority_speaker", "create_expressions", "create_events", "set_voice_channel_status", "pin_messages", "bypass_slowmode"],
      "reason": "Revoking mention_everyone from Community role."
    }
  ]
}
```

## Edge Cases
### Example 1: Creating a Bot Role with Minimal Permissions
```json
{
  "comment": "Creating a restricted bot role with only necessary permissions.",
  "actions": [
    {
      "action": "role",
      "name": "Music Bot",
      "colour": "#1ABC9C",
      "mentionable": false,
      "hoist": false,
      "position": 10,
      "deny": ["administrator", "manage_channels", "manage_guild", "manage_messages", "manage_nicknames", "manage_roles", "manage_webhooks", "manage_expressions", "manage_events", "manage_threads", "view_audit_log", "view_creator_monetization_analytics", "view_guild_insights", "kick_members", "ban_members", "mute_members", "deafen_members", "move_members", "moderate_members", "mention_everyone", "priority_speaker", "create_expressions", "create_events", "set_voice_channel_status", "pin_messages", "bypass_slowmode", "create_instant_invite", "stream", "send_tts_messages", "external_emojis", "external_stickers", "request_to_speak", "create_public_threads", "create_private_threads", "send_messages_in_threads", "use_embedded_activities", "use_soundboard", "use_external_sounds", "send_voice_messages", "send_polls", "use_external_apps"],
      "reason": "Creating restricted bot role."
    }
  ]
}
```

### Example 2: Creating a Role at Specific Position
```json
{
  "comment": "Creating Staff role positioned between Admin and Moderator.",
  "actions": [
    {
      "action": "role",
      "name": "Staff",
      "colour": "#E67E22",
      "mentionable": true,
      "hoist": true,
      "position": 6,
      "deny": ["administrator", "manage_guild", "view_creator_monetization_analytics"],
      "reason": "Creating Staff role for team members."
    }
  ]
}
```

### Example 3: Renaming and Repositioning an Existing Role
```json
{
  "comment": "Renaming Veteran role to Legend and adjusting position.",
  "actions": [
    {
      "action": "role",
      "id": "Veteran",
      "name": "Legend",
      "colour": "#F1C40F",
      "mentionable": true,
      "hoist": true,
      "position": 2,
      "deny": ["administrator", "manage_channels", "manage_guild", "manage_messages", "manage_nicknames", "manage_roles", "manage_webhooks", "manage_expressions", "manage_events", "manage_threads", "view_audit_log", "view_creator_monetization_analytics", "view_guild_insights", "kick_members", "ban_members", "mute_members", "deafen_members", "move_members", "moderate_members", "mention_everyone", "priority_speaker", "create_expressions", "create_events", "set_voice_channel_status", "pin_messages", "bypass_slowmode"],
      "reason": "Renaming Veteran to Legend for brand consistency."
    }
  ]
}
```

### Example 4: Creating a No-Permission "Prison" Role
```json
{
  "comment": "Creating a restricted role for muted/timeout users.",
  "actions": [
    {
      "action": "role",
      "name": "Muted",
      "colour": "#7F8C8D",
      "mentionable": false,
      "hoist": false,
      "position": 0,
      "deny": ["administrator", "manage_channels", "manage_guild", "manage_messages", "manage_nicknames", "manage_roles", "manage_webhooks", "manage_expressions", "manage_events", "manage_threads", "view_audit_log", "view_creator_monetization_analytics", "view_guild_insights", "kick_members", "ban_members", "mute_members", "deafen_members", "move_members", "moderate_members", "mention_everyone", "priority_speaker", "create_expressions", "create_events", "set_voice_channel_status", "pin_messages", "bypass_slowmode", "create_instant_invite", "add_reactions", "stream", "send_messages", "send_tts_messages", "embed_links", "attach_files", "external_emojis", "connect", "speak", "use_voice_activation", "change_nickname", "use_application_commands", "request_to_speak", "create_public_threads", "create_private_threads", "external_stickers", "send_messages_in_threads", "use_embedded_activities", "use_soundboard", "use_external_sounds", "send_voice_messages", "send_polls", "use_external_apps"],
      "reason": "Creating muted role for timeout enforcement."
    }
  ]
}
```