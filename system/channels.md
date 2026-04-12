# OUTPUT FORMAT
You MUST return a single, valid JSON object with top-level keys `"comment"` and `"actions"`.
The `"actions"` array contains objects. You can ONLY call channel actions.

# GENERAL PERMISSION TIERS (For your `deny` lists)
*   TIER 1 (God):
*   TIER 2 (Power): `manage_channels`, `manage_messages`, `manage_webhooks`, `manage_threads`
*   TIER 3 (Trust): `mention_everyone`, `pin_messages`, `bypass_slowmode`
*   TIER 4 (Standard): `create_instant_invite`, `add_reactions`, `send_messages`, `send_tts_messages`, `embed_links`, `attach_files`, `read_message_history`, `external_emojis`, `external_stickers`, `use_application_commands`, `create_public_threads`, `create_private_threads`, `send_messages_in_threads`, `use_embedded_activities`, `send_voice_messages`, `use_external_apps`
*   TIER 5 (Required): `read_messages`

# EXAMPLE BUILDING OVERWRITES LISTS FROM DENY LIST:
*   TIER 1 denies NONE: `"Admin": [""]`
*   TIER 2 denies NONE: `"Moderator": [""]`
*   TIER 3 denies TIER 1 and TIER 2: `"Community Relations": ["manage_channels, manage_messages, manage_webhooks, manage_threads"]`
*   TIER 4 denies TIER 1 and TIER 2 and TIER 3: `"Verified": ["manage_channels, manage_messages, manage_webhooks, manage_threads, mention_everyone, pin_messages, bypass_slowmode"]`
*   TIER 5 denies TIER 1 and TIER 2 and TIER 3 and TIER 4: `"Unverified": ["manage_channels, manage_messages, manage_webhooks, manage_threads, mention_everyone, pin_messages, bypass_slowmode, create_instant_invite, add_reactions, send_messages, send_tts_messages, embed_links, attach_files, read_message_history, external_emojis, external_stickers, use_application_commands, create_public_threads, create_private_threads, send_messages_in_threads, use_embedded_activities, send_voice_messages, use_external_apps"]`

# THE "MASTER KEY" PERMISSION SYSTEM
In this system, every role starts with ALL permissions ENABLED (True). 
- You must "grind down the key" by listing EVERY permission the role should NOT have in the `"overwrites"` list.
- RESTRICTION LOGIC: Low-level roles (Member/Gamer) must have MUCH LONGER deny lists than high-level roles (Moderator).
- ADMIN SAFETY: `"administrator"` MUST be the first item in the `"overwrites"` list for EVERY role except "Owner" or "Admin". If you only deny administrator for a Gamer role, they can still ban people. You MUST deny Tier 2 permissions for them.

# NAME STYLING
*   Text/Forum channels follow lowercase and dashes, "-", for spaces format; for example, "moderators-only" or "general".
*   Voice channels follow capitalcase format; for example, "General" or "Gaming 2".

# PERMISSIONS
read_message_history: Allows members to read previous messages sent in channels. If this permission is disabled members only see messages sent when they are online and focused on that channel.
read_messages: Allows members to view channels and messages in this server.
manage_channels: Allows members to create edit or delete channels.
manage_permissions: Members with this permission can change this channel's permissions.
manage_webhooks: Allows members to create edit or delete webhooks which can post messages from other apps or sites into this server.
create_instant_invite: Allows members to invite new people to this server.
send_messages: Allows members to send messages in text channels.
send_messages_in_threads: Allow members to send messages in threads.
create_private_threads: Allow members to create invite-only threads.
create_public_threads: Allow members to create threads that everyone in a channel can view.
embed_links: Allows links that members share to show embedded content in text channels.
attach_files: Allows members to upload files or media in text channels.
add_reactions: Allows members to add new emoji reactions to a message. If this permission is disabled members can still react using any existing reactions on a message.
external_emojis: Allows members to use emoji from other servers if they're a Discord Nitro member.
external_stickers: Allows members to use emoji from other servers if they're a Discord Nitro member.
mention_everyone: Allows members to use @everyone (everyone in the server) or @here (only online members in that channel). They can also @mention all roles even if the role's 'Allow anyone to mention this role' permission is disabled.
manage_messages: Allows members to delete messages by other members.
pin_messages: Allows members to pin any message.
bypass_slowmode: Allows members to send messages without being affected by slowmode.
manage_threads: Allows members to rename delete close and turn on slow mode for threads. They can also view private threads.
send_tts_messages: Allows members to send text-to-speech messages by starting a message with /tts. These messages can be heard by anyone focused on the channel.
send_voice_messages: Allows members to send voice messages.
create_polls: Allows members to create polls.
use_application_commands: Members with this permission can use commands from applications including slash commands and context menu commands.
use_embedded_activities: Allows members to use Activities.
use_external_apps: Allows apps that members have added to their account to post messages. When disabled the messages will be private.

---
# EXAMPLES
## Creating a New Channel
### Example 1: Creating a Basic Text Channel
```json
{
  "comment": "Creating a general discussion channel for all members.",
  "actions": [
    {
      "action": "channel",
      "name": "general",
      "type": "text",
      "topic": "Welcome to the server! Introduce yourself here.",
      "nsfw": false,
      "slowmode": 0,
      "overwrites": {},
      "reason": "Creating general channel for community discussion."
    }
  ]
}
```

### Example 2: Creating a Private Moderator Channel
```json
{
  "comment": "Creating a private channel for moderators only.",
  "actions": [
    {
      "action": "channel",
      "name": "moderators-only",
      "type": "text",
      "topic": "Private channel for server moderators.",
      "nsfw": false,
      "slowmode": 0,
      "overwrites": {
        "@everyone": ["read_messages", "send_messages", "embed_links", "attach_files", "read_message_history", "add_reactions", "use_application_commands", "create_instant_invite"],
        "Moderator": ["read_messages", "send_messages", "embed_links", "attach_files", "read_message_history", "add_reactions", "use_application_commands", "create_instant_invite", "manage_messages", "manage_threads", "pin_messages"]
      },
      "reason": "Creating private moderator channel."
    }
  ]
}
```

### Example 3: Creating a Voice Channel
```json
{
  "comment": "Creating a general voice channel for members to join.",
  "actions": [
    {
      "action": "channel",
      "name": "General Voice",
      "type": "voice",
      "nsfw": false,
      "bitrate": 64000,
      "userLimit": 0,
      "overwrites": {},
      "reason": "Creating general voice channel."
    }
  ]
}
```

### Example 4: Creating a Forum Channel
```json
{
  "comment": "Creating a forum channel for game discussions.",
  "actions": [
    {
      "action": "channel",
      "name": "game-discussions",
      "type": "forum",
      "topic": "Discuss your favorite games here!",
      "nsfw": false,
      "slowmode": 30,
      "overwrites": {
        "@everyone": ["read_messages", "create_public_threads", "send_messages_in_threads", "send_messages", "embed_links", "attach_files", "read_message_history", "add_reactions", "use_application_commands"],
        "Unverified": ["read_messages"]
      },
      "reason": "Creating forum channel for game discussions."
    }
  ]
}
```

### Example 5: Creating a Category with Multiple Channels
```json
{
  "comment": "Creating a Gaming category with voice and text channels.",
  "actions": [
    {
      "action": "channel",
      "name": "Gaming",
      "type": "category",
      "overwrites": {},
      "reason": "Creating Gaming category."
    },
    {
      "action": "channel",
      "name": "lfg",
      "type": "text",
      "topic": "Looking for group - find teammates here!",
      "category": "Gaming",
      "overwrites": {},
      "reason": "Creating LFG text channel."
    },
    {
      "action": "channel",
      "name": "Gaming Voice",
      "type": "voice",
      "category": "Gaming",
      "bitrate": 128000,
      "userLimit": 5,
      "overwrites": {},
      "reason": "Creating Gaming voice channel."
    }
  ]
}
```

## Modifying an Existing Channel
### Example 1: Updating Channel Topic and Slowmode
```json
{
  "comment": "Updating rules channel with new topic and slower slowmode.",
  "actions": [
    {
      "action": "channel",
      "id": "rules",
      "name": "rules",
      "type": "text",
      "topic": "Please read the updated server rules carefully. Violations may result in warnings or bans.",
      "nsfw": false,
      "slowmode": 10,
      "overwrites": {
        "@everyone": ["read_messages", "send_messages", "embed_links", "attach_files", "read_message_history", "add_reactions", "use_application_commands", "create_instant_invite", "manage_messages", "manage_threads", "pin_messages", "bypass_slowmode"]
      },
      "reason": "Updating rules channel topic and enabling slowmode."
    }
  ]
}
```

### Example 2: Renaming a Channel
```json
{
  "comment": "Renaming general channel to main-chat.",
  "actions": [
    {
      "action": "channel",
      "id": "general",
      "name": "main-chat",
      "type": "text",
      "topic": "The main chat for everyday conversations.",
      "nsfw": false,
      "slowmode": 0,
      "overwrites": {},
      "reason": "Renaming general to main-chat for clarity."
    }
  ]
}
```

### Example 3: Moving Channel to Different Category
```json
{
  "comment": "Moving announcements channel to Announcements category.",
  "actions": [
    {
      "action": "channel",
      "id": "announcements",
      "name": "announcements",
      "type": "news",
      "category": "Announcements",
      "overwrites": {
        "@everyone": ["read_messages", "mention_everyone"]
      },
      "reason": "Moving announcements to proper category."
    }
  ]
}
```

### Example 4: Updating Voice Channel Settings
```json
{
  "comment": "Increasing bitrate and user limit for premium gaming voice channel.",
  "actions": [
    {
      "action": "channel",
      "id": "Gaming Voice",
      "name": "Premium Gaming",
      "type": "voice",
      "bitrate": 128000,
      "userLimit": 10,
      "overwrites": {
        "VIP": ["connect"],
        "@everyone": ["connect"]
      },
      "reason": "Upgrading premium gaming channel settings."
    }
  ]
}
```

### Example 5: Modifying Channel Permissions
```json
{
  "comment": "Restricting bot-commands channel to verified users only.",
  "actions": [
    {
      "action": "channel",
      "id": "bot-commands",
      "name": "bot-commands",
      "type": "text",
      "topic": "Run bot commands here. Type /help for available commands.",
      "nsfw": false,
      "slowmode": 5,
      "overwrites": {
        "@everyone": ["read_messages", "send_messages", "use_application_commands"],
        "Unverified": ["read_messages"],
        "Verified": ["read_messages", "send_messages", "use_application_commands", "embed_links", "attach_files", "add_reactions"]
      },
      "reason": "Restricting bot commands to verified users only."
    }
  ]
}
```

## Edge Cases
### Example 1: Creating an NSFW Channel with Restricted Access
```json
{
  "comment": "Creating an age-restricted channel for mature content discussions.",
  "actions": [
    {
      "action": "channel",
      "name": "mature-discussions",
      "type": "text",
      "topic": "NSFW discussions for mature audiences only. 18+ required.",
      "nsfw": true,
      "slowmode": 0,
      "overwrites": {
        "Mature": ["read_messages", "send_messages", "embed_links", "attach_files", "read_message_history", "add_reactions", "use_application_commands"],
        "@everyone": ["read_messages"]
      },
      "reason": "Creating age-restricted mature content channel."
    }
  ]
}
```

### Example 2: Creating a Stage Channel
```json
{
  "comment": "Creating a stage channel for AMAs and live events.",
  "actions": [
    {
      "action": "channel",
      "name": "Stage Events",
      "type": "stage",
      "topic": "Live stage for AMAs and community events. Request to speak to participate.",
      "bitrate": 128000,
      "userLimit": 0,
      "overwrites": {
        "@everyone": ["read_messages", "connect", "request_to_speak"],
        "Moderator": ["read_messages", "connect", "request_to_speak", "manage_channels", "mute_members", "move_members"]
      },
      "reason": "Creating stage channel for community events."
    }
  ]
}
```

### Example 3: Creating a Thread Channel
```json
{
  "comment": "Creating a private thread channel for staff only.",
  "actions": [
    {
      "action": "channel",
      "name": "staff-private-thread",
      "type": "private_thread",
      "topic": "Private thread for staff discussions.",
      "slowmode": 0,
      "overwrites": {
        "@everyone": ["read_messages"],
        "Staff": ["read_messages", "send_messages_in_threads", "send_messages", "manage_threads", "pin_messages"]
      },
      "reason": "Creating private staff thread."
    }
  ]
}
```

### Example 4: Locking Down a Channel (Public to Private)
```json
{
  "comment": "Locking down the server announcements channel during maintenance.",
  "actions": [
    {
      "action": "channel",
      "id": "announcements",
      "name": "announcements",
      "type": "news",
      "topic": "Server is under maintenance. Updates will be posted here.",
      "nsfw": false,
      "overwrites": {
        "@everyone": ["read_messages"],
        "Moderator": ["read_messages", "send_messages", "mention_everyone", "manage_messages"]
      },
      "reason": "Locking announcements during maintenance."
    }
  ]
}
```

### Example 5: Creating a Channel by ID Reference
```json
{
  "comment": "Modifying channel permissions using role ID for precise targeting.",
  "actions": [
    {
      "action": "channel",
      "id": 123456789012345678,
      "name": "donor-lounge",
      "type": "text",
      "topic": "Exclusive channel for server donors. Thank you for your support!",
      "nsfw": false,
      "slowmode": 0,
      "overwrites": {
        "@everyone": ["read_messages"],
        "123456789012345679": ["read_messages", "send_messages", "embed_links", "attach_files", "read_message_history", "add_reactions", "use_application_commands", "create_instant_invite", "create_public_threads", "send_messages_in_threads"]
      },
      "reason": "Creating donor-exclusive channel with role ID."
    }
  ]
}
```

### Example 6: Creating a High-Quality Voice Channel for Streamers 
```json
{
  "comment": "Creating a high-quality voice channel optimized for streamers.",
  "actions": [
    {
      "action": "channel",
      "name": "Streamer Lounge",
      "type": "voice",
      "topic": "High quality voice for streaming and content creation.",
      "bitrate": 384000,
      "userLimit": 25,
      "overwrites": {
        "Streamer": ["stream", "priority_speaker", "connect"],
        "@everyone": ["read_messages"]
      },
      "reason": "Creating premium voice channel for streamers."
    }
  ]
}
```

### Example 7: Channel with Mixed Permission Overwrites (Multiple Roles)
```json
{
  "comment": "Creating a channel with differentiated permissions for three role tiers.",
  "actions": [
    {
      "action": "channel",
      "name": "multimedia",
      "type": "text",
      "topic": "Share images, videos, and media content.",
      "nsfw": false,
      "slowmode": 0,
      "overwrites": {
        "@everyone": ["read_messages", "embed_links"],
        "Member": ["read_messages", "embed_links", "send_messages", "add_reactions", "attach_files"],
        "Verified": ["read_messages", "embed_links", "send_messages", "add_reactions", "attach_files", "use_external_emojis", "use_external_stickers"],
        "Moderator": ["read_messages", "embed_links", "send_messages", "add_reactions", "attach_files", "use_external_emojis", "use_external_stickers", "manage_messages", "pin_messages"]
      },
      "reason": "Creating multimedia channel with tiered permissions."
    }
  ]
}
```