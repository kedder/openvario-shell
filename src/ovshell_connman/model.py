from typing import Any, Dict

from dbus_next import Variant

from .api import ConnmanService, ConnmanServiceState, ConnmanTechnology


def create_service_from_props(path: str, props: Dict[str, Any]) -> ConnmanService:
    model_props = _convert_service_props(props)
    return ConnmanService(path, **model_props)


def update_service_from_props(service: ConnmanService, props: Dict[str, Any]) -> None:
    model_props = _convert_service_props(props)
    service.__dict__.update(model_props)


def create_technology_from_props(path: str, props: Dict[str, Any]) -> ConnmanTechnology:
    model_props = _convert_tech_props(props)
    return ConnmanTechnology(path, **model_props)


def update_technoology_from_props(
    technology: ConnmanTechnology, props: Dict[str, Any]
) -> None:
    model_props = _convert_tech_props(props)
    technology.__dict__.update(model_props)


def _convert_tech_props(props: Dict[str, Variant]) -> Dict[str, Any]:
    propmap = {
        "Name": "name",
        "Type": "type",
        "Connected": "connected",
        "Powered": "powered",
    }
    return {pp: props[dp].value for dp, pp in propmap.items() if dp in props}


def _convert_service_props(props: Dict[str, Variant]) -> Dict[str, Any]:
    propmap = {
        "AutoConnect": "auto_connect",
        "Favorite": "favorite",
        "Name": "name",
        "Security": "security",
        "Strength": "strength",
        "Type": "type",
    }
    converted = {pp: props[dp].value for dp, pp in propmap.items() if dp in props}
    if "State" in props:
        converted["state"] = ConnmanServiceState(props["State"].value)
    return converted
