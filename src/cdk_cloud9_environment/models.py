# DO NOT modify this file by hand, changes will be overwritten
import sys
from dataclasses import dataclass
from inspect import getmembers, isclass
from typing import (
    AbstractSet,
    Any,
    Generic,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
)

from cloudformation_cli_python_lib.interface import (
    BaseModel,
    BaseResourceHandlerRequest,
)
from cloudformation_cli_python_lib.recast import recast_object
from cloudformation_cli_python_lib.utils import deserialize_list

T = TypeVar("T")


def set_or_none(value: Optional[Sequence[T]]) -> Optional[AbstractSet[T]]:
    if value:
        return set(value)
    return None


@dataclass
class ResourceHandlerRequest(BaseResourceHandlerRequest):
    # pylint: disable=invalid-name
    desiredResourceState: Optional["ResourceModel"]
    previousResourceState: Optional["ResourceModel"]


@dataclass
class ResourceModel(BaseModel):
    InstanceId: Optional[str]
    Name: Optional[str]
    InstanceType: Optional[str]
    Description: Optional[str]
    EBSVolumeSize: Optional[int]
    EnvironmentId: Optional[str]
    OwnerArn: Optional[str]
    Cloud9InstancePolicy: Optional["_Cloud9InstancePolicy"]

    @classmethod
    def _deserialize(
        cls: Type["_ResourceModel"],
        json_data: Optional[Mapping[str, Any]],
    ) -> Optional["_ResourceModel"]:
        if not json_data:
            return None
        dataclasses = {n: o for n, o in getmembers(sys.modules[__name__]) if isclass(o)}
        recast_object(cls, json_data, dataclasses)
        return cls(
            InstanceId=json_data.get("InstanceId"),
            Name=json_data.get("Name"),
            InstanceType=json_data.get("InstanceType"),
            Description=json_data.get("Description"),
            EBSVolumeSize=json_data.get("EBSVolumeSize"),
            EnvironmentId=json_data.get("EnvironmentId"),
            OwnerArn=json_data.get("OwnerArn"),
            Cloud9InstancePolicy=Cloud9InstancePolicy._deserialize(json_data.get("Cloud9InstancePolicy")),
        )


# work around possible type aliasing issues when variable has same name as a model
_ResourceModel = ResourceModel


@dataclass
class Cloud9InstancePolicy(BaseModel):
    PolicyName: Optional[str]
    PolicyDocument: Optional["_PolicyDocument"]

    @classmethod
    def _deserialize(
        cls: Type["_Cloud9InstancePolicy"],
        json_data: Optional[Mapping[str, Any]],
    ) -> Optional["_Cloud9InstancePolicy"]:
        if not json_data:
            return None
        return cls(
            PolicyName=json_data.get("PolicyName"),
            PolicyDocument=PolicyDocument._deserialize(json_data.get("PolicyDocument")),
        )


# work around possible type aliasing issues when variable has same name as a model
_Cloud9InstancePolicy = Cloud9InstancePolicy


@dataclass
class PolicyDocument(BaseModel):
    Version: Optional[str]
    Statement: Optional[Sequence["_PolicyStatement"]]

    @classmethod
    def _deserialize(
        cls: Type["_PolicyDocument"],
        json_data: Optional[Mapping[str, Any]],
    ) -> Optional["_PolicyDocument"]:
        if not json_data:
            return None
        return cls(
            Version=json_data.get("Version"),
            Statement=deserialize_list(json_data.get("Statement"), PolicyStatement),
        )


# work around possible type aliasing issues when variable has same name as a model
_PolicyDocument = PolicyDocument


@dataclass
class PolicyStatement(BaseModel):
    Effect: Optional[str]
    Action: Optional[Sequence[str]]
    Resource: Optional[Sequence[str]]

    @classmethod
    def _deserialize(
        cls: Type["_PolicyStatement"],
        json_data: Optional[Mapping[str, Any]],
    ) -> Optional["_PolicyStatement"]:
        if not json_data:
            return None
        return cls(
            Effect=json_data.get("Effect"),
            Action=json_data.get("Action"),
            Resource=json_data.get("Resource"),
        )


# work around possible type aliasing issues when variable has same name as a model
_PolicyStatement = PolicyStatement


