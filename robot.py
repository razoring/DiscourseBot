import inspect
import json
import asyncio
import traceback
import os
from typing import Optional,get_args, Literal
import discord
from discord import app_commands
from discord.ext import commands
from ollama import ChatResponse
from ollama import AsyncClient
from dotenv import load_dotenv
from pydantic import BaseModel
import datetime
import io
from models import Decision, ImplementationPlan, Action, PlanSummary, ServerSnapshot, RoleSnapshot, ChannelSnapshot

PLAN_SOUL_PATH = "system/plan.md"
DECISION_SOUL_PATH = "system/decision.md"

class Robot(commands.Cog):
    def __init__(self, bot):
        self._bot = bot
        self._planSoul = ""
        self._decisionSoul = ""
        self._checkpointDir = "checkpoints"
        
        if not os.path.exists(self._checkpointDir):
            os.makedirs(self._checkpointDir)
        
        with open(PLAN_SOUL_PATH, "r") as file:
            self._planSoul = file.read()
        with open(DECISION_SOUL_PATH, "r") as file:
            self._decisionSoul = file.read()

        # Context Menus must be added manually in Cogs
        self.ctx_menu = app_commands.ContextMenu(
            name='Implement Plan',
            callback=self.stagehandContext,
        )
        self._bot.tree.add_command(self.ctx_menu)

    @commands.Cog.listener("on_ready")
    async def onReady(self):
        await AsyncClient().chat(model="gemma4:e2b", messages=[{"role": "user", "content": "Hello world!"}], think=False)

    @commands.Cog.listener("on_message")
    async def onMessage(self, msg: discord.Message):
        if not self._bot.is_ready(): return
        if msg.author == self._bot.user: return
        if msg.reference and isinstance(msg.reference.resolved, discord.Message):
            replied = msg.reference.resolved
            if replied.author == self._bot.user:
                async with msg.channel.typing():
                    decision = await self.getDecision(msg.content)
                    context = await self.getContext(msg, decision)
                    # Request with JSON schema to enforce the ImplementationPlan structure
                    reply: ChatResponse = await AsyncClient().chat(model="gemma4:e2b", messages=context, think=True, format=ImplementationPlan.model_json_schema())
                    parts = await self.processResponse(msg.guild, reply.message.content, execute=False)
                    
                    for i, text in enumerate(parts):
                        if i == 0: await msg.reply(text)
                        else: await msg.channel.send(text)
                    
                    await msg.channel.send("**Plan Generated.** Right-click the plan or previous message and select **Apps -> Implement Plan** to deploy.")

    @app_commands.command(name="plan", description="Instruct Stagehand to create an implementation plan")
    @app_commands.describe(instructions="Instructions to send")
    async def plan(self, interaction: discord.Interaction, instructions: str):
        await interaction.response.defer()
        decision = await self.getDecision(instructions)
        content = await self.getPlan(interaction.guild, decision)
        reply: ChatResponse = await AsyncClient().chat(model="gemma4:e2b", messages=[{"role": "system", "content": content}, {"role": "user", "content": decision.refinedPrompt}], think=True, format=ImplementationPlan.model_json_schema())
        messages = await self.processResponse(interaction.guild, reply.message.content)
        for i, msgText in enumerate(messages):
            if i == 0: await interaction.followup.send(msgText)
            else: await interaction.channel.send(msgText)

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload(self, ctx):
        await self._bot.reload_extension("robot")
        await self._bot.tree.sync()
        await ctx.send("Reloaded robot.py and synced commands")

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync(self, ctx):
        synced = await self._bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands globally")

    ## PRELIMINARIES
    def errorHandler(func):
        async def wrapper(*args, **kwargs):
            try:
                if inspect.iscoroutinefunction(func): return await func(*args, **kwargs)
                return func(*args, **kwargs)
            except discord.Forbidden as e: return f"403: Forbidden\nBot does not have permissions: {e}"
            except discord.HTTPException as e: return f"409: Bad Request\nBot failed to perform action: {e}"
            except Exception as e:
                traceback.print_exc()
                return f"500: Internal Server Error\nUnexpected failure {e}"
        return wrapper

    def resolveId(self, guild: discord.Guild, ref: int|str|None, datatype: Literal["role", "channel"]):
        if not ref or isinstance(ref, int): return ref
        if isinstance(ref, str) and ref.isdigit(): return int(ref)
        
        # Resolve by name
        ref_low = ref.lower().lstrip("@#")
        if datatype == "role":
            if ref_low == "everyone": return guild.default_role.id
            role = discord.utils.get(guild.roles, name=ref) or discord.utils.find(lambda r: r.name.lower() == ref_low, guild.roles)
            if role: return role.id
            
            # Fallback to member search for overwrites
            member = discord.utils.get(guild.members, name=ref) or discord.utils.find(lambda m: m.name.lower() == ref_low or (m.nick and m.nick.lower() == ref_low), guild.members)
            if member: return member.id
        else: # channel
            channel = discord.utils.get(guild.channels, name=ref) or discord.utils.find(lambda c: c.name.lower() == ref_low, guild.channels)
            if channel: return channel.id
        return ref

    async def getDecision(self, instructions: str):
        from models import Decision
        try:
            reply: ChatResponse = await AsyncClient().chat(model="gemma4:e2b", messages=[{"role": "system", "content": self._decisionSoul}, {"role": "user", "content": instructions}], think=False, format=Decision.model_json_schema())
            data = self._extractJson(reply.message.content)
            if not data:
                # Fallback to a default decision if LLM fails
                return Decision(refinedPrompt=instructions, needsRoles=True, needsChannels=True, needsPermissions=True)
            return Decision(**data)
        except Exception as e:
            print(f"Decision failed: {e}")
            return Decision(refinedPrompt=instructions, needsRoles=True, needsChannels=True, needsPermissions=True)

    def _extractJson(self, content: str):
        try:
            # Handle Python booleans if LLM slips up
            processed = content.replace(': True', ': true').replace(': False', ': false')
            
            start = processed.find('{')
            end = processed.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(processed[start:end])
            return None
        except:
            return None

    def _toSnakeCase(self, name: str):
        import re
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

    async def getContext(self, msg: discord.Message, decision: 'Decision'):
        content = await self.getPlan(msg.guild, decision)
        messages = [{"role": "assistant", "content": content}, {"role": ("system" if msg.author == self._bot.user else "user"), "content": decision.refinedPrompt}]
        current = msg

        while current.reference and current.reference.message_id:
            if isinstance(current.reference.resolved, discord.Message): current = current.reference.resolved
            else:
                try: current = await msg.channel.fetch_message(current.reference.message_id)
                except discord.NotFound: break
            messages.append({"role": ("system" if current.author == self._bot.user else "user"), "content": current.content})
        
        messages.reverse()
        return messages

    async def getPlan(self, guild: discord.Guild, decision: 'Decision'):
        updated = self._planSoul + "\n\n## TOOLS\n"
        
        from models import ImplementationPlan, Decision
        tools = ImplementationPlan.model_fields['actions']
        types = get_args(tools.annotation)[0]
        classes = get_args(types) or [types]

        for tool in classes:
            updated += f"- {tool.__name__}:\n"
            for field_name, field_info in tool.model_fields.items(): 
                updated += f"\t- {field_name}: {field_info.description}\n"
        
        if decision.needsPermissions:
            updated += "\n## ROLE PERMISSIONS\n"
            for name, _ in iter(discord.Permissions.all()): updated += f"- {name}:True/False\n"

        if guild:
            if decision.needsRoles:
                updated += "\n## EXISTING ROLES\n"
                roles = await self.listRoles(guild)
                if isinstance(roles, list):
                    for role in roles: updated += f"- Name: '{role['name']}' (ID: {role['id']}): {','.join(role['permissions'])}\n"
                else: updated += f"Error fetching roles: {roles}\n"
            
            if decision.needsChannels:
                channels = await self.listChannels(guild)
                if isinstance(channels, list):
                    updated += "\n## EXISTING CHANNELS (Default Rules Apply unless Overwrites Listed)\n"
                    for ch in channels:
                        if ch['type'] != "category":
                            p_text = ""
                            for ow in ch['overwrites']:
                                p_text += f"{ow['target']}({ow['type']}): +{','.join(ow['allow'])}, -{','.join(ow['deny'])} | "
                            updated += f"- Name: '{ch['name']}' (Type: {ch['type']}, ID: {ch['id']}): {p_text if p_text else 'Inherits @everyone role default permissions.'}\n"
                else: updated += f"Error fetching channels: {channels}\n"
        
        updated += "\n## USAGE GUIDELINES\n"
        updated += "1. 'name' must be a human-readable ROLE or CHANNEL name (e.g.,'Mod','Lounge').\n"
        updated += "2. NEVER put technical strings or permission names (like 'view_channel') in the 'name' field.\n"
        updated += "3. Avoid asking structural questions. Focus on the intent and providing the plan directly.\n"
        updated += "4. For channel overwrites, use the format: {\"id\": \"RoleName\", \"allow\": [\"viewChannel\"], \"deny\": [\"sendMessages\"]}\n"
        
        print(updated)
        return updated

    async def processResponse(self, guild: discord.Guild, content: str, execute: bool = False):
        from models import ImplementationPlan
        try:
            data = self._extractJson(content)
            if data and ("actions" in data or "comments" in data):
                plan = ImplementationPlan(**data)
                for act in plan.actions:
                    # Resolve IDs/References
                    act.id = self.resolveId(guild, act.id, act.actionType)
                    
                    # Fuzzy Recovery: If id is null, but name matches an existing item, treat it as a modification
                    if act.id is None:
                        fuzzyId = self.resolveId(guild, act.name, act.actionType)
                        if isinstance(fuzzyId, int):
                            act.id = fuzzyId
                    
                    if act.actionType == "channel" and act.category:
                        act.category = self.resolveId(guild, act.category, "channel")

                    if act.actionType == "role":
                        if execute:
                            await self.roleManagement(
                                guild=guild,
                                name=act.name,
                                id=act.id,
                                colour=act.colour,
                                hoist=act.hoist,
                                position=act.position or 0,
                                restrictions=act.roleRestrictions,
                                reason=act.reason
                            )
                    elif act.actionType == "channel":
                        # Initialize overwrites list
                        overwrites = []
                        
                        # 1. Add explicit overwrites from the action
                        for ow in act.overwrites:
                            overwrites.append({
                                "id": ow.id,
                                "allow": ow.allow,
                                "deny": ow.deny
                            })
                        
                        # 2. Add/Merge @everyone restrictions
                        everyone_denies = list(set(act.channelRestrictions) | set(act.denyPermissions))
                        if everyone_denies:
                            everyone_ow = next((o for o in overwrites if o["id"] == "@everyone"), None)
                            if everyone_ow:
                                everyone_ow["deny"] = list(set(everyone_ow["deny"]) | set(everyone_denies))
                            else:
                                overwrites.append({
                                    "id": "@everyone",
                                    "allow": [],
                                    "deny": everyone_denies
                                })
                        
                        if execute:
                            await self.channelManagement(
                                guild=guild,
                                datatype=self._parseChannelType(act.channelType),
                                name=act.name,
                                id=act.id,
                                topic=act.topic,
                                category=act.category,
                                overwrites=overwrites,
                                reason=act.reason,
                                position=act.position
                            )
                
                resolvedData = plan.model_dump()
                print(resolvedData)
                return await self.formatPlan(guild, resolvedData)
            
            return [content[i:i+1900] for i in range(0, len(content), 1900)]
        except Exception as e:
            import traceback
            traceback.print_exc()
            return [f"Error processing plan: {str(e)}"]

    def _parseChannelType(self, typeStr: str) -> discord.ChannelType:
        mapping = {
            "text": discord.ChannelType.text,
            "voice": discord.ChannelType.voice,
            "category": discord.ChannelType.category,
            "news": discord.ChannelType.news,
            "forum": discord.ChannelType.forum,
            "stage": discord.ChannelType.stage_voice,
            "public_thread": discord.ChannelType.public_thread,
            "private_thread": discord.ChannelType.private_thread,
            "publicThread": discord.ChannelType.public_thread,
            "privateThread": discord.ChannelType.private_thread
        }
        return mapping.get(typeStr, discord.ChannelType.text)

    async def formatPlan(self, guild: discord.Guild, response: dict):
        commentsText = response.get("comments", "")
        actionsList = response.get("actions", [])
        diffChunks = []
        currentDiff = []
        SEP = "-" * 25
        
        for action in actionsList:
            actionType = action.get("actionType", "").lower()
            itemId = action.get("id")
            itemName = action.get("name", "New Item")
            
            toolDiff = [SEP]
            if actionType == "role":
                if itemId and not isinstance(itemId, str):
                    toolDiff.append(f"*** '@{itemName}'")
                    oldRole = guild.get_role(itemId)
                    if oldRole:
                        # Diff shows what is being REMOVED compared to before
                        oldRestrictions = [n for n, v in oldRole.permissions if not v]
                        newRestrictions = action.get("roleRestrictions", [])
                        added = [p for p in newRestrictions if p not in oldRestrictions]
                        removed = [p for p in oldRestrictions if p not in newRestrictions]
                        for p in added: toolDiff.append(f"--​- {p}")
                        for p in removed: toolDiff.append(f"+​++ {p}")
                else:
                    toolDiff.append(f"+​++ '@{itemName}'")
                    for p in action.get("roleRestrictions", []): toolDiff.append(f"--​- {p}")
            
            elif actionType == "channel":
                prefix = "#" if action.get("channelType") != "category" else ""
                if itemId and not isinstance(itemId, str):
                    toolDiff.append(f"*** '{prefix}{itemName}'")
                else:
                    toolDiff.append(f"+​++ '{prefix}{itemName}' ({action.get('channelType', 'text')})")
                
                # Allow by Default: Only show restrictions
                for p in action.get("channelRestrictions", []): toolDiff.append(f"--​- @everyone: {p}")
            
            potentialLength = sum(len(line)+1 for line in currentDiff)+sum(len(line)+1 for line in toolDiff)+len(SEP)+20
            if potentialLength > 1900 and currentDiff:
                diffChunks.append("```diff\n"+"\n".join(currentDiff)+"\n"+SEP+"\n```")
                currentDiff = toolDiff
            else:
                currentDiff.extend(toolDiff)
        
        if currentDiff:
            currentDiff.append(SEP)
            diffChunks.append("```diff\n"+"\n".join(currentDiff)+"\n```")

        totalDiffLen = sum(len(chunk) for chunk in diffChunks)+(len(diffChunks)-1)*2
        
        if len(commentsText)+totalDiffLen+2 > 2000: return diffChunks if diffChunks else [commentsText]
        else:
            if not diffChunks: return [commentsText]
            firstChunk = commentsText+"\n\n"+diffChunks[0]
            return [firstChunk]+diffChunks[1:]
    
    @errorHandler
    async def listRoles(self, guild: discord.Guild):
        roles = []
        if not guild.roles: return []
        for role in guild.roles:
            perms = [name for name, value in role.permissions if value]
            roles.append({"name": role.name, "id": role.id, "position": role.position, "permissions": perms})
        roles.sort(key=lambda r: r["position"], reverse=True)
        return roles
    
    @errorHandler
    async def roleManagement(self, guild: discord.Guild, name: str, id: int=None, colour: str="#000000", hoist: bool=False, mentionable: bool=False, position: int=0, restrictions: list=None, reason: str="Automated Action by Stagehand."):
        restrictions = [self._toSnakeCase(p) for p in (restrictions or [])]
        
        # Fetch existing permissions if editing, otherwise start with all (Subtractive Law)
        role = guild.get_role(id) if id else None
        permsObj = role.permissions if role else discord.Permissions.all()
        
        for p in restrictions:
            if hasattr(permsObj, p):
                setattr(permsObj, p, False)
        
        colourHex = colour.replace("#", "")
        colourObj = discord.Color(int(colourHex, 16)) if colourHex else discord.Color.default()
        args = {"name": name, "permissions": permsObj, "colour": colourObj, "hoist": hoist, "mentionable": mentionable, "reason": reason}
        if not id:
            role = await guild.create_role(**args)
            if position > 0: await role.edit(position=position)
        else:
            role = guild.get_role(id)
            if role:
                final_args = {k: v for k, v in args.items() if v is not None}
                if position > 0: final_args["position"] = position
                await role.edit(**final_args)
        return role
    
    @errorHandler
    async def listChannels(self, guild: discord.Guild):
        channels = []
        for channel in guild.channels:
            overwrites = []
            for target, overwrite in channel.overwrites.items():
                allow = [n for n, v in overwrite if v is True]
                deny = [n for n, v in overwrite if v is False]
                targetName = target.name if hasattr(target, "name") else str(target)
                overwrites.append({"target": targetName, "id": target.id, "type": "role" if isinstance(target, discord.Role) else "member", "allow": allow, "deny": deny})
            channels.append({"name": channel.name, "id": channel.id, "type": str(channel.type).replace("ChannelType.", ""), "category": channel.category.name if channel.category else "None", "overwrites": overwrites})
        channels.sort(key=lambda c: (c['category'], c['name']))
        return channels
    
    @errorHandler
    async def channelManagement(self, guild: discord.Guild, datatype: discord.ChannelType, name: str, id: int=None, topic: str=None, nsfw: bool=False, category: int=None, bitrate: int=64000, userLimit: int=0, slowmode: int=0, overwrites: list=None, reason: str="Automated Action by Stagehand.", position: int=None):
        channel = None
        targets = {}
        if overwrites:
            valid_flags = [n for n, v in discord.Permissions.all()]
            for ow in overwrites:
                t_id = self.resolveId(guild, ow['id'], "role")
                target = guild.get_role(t_id) or guild.get_member(t_id) if isinstance(t_id, int) else None
                
                if target:
                    allowSide = [self._toSnakeCase(p) for p in ow.get('allow', []) if self._toSnakeCase(p) in valid_flags]
                    denySide = [self._toSnakeCase(p) for p in ow.get('deny', []) if self._toSnakeCase(p) in valid_flags]
                    targets[target] = discord.PermissionOverwrite(**{p: True for p in allowSide}, **{p: False for p in denySide})
                else:
                    print(f"[{guild.name}] Could not resolve overwrite target: {ow['id']}")
        catObj = guild.get_channel(category) if category else None
        common = {"name": name, "overwrites": targets, "reason": reason, "category": catObj, "position": position}
        if not id:
            if datatype == discord.ChannelType.text: channel = await guild.create_text_channel(**common, topic=topic, nsfw=nsfw, slowmode_delay=slowmode)
            elif datatype == discord.ChannelType.voice: channel = await guild.create_voice_channel(**common, bitrate=bitrate, user_limit=userLimit)
            elif datatype == discord.ChannelType.category: channel = await guild.create_category(name=name, overwrites=targets, reason=reason, position=position)
            elif datatype == discord.ChannelType.news: channel = await guild.create_news_channel(**common, topic=topic, nsfw=nsfw)
            elif datatype == discord.ChannelType.forum: channel = await guild.create_forum(**common, topic=topic, nsfw=nsfw)
            elif datatype == discord.ChannelType.stage_voice: channel = await guild.create_stage_channel(**common, topic=topic)
        else:
            channel = guild.get_channel(id)
            if channel:
                editMap = {"name": name, "overwrites": targets, "reason": reason, "category": catObj, "position": position, "topic": topic, "nsfw": nsfw, "slowmode_delay": slowmode, "bitrate": bitrate, "user_limit": userLimit}
                finalEdit = {k: v for k, v in editMap.items() if (hasattr(channel, k) or k in ["name", "overwrites", "reason", "category", "position"]) and v is not None}
                await channel.edit(**finalEdit)
        return channel

    @errorHandler
    async def createSnapshot(self, guild: discord.Guild) -> ServerSnapshot:
        roles = []
        for role in guild.roles:
            perms = [n for n, v in role.permissions if v]
            roles.append(RoleSnapshot(
                id=role.id,
                name=role.name,
                colour=str(role.colour),
                hoist=role.hoist,
                position=role.position,
                permissions=perms
            ))

        channels = []
        for channel in guild.channels:
            chanOverwrites = []
            for target, overwrite in channel.overwrites.items():
                allow = [n for n, v in overwrite if v is True]
                deny = [n for n, v in overwrite if v is False]
                chanOverwrites.append({
                    "id": target.id,
                    "type": "role" if isinstance(target, discord.Role) else "member",
                    "allow": allow,
                    "deny": deny
                })
            
            channels.append(ChannelSnapshot(
                id=channel.id,
                name=channel.name,
                type=str(channel.type).replace("ChannelType.", ""),
                category=channel.category_id if hasattr(channel, "category_id") else None,
                topic=getattr(channel, "topic", None),
                position=channel.position,
                overwrites=chanOverwrites
            ))
        
        return ServerSnapshot(
            timestamp=discord.utils.utcnow().isoformat(),
            guildId=guild.id,
            roles=roles,
            channels=channels
        )

    @errorHandler
    async def loadState(self, guild: discord.Guild, snapshot: ServerSnapshot, absolute: bool = False):
        if absolute:
            # Absolute: Reconcile current state to snapshot
            # 1. Update/Restore roles
            snapRoleIds = {r.id for r in snapshot.roles}
            for snapRole in snapshot.roles:
                existing = guild.get_role(snapRole.id)
                perms = discord.Permissions(**{p: True for p in snapRole.permissions})
                colour = discord.Color(int(snapRole.colour.replace("#", ""), 16))
                if existing:
                    if existing.is_default():
                        # Cannot edit name, colour, or position of @everyone
                        await existing.edit(permissions=perms)
                    else:
                        args = {"name": snapRole.name, "permissions": perms, "colour": colour, "hoist": snapRole.hoist}
                        if snapRole.position > 0: args["position"] = snapRole.position
                        await existing.edit(**args)
                else:
                    # Try to recreate
                    await guild.create_role(name=snapRole.name, permissions=perms, colour=colour, hoist=snapRole.hoist)
            
            # Delete roles not in snapshot
            for role in guild.roles:
                if role.id not in snapRoleIds and not role.is_default() and not role.managed:
                    await role.delete(reason="Restoring snapshot (Absolute)")

            # 2. Update/Restore channels
            snapChanIds = {c.id for c in snapshot.channels}
            
            # Sort to handle categories FIRST
            sortedChannels = sorted(snapshot.channels, key=lambda x: 0 if x.type == "category" else 1)
            
            for snapChan in sortedChannels:
                existing = guild.get_channel(snapChan.id)
                # Parse overwrites
                overwrites = {}
                valid_flags = [n for n, v in discord.Permissions.all()]
                for ow in snapChan.overwrites:
                    t_id = self.resolveId(guild, ow['id'], "role")
                    target = guild.get_role(t_id) or guild.get_member(t_id) if isinstance(t_id, int) else None
                    
                    if target:
                        allowSide = [p for p in ow['allow'] if p in valid_flags]
                        denySide = [p for p in ow['deny'] if p in valid_flags]
                        overwrites[target] = discord.PermissionOverwrite(**{p: True for p in allowSide}, **{p: False for p in denySide})
                
                catObj = guild.get_channel(snapChan.category) if snapChan.category else None
                if existing:
                    await existing.edit(name=snapChan.name, topic=snapChan.topic, position=snapChan.position, overwrites=overwrites, category=catObj)
                else:
                    # Recreate
                    dtype = self._parseChannelType(snapChan.type)
                    await self.channelManagement(guild, dtype, snapChan.name, topic=snapChan.topic, overwrites=snapChan.overwrites, position=snapChan.position, category=snapChan.category, execute=True) # Execute=True for Recreate

            # Delete channels not in snapshot
            for channel in guild.channels:
                if channel.id not in snapChanIds:
                    await channel.delete(reason="Restoring snapshot (Absolute)")
        else:
            # Selective: Undo Bot Actions only via Audit Log
            cutoff = datetime.datetime.fromisoformat(snapshot.timestamp)
            async for entry in guild.audit_logs(after=cutoff, oldest_first=False):
                if entry.user.id != self._bot.user.id: continue
                
                # Channel Actions
                if entry.action == discord.AuditLogAction.channel_create:
                    if entry.target: await entry.target.delete(reason="Undo Action")
                elif entry.action == discord.AuditLogAction.channel_update:
                    if entry.target:
                        changes = {}
                        for attr in ["name", "topic", "position", "nsfw", "slowmode_delay"]:
                            if hasattr(entry.before, attr):
                                val = getattr(entry.before, attr)
                                if val is not None: changes[attr] = val
                        if changes: await entry.target.edit(**changes)
                
                # Role Actions
                elif entry.action == discord.AuditLogAction.role_create:
                    if entry.target: await entry.target.delete(reason="Undo Action")
                elif entry.action == discord.AuditLogAction.role_update:
                    if entry.target:
                        changes = {}
                        for attr in ["name", "permissions", "colour", "hoist", "position", "mentionable"]:
                            if hasattr(entry.before, attr):
                                val = getattr(entry.before, attr)
                                if val is not None: changes[attr] = val
                        if changes: await entry.target.edit(**changes)

    async def stagehandContext(self, interaction: discord.Interaction, message: discord.Message):
        await self._runImplementationWorkflow(interaction, message)

    @app_commands.command(name="implement", description="Summarize the thread's decisions and prepare for implementation.")
    async def implementCommand(self, interaction: discord.Interaction):
        # Support for "Reply Context" in slash commands
        replied_msg = interaction.message
        
        # If interaction.message isn't populated (platform dependent), try to find it in resolved data
        if not replied_msg and interaction.data.get("resolved", {}).get("messages"):
            msg_id = list(interaction.data["resolved"]["messages"].keys())[0]
            replied_msg = await interaction.channel.fetch_message(int(msg_id))

        if not replied_msg:
            await interaction.response.send_message("This command must be used as a **Reply** to a message to fetch history.", ephemeral=True)
            return
        
        await self._runImplementationWorkflow(interaction, replied_msg)

    async def _runImplementationWorkflow(self, interaction: discord.Interaction, anchor_msg: discord.Message):
        if interaction.response.is_done():
            await interaction.followup.send("Processing...", ephemeral=True)
        else:
            await interaction.response.defer()
        
        # 1. Fetch History from Anchor backwards
        history = []
        async for msg in interaction.channel.history(limit=50, before=anchor_msg.created_at):
            history.append(f"{msg.author.name}: {msg.content}")
        history.append(f"{anchor_msg.author.name}: {anchor_msg.content}") # Include the anchor
        history_str = "\n".join(history[-50:]) # Take last 50
        
        # 2. Summarize Context using execute.md
        with open("system/execute.md", "r") as f:
            execute_soul = f.read()
            
        messages = [
            {"role": "system", "content": execute_soul},
            {"role": "user", "content": f"THREAD HISTORY:\n{history_str}"}
        ]
        
        summary_reply: ChatResponse = await AsyncClient().chat(model="gemma4:e2b", messages=messages, format=PlanSummary.model_json_schema())
        summary = PlanSummary(**json.loads(summary_reply.message.content))
        
        # 3. Create Snapshot
        snapshot = await self.createSnapshot(interaction.guild)
        snapshot_json = snapshot.model_dump_json(indent=2)
        
        # 4. Create Backup Webhook indicator
        ts = int(discord.utils.utcnow().timestamp())
        await interaction.channel.create_webhook(name=f"Server Backup ({ts})", reason="Automated Safeguard")
        
        # 5. Build Embed
        embed = discord.Embed(title="Implementation Summary", color=discord.Color.blue())
        embed.add_field(name="Justification", value=summary.justification, inline=False)
        embed.add_field(name="Consensus", value=summary.consensus, inline=False)
        embed.description = "**Decided Actions:**\n" + "\n".join([f"• {a}" for a in summary.actions])
        
        # 6. Attachment
        snapshot_file = discord.File(io.StringIO(snapshot_json), filename="undo.json")
        
        view = ImplementView(self, interaction.channel, snapshot)
        await interaction.followup.send(embed=embed, file=snapshot_file, view=view)

    @app_commands.command(name="undo", description="Restore server state from a snapshot (undo.json) or audit logs.")
    @app_commands.describe(file="The undo.json snapshot file.", absolute="Revert EVERY change since snapshot, not just bot actions.")
    async def undoCommand(self, interaction: discord.Interaction, file: discord.Attachment = None, absolute: bool = False):
        await interaction.response.defer(ephemeral=True)
        
        snapshot = None
        if file:
            content = await file.read()
            snapshot = ServerSnapshot(**json.loads(content.decode("utf-8")))
        
        if not snapshot:
            await interaction.followup.send("No snapshot provided. Please attach an `undo.json` file.", ephemeral=True)
            return
            
        await self.loadState(interaction.guild, snapshot, absolute)
        await interaction.followup.send(f"Restoration Complete. Mode: {'Absolute' if absolute else 'Selective'}", ephemeral=True)

class ImplementView(discord.ui.View):
    def __init__(self, robot, channel, snapshot):
        super().__init__(timeout=600)
        self.robot = robot
        self.channel = channel
        self.snapshot = snapshot

    @discord.ui.button(label="Proceed", style=discord.ButtonStyle.green)
    async def proceed(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        # 1. Fetch History for planning (from the same reply context)
        history = []
        async for msg in self.channel.history(limit=50):
            if msg.author == self.robot._bot.user: continue
            history.append(f"{msg.author.name}: {msg.content}")
        history_str = "\n".join(reversed(history))
        
        # 2. Get Decision
        decision = await self.robot.getDecision(history_str)
        # 3. Get Context
        # Fake a message object for getContext
        fake_msg = type('obj', (object,), {
            'channel': self.channel, 
            'guild': interaction.guild, 
            'author': interaction.user,
            'reference': None,
            'content': history_str,
            'created_at': discord.utils.utcnow()
        })
        context = await self.robot.getContext(fake_msg, decision)
        
        # 4. Generate & Process Plan
        reply = await AsyncClient().chat(model="gemma4:e2b", messages=context, think=True, format=ImplementationPlan.model_json_schema())
        parts = await self.robot.processResponse(interaction.guild, reply.message.content, execute=True)
        
        for text in parts:
            await self.channel.send(text)
            
        await interaction.followup.send("Implementation Successful.", ephemeral=True)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Implementation Cancelled.", ephemeral=True)
        self.stop()

async def setup(bot):
    await bot.add_cog(Robot(bot))