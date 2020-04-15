from typing import Dict, Optional, Type, TypeVar
import os
import json

from ovshell import protocol

JT = TypeVar("JT", bound=protocol.JsonType)


class StoredSettingsImpl(protocol.StoredSettings):
    _settings: Dict[str, Optional[protocol.JsonType]]
    _filename: Optional[str]

    def __init__(
        self,
        settings: Dict[str, Optional[protocol.JsonType]] = None,
        filename: str = None,
    ) -> None:
        self._settings = settings or {}
        self._filename = filename

    @classmethod
    def load(cls, filename: str) -> "StoredSettingsImpl":
        if not os.path.exists(filename):
            return StoredSettingsImpl(filename=filename)

        with open(filename, "r") as f:
            settings = json.load(f)
        return StoredSettingsImpl(settings, filename)

    def save(self) -> None:
        assert self._filename is not None
        with open(self._filename, "w") as f:
            json.dump(self._settings, f, indent=4, sort_keys=True)

    def setdefault(self, key: str, value: protocol.JsonType) -> None:
        self._settings.setdefault(key, value)

    def set(self, key: str, value: Optional[protocol.JsonType], save: bool = False):
        self._settings[key] = value
        if save:
            self.save()

    def get(self, key: str, type: Type[JT], default: JT = None) -> Optional[JT]:
        v = self._settings.get(key, default)
        return v if isinstance(v, type) else None

    def getstrict(self, key: str, type: Type[JT]) -> JT:
        v = self.get(key, type)
        assert v is not None
        return v
