from typing import Optional, Annotated, Union, Literal
from pydantic import BaseModel, StringConstraints, Field

class RoleManagement(BaseModel):
    action: Literal["role"] = Field(default="role")
    id: int | str | None = Field(default=None, description="ID or NAME of role to modify. Leave empty when creating.")
    name: str = Field(description="Name of the role.")
    colour: str = Field(default="#000000", description='Hex string, e.g: "#FFFFFF"')
    mentionable: bool = Field(default=False, description="Whether a role can be mentioned or not.")
    hoist: bool = Field(default=False, description="Whether a role will display separately or not in the user list.")
    position: int = Field(default=0, description="Hierarchy position of the role.")
    deny: list[str] = Field(default=[], description="List of permissions to DISALLOW. All permissions (including Administrator) are granted by default.")
    reason: Annotated[str, StringConstraints(max_length=200)] = Field(default="Automated Action by Stagehand.", description="Reason for change.")

class ChannelManagement(BaseModel):
    action: Literal["channel"] = Field(default="channel")
    id: int | str | None = Field(default=None, description="ID or NAME of channel to modify. Leave empty when creating.")
    name: str = Field(description="Name of the channel.")
    type: Literal["text", "voice", "category", "news", "forum", "stage", "public_thread", "private_thread"] = Field(description="Type of the channel.")
    topic: str | None = Field(default=None, description="Topic of the channel.")
    nsfw: bool = Field(default=False, description="Whether the channel is NSFW.")
    category: int | str | None = Field(default=None, description="ID or NAME of the parent category.")
    position: int | None = Field(default=None, description="Position of the channel.")
    bitrate: int = Field(default=64000, description="Bitrate for voice/stage channels.")
    userLimit: int = Field(default=0, description="User limit for voice/stage channels.")
    slowmode: int = Field(default=0, description="Slowmode delay in seconds.")
    overwrites: dict[int | str, list[str]] = Field(default={}, description="Mapping of Target (Role/Name) to list of permissions to DENY.")
    reason: Annotated[str, StringConstraints(max_length=200)] = Field(default="Automated Action by Stagehand.", description="Reason for creating/modifying.")

class DecisionPlan(BaseModel):
    comments: Annotated[str, StringConstraints(max_length=500)] = Field(description="Brief comments about what tasks are needed. Max 500 characters.")
    rolesNeeded: bool = Field(description="Whether role creation/modification is requested.")
    channelsNeeded: bool = Field(description="Whether channel creation/modification is requested.")

class RoleImplementationPlan(BaseModel):
    comments: Annotated[str, StringConstraints(max_length=500)] = Field(description="Brief comments about the plan. Max 500 characters.")
    actions: list[RoleManagement] = Field(default=[], description="List of role actions to perform.")

class ChannelImplementationPlan(BaseModel):
    comments: Annotated[str, StringConstraints(max_length=500)] = Field(description="Brief comments about the plan. Max 500 characters.")
    actions: list[ChannelManagement] = Field(default=[], description="List of channel actions to perform.")