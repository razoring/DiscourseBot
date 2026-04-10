from typing import Optional, Annotated, Union, Literal
from pydantic import BaseModel, StringConstraints, Field

class RoleManagement(BaseModel):
    action: Literal["role"] = Field(default="role")
    id: Optional[int | str] = Field(default=None, description="ID or NAME of role to modify. Leave empty when creating.")
    name: str = Field(description="Name of the role.")
    colour: str = Field(default="#000000", description='Hex string, e.g: "#FFFFFF"')
    mentionable: bool = Field(default=False, description="Whether a role can be mentioned or not.")
    hoist: bool = Field(default=False, description="Whether a role will display separately or not in the user list.")
    position: int = Field(default=0, description="Hierarchy position of the role.")
    permissions: list[str] = Field(default=[], description="List of selected permissions from the appended.")
    reason: Annotated[str, StringConstraints(max_length=200)] = Field(default="Automated Action by Stagehand.", description="Reason for change.")

class ChannelOverwrite(BaseModel):
    id: int | str = Field(description="ID or NAME of role or member to apply override to.")
    allow: list[str] = Field(default=[], description="List of permissions to allow.")
    deny: list[str] = Field(default=[], description="List of permissions to deny.")

class ChannelManagement(BaseModel):
    action: Literal["channel"] = Field(default="channel")
    id: Optional[int | str] = Field(default=None, description="ID or NAME of channel to modify. Leave empty when creating.")
    name: str = Field(description="Name of the channel.")
    type: Literal["text", "voice", "category", "news", "forum", "stage", "public_thread", "private_thread"] = Field(description="Type of the channel.")
    topic: Optional[str] = Field(default=None, description="Topic of the channel.")
    nsfw: bool = Field(default=False, description="Whether the channel is NSFW.")
    category: Optional[int | str] = Field(default=None, description="ID or NAME of the parent category.")
    position: Optional[int] = Field(default=None, description="Position of the channel.")
    bitrate: int = Field(default=64000, description="Bitrate for voice/stage channels.")
    userLimit: int = Field(default=0, description="User limit for voice/stage channels.")
    slowmode: int = Field(default=0, description="Slowmode delay in seconds.")
    overwrites: list[ChannelOverwrite] = Field(default=[], description="List of local permission overwrites.")
    reason: Annotated[str, StringConstraints(max_length=200)] = Field(default="Automated Action by Stagehand.", description="Reason for creating/modifying.")

class Delete(BaseModel):
    action: Literal["delete"] = Field(default="delete")
    id: int | str = Field(description="ID or NAME of channel/role to delete.")
    type: Literal["role", "channel"] = Field(description='"role" for roles, "channel" for channels.')
    reason: Annotated[str, StringConstraints(max_length=200)] = Field(default="Automated Action by Stagehand.", description="Reason for deleting.")

class ImplementationPlan(BaseModel):
    comments: Annotated[str, StringConstraints(max_length=500)] = Field(description="Brief comments about the plan. Max 500 characters.")
    actions: list[RoleManagement|ChannelManagement] = Field(description="List of actions to perform.") # |Delete] 
