import logging
from dataclasses import dataclass
import typing
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Type,
    Union,
)
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

@dataclass
class ProvisioningStatus(dict):
    def __init__(self):
        dict.__init__(self, Type=type(self).__name__)
    def __str__(self):
        return self.__class__
    def _serialize(self) -> Mapping[str, Any]:
        return {"Type": self.__class__}
    @classmethod
    def _deserialize(
        cls: Type["ProvisioningStatus"], json_data: Optional[Mapping[str, Any]]
    ) -> Optional["ProvisioningStatus"]:
        return globals()[json_data["Type"]]()

class EnvironmentCreated(ProvisioningStatus): pass
class RoleCreated(ProvisioningStatus): pass
class ProfileAttached(ProvisioningStatus): pass
class CommandSent(ProvisioningStatus): pass
class InstanceStable(ProvisioningStatus): pass
class ResizedInstance(ProvisioningStatus): pass
