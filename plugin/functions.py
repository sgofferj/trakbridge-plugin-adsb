"""
Functions for ADSB to CoT conversion.
"""

import os
import json
import uuid
from typing import Any, Dict, List, Optional, Union

# Constants and environment variables
MY_CALLSIGN: str = os.getenv("CALLSIGN", "adsb.one")
MY_TYPE: str = os.getenv("MYCOT", "a-f-G-U")
MY_UID: str = os.getenv("UUID", str(uuid.uuid4()))
COT_DB_FILE: Optional[str] = os.getenv("COTDB")
COUNTRIES_DB_FILE: Optional[str] = os.getenv("COUNTRIESDB")
LOG_UNK: bool = os.getenv("LOGUNK", "false").lower() == "true"


def load_json_db(file_path: Optional[str]) -> Any:
    """
    Load JSON database from file path.

    Args:
        file_path: Path to the JSON file.

    Returns:
        The parsed JSON data or None if file doesn't exist or is invalid.
    """
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    return None


COT_DB: Optional[Dict[str, Any]] = load_json_db(COT_DB_FILE)
COUNTRIES_DB: Optional[List[Dict[str, Any]]] = load_json_db(COUNTRIES_DB_FILE)


def get_affil(hexid: str) -> Dict[str, Any]:
    """
    Get affiliation and country from hex ID.

    Args:
        hexid: The hex ID of the aircraft.

    Returns:
        A dictionary containing affiliation information.
    """
    affil = {"start": None, "stop": None, "affil": "u", "country": "unknown"}
    hexid_upper = hexid.upper()
    if COUNTRIES_DB is not None:
        for entry in COUNTRIES_DB:
            start = entry.get("start")
            end = entry.get("end")
            if start and end and start <= hexid_upper <= end:
                return entry
    return affil


def get_type(ac_category: str) -> str:
    """
    Get CoT type suffix based on aircraft category.

    Args:
        ac_category: The aircraft category string.

    Returns:
        The CoT type suffix.
    """
    mapping = {
        "A6": "-F-F",
        "A7": "-H",
        "B1": "-F",
        "B2": "-L",
        "B4": "-F",
        "B6": "-F-Q",
    }
    if ac_category in mapping:
        return mapping[ac_category]

    if ac_category.startswith("A"):
        return "-F"
    return ""


def get_cot(item: Dict[str, Any]) -> List[Union[str, bool]]:
    """
    Get CoT data for an aircraft item.

    Args:
        item: The ADSB item dictionary.

    Returns:
        A list containing [cottype, reg, model, country, (optional) icontype].
    """
    hexid = item.get("hex", "").lower()
    if COT_DB is not None:
        if hexid in COT_DB:
            return list(COT_DB[hexid])

        affil = get_affil(hexid)
        ac_category = str(item.get("category", ""))
        ac_type_suffix = get_type(ac_category) if ac_category else ""
        model = item.get("t", "unknown")
        reg = item.get("r", item.get("hex", "unknown"))

        cm = "C"
        if "dbFlags" in item:
            try:
                if (int(item["dbFlags"]) & 1) == 1:
                    cm = "M"
            except (ValueError, TypeError):
                pass

        cot_type = f"a-{affil['affil']}-A-{cm}{ac_type_suffix}"
        cot_data: List[Union[str, bool]] = [
            cot_type,
            str(reg),
            str(model),
            str(affil["country"]),
        ]

        if LOG_UNK:
            print(f'"{hexid}","COT","{reg}","{model}","{affil["country"]}"')
        return cot_data

    return ["a-u-A", False, False, False]


def get_icon_info(
    cot_type: str, operator: str, icon_type: Optional[str]
) -> Dict[str, Any]:
    """
    Get milsym and usericon information based on CoT type, operator, and icon type.

    Args:
        cot_type: The CoT type string.
        operator: The operator name.
        icon_type: The icon type string.

    Returns:
        A dictionary containing milsym and usericon details.
    """
    info: Dict[str, Any] = {}
    if not icon_type:
        return info

    icon_set_path = ""
    if "#LEO" in operator:
        info["__milsym"] = {"_attributes": {"id": "SUGP-----------"}}
        leo_icons = {
            "LE_ROTOR": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/" "Public Safety Air/LE_ROTOR.png"
            ),
            "LE_FIXED_WING": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/LE_FIXED_WING.png"
            ),
            "LE_FIXED_WING_ISR": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/LE_FIXED_WING_ISR.png"
            ),
            "LE_ROTOR_RESCUE": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/LE_ROTOR_RESCUE.png"
            ),
            "LE_UAS": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/" "Public Safety Air/LE_UAS.png"
            ),
        }
        icon_set_path = leo_icons.get(icon_type, "")

    if cot_type == "a-f-A-C-H":
        info["__milsym"] = {"_attributes": {"id": "SFAPCH---------"}}
        ems_rotor_icons = {
            "EMS_ROTOR": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/EMS_ROTOR.png"
            ),
            "EMS_ROTOR_RESCUE": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/EMS_ROTOR_RESCUE.png"
            ),
            "FIRE_ROTOR": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/FIRE_ROTOR.png"
            ),
            "FIRE_ROTOR_AIR_ATTACK": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/FIRE_ROTOR_AIR_ATTACK.png"
            ),
            "FIRE_ROTOR_INTEL": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/FIRE_ROTOR_INTEL.png"
            ),
            "FIRE_ROTOR_RESCUE": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/FIRE_ROTOR_RESCUE.png"
            ),
        }
        if not icon_set_path:
            icon_set_path = ems_rotor_icons.get(icon_type, "")

    if cot_type == "a-f-A-C-F":
        info["__milsym"] = {"_attributes": {"id": "SFAPCF---------"}}
        fire_icons = {
            "EMS_FIXED_WING": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/EMS_FIXED_WING.png"
            ),
            "FIRE_AIR_ATTACK": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/FIRE_AIR_ATTACK.png"
            ),
            "FIRE_AIR_TANKER": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/FIRE_AIR_TANKER.png"
            ),
            "FIRE_INTEL": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/FIRE_INTEL.png"
            ),
            "FIRE_LEAD_PLANE": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/FIRE_LEAD_PLANE.png"
            ),
            "FIRE_MULTI_USE": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/FIRE_MULTI_USE.png"
            ),
            "FIRE_SEAT": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/FIRE_SEAT.png"
            ),
            "FIRE_SMOKE_JMPR": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/"
                "Public Safety Air/FIRE_SMOKE_JMPR.png"
            ),
            "FIRE_UAS": (
                "66f14976-4b62-4023-8edb-d8d2ebeaa336/" "Public Safety Air/FIRE_UAS.png"
            ),
        }
        if not icon_set_path:
            icon_set_path = fire_icons.get(icon_type, "")

    if icon_set_path:
        info["usericon"] = {"_attributes": {"iconsetpath": icon_set_path}}

    return info
