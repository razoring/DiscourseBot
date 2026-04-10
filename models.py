from typing import Optional, Annotated, Union, Literal
from pydantic import BaseModel, StringConstraints, Field

class Delete(BaseModel):
    id: int = Field(default=None, description="ID of channel/role to delete.")
    datatype: Literal["role", "channel"] = Field(description='"role" defines that a role with the id is being deleted. "channel" means that a channel with the id is being deleted')
    reason: Annotated[str,StringConstraints(max_length=200)] = Field(description="Reason for deleting. Max is 200 characters.")

class RoleManagement(BaseModel):
    id: Optional[int] = Field(default=None, description="Only required when modifying an existing role; leave empty when creating. ID of role to modify.")
    name: str = Field(description="Name of the role.")
    colour: str = Field(description='Hex string, e.g: "#FFFFFF"')
    mentionable: bool = Field(description="Whether a role can be mentioned or not.")
    hoist: bool = Field(description="Whether a role will display separately or not in the user list.")
    reason: Annotated[str,StringConstraints(max_length=200)] = Field(description="Reason for change. Max is 200 characters.")
    position: int = Field(description="Heirarchy of role.")
    permissions: list[str] = Field(description="List of selected permissions from the appended.")
    
class ChannelOverwrite(BaseModel):
    id: int = Field(description="ID of role or member to apply override to.")
    allow: list[str] = Field(default=[], description="List of permissions to allow.")
    deny: list[str] = Field(default=[], description="List of permissions to deny.")

class ChannelManagement(BaseModel):
    id: Optional[int] = Field(default=None, description="Only required when modifying an existing channel; leave empty when creating. ID of channel to modify.")
    name: str = Field(description="Name of the channel.")
    type: Literal["text", "voice", "category", "news", "forum", "stage"] = Field(description="Type of the channel.")
    reason: Annotated[str, StringConstraints(max_length=200)] = Field(description="Reason for creating/modifying. Max 200 characters.")
    overwrites: list[ChannelOverwrite] = Field(default=[], description="List of permission overwrites for the channel.")

class ImplementationPlan(BaseModel):
    comments: Annotated[str, StringConstraints(max_length=500)] = Field(description="Brief comments about the plan. Max 500 characters.")
    actions: list[Union[Delete, RoleManagement, ChannelManagement]] = Field(description="List of actions to perform.")
