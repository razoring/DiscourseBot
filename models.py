from typing import Optional, Annotated, Union, Literal
from pydantic import BaseModel, StringConstraints, Field

class ChannelOverwrite(BaseModel):
    id: int | str = Field(description="ID or NAME of role or member to apply override to.")
    allow: list[str] = Field(default=[], description="List of permissions to allow.")
    deny: list[str] = Field(default=[], description="List of permissions to deny.")

class Action(BaseModel):
    actionType: Literal["role", "channel"] = Field(description="Use 'channel' for text/voice/categories, 'role' for groups of people.")
    id: Optional[int | str] = Field(default=None, description="Existing Name or ID. Use '@everyone' for everyone. Leave null for creation.")
    name: str = Field(description="Desired display name.")
    
    # Channel specific (Ignored for roles)
    channelType: Optional[Literal["text", "voice", "category", "news", "forum", "stage", "public_thread", "private_thread"]] = Field(default=None, description="REQUIRED if actionType is 'channel'.")
    category: Optional[int | str] = Field(default=None, description="Parent category name or ID (channels only).")
    topic: Optional[str] = Field(default=None, description="Channel topic (channels only).")
    denyPermissions: list[str] = Field(default=[], description="Permissions to DENY for @everyone (channels only).")
    
    # Role specific (Ignored for channels)
    colour: str = Field(default="#000000", description='Hex string, e.g: "#FFFFFF" (roles only).')
    hoist: bool = Field(default=False, description="Display role separately (roles only).")
    position: Optional[int] = Field(default=None, description="Hierarchy position.")
    overwrites: list[ChannelOverwrite] = Field(default=[], description="Explicit overrides for specific roles/members (channels only).")
    
    # Shared
    roleRestrictions: list[str] = Field(default=[], description="STRICTLY PERMISSION NAMES ONLY (e.g. administrator). NO NAMES OR IDS.")
    channelRestrictions: list[str] = Field(default=[], description="STRICTLY PERMISSION NAMES ONLY (e.g. viewChannel). NO NAMES OR IDS.")
    reason: Annotated[str, StringConstraints(max_length=200)] = Field(default="Automated Action by Stagehand.", description="Reason for change.")

class ImplementationPlan(BaseModel):
    comments: Annotated[str, StringConstraints(max_length=500)] = Field(description="Plan summary.")
    actions: list[Action] = Field(description="List of actions to take.")

class PlanSummary(BaseModel):
    justification: Annotated[str, StringConstraints(max_length=500)] = Field(description="Why these changes are being made.")
    consensus: Annotated[str, StringConstraints(max_length=500)] = Field(description="The final decision reached in the thread.")
    actions: list[str] = Field(description="High-level list of technical changes (e.g. 'Created #general', 'Restricted @everyone').")

class RoleSnapshot(BaseModel):
    id: int
    name: str
    colour: str
    hoist: bool
    position: int
    permissions: list[str]

class ChannelSnapshot(BaseModel):
    id: int
    name: str
    type: str
    category: Optional[int]
    topic: Optional[str]
    position: int
    overwrites: list[dict] # {id: int, type: str, allow: list[str], deny: list[str]}

class ServerSnapshot(BaseModel):
    timestamp: str
    guildId: int
    roles: list[RoleSnapshot]
    channels: list[ChannelSnapshot]

class Decision(BaseModel):
    refinedPrompt: str = Field(description="A clearer version of the user's intent.")
    needsRoles: bool = Field(description="True if the plan requires role context or modifications.")
    needsChannels: bool = Field(description="True if the plan requires channel or category context.")
    needsPermissions: bool = Field(description="True if the plan involves complex permission mapping.")
