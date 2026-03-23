# adsb.py from https://github.com/sgofferj/trakbridge-plugin-adsb.git
#
# Copyright Stefan Gofferje
#
# Licensed under the Gnu General Public License Version 3 or higher (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.gnu.org/licenses/gpl-3.0.en.html

"""
ADSB Plugin for TrakBridge
"""

import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, cast

import aiohttp
from plugins.base_plugin import (
    BaseGPSPlugin,
    CallsignMappable,
    FieldMetadata,
    PluginConfigField,
)
from services.logging_service import get_module_logger

# Initialize module logger
logger = get_module_logger(__name__)


# Functions from functions.py
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


def get_affil(
    hexid: str, countries_db: Optional[List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Get affiliation and country from hex ID.

    Args:
        hexid: The hex ID of the aircraft.
        countries_db: The countries database.

    Returns:
        A dictionary containing affiliation information.
    """
    affil = {"start": None, "stop": None, "affil": "u", "country": "unknown"}
    hexid_upper = hexid.upper()
    if countries_db is not None:
        for entry in countries_db:
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


def get_cot_details(
    item: Dict[str, Any],
    cot_db: Optional[Dict[str, Any]],
    countries_db: Optional[List[Dict[str, Any]]],
    log_unknown: bool,
) -> Dict[str, Any]:
    """
    Get detailed CoT data for an aircraft item.

    Args:
        item: The ADSB item dictionary.
        cot_db: The CoT database.
        countries_db: The countries database.
        log_unknown: Whether to log unknown aircraft.

    Returns:
        A dictionary containing [cot_type, reg, model, operator, country, icon_type].
    """
    hexid = item.get("hex", "").lower()

    # Always check country affiliation for consistent display
    affil_info = get_affil(hexid, countries_db)

    # 1. Try to find in custom CoT DB
    if cot_db is not None and hexid in cot_db:
        entry = cot_db[hexid]
        # Format: [cot_type, reg, model, operator, icon_type]
        return {
            "cot_type": str(entry[0]),
            "reg": str(entry[1]),
            "model": str(entry[2]),
            "operator": str(entry[3]),
            "icon_type": str(entry[4]) if len(entry) > 4 else None,
            "country": affil_info["country"],
        }

    # 2. Fallback to general logic
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

    cot_type = f"a-{affil_info['affil']}-A-{cm}{ac_type_suffix}"

    if log_unknown:
        print(
            f'"{hexid}","COT","{reg}","{model}","{affil_info["affil"]}","{affil_info["country"]}"'
        )

    return {
        "cot_type": cot_type,
        "reg": str(reg),
        "model": str(model),
        "operator": "",  # Set operator to empty string if not found in cot_db
        "icon_type": None,
        "country": affil_info["country"],
    }


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
    icon_set_path = ""

    if "#LEO" in operator:
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
        if icon_type and icon_type in leo_icons:
            icon_set_path = leo_icons[icon_type]
            info["__milsym"] = {"_attributes": {"id": "SUGP-----------"}}

    # Match EMS/Fire regardless of affiliation (f, h, or u) if type suffix matches
    if "-A-C-H" in cot_type:
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
        if icon_type and not icon_set_path and icon_type in ems_rotor_icons:
            icon_set_path = ems_rotor_icons[icon_type]
            info["__milsym"] = {"_attributes": {"id": "SFAPCH---------"}}

    if "-A-C-F" in cot_type:
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
        if icon_type and not icon_set_path and icon_type in fire_icons:
            icon_set_path = fire_icons[icon_type]
            info["__milsym"] = {"_attributes": {"id": "SFAPCF---------"}}

    if icon_set_path:
        info["usericon"] = {"_attributes": {"iconsetpath": icon_set_path}}

    return info


class ADSBPlugin(BaseGPSPlugin, CallsignMappable):  # type: ignore
    """ADSB integration"""

    PLUGIN_NAME = "adsb"

    @classmethod
    def get_plugin_name(cls) -> str:
        return cls.PLUGIN_NAME

    @property
    def plugin_name(self) -> str:
        return self.PLUGIN_NAME

    @property
    def plugin_metadata(self) -> Dict[str, Any]:
        return {
            "display_name": "ADSB Plugin",
            "description": "Get aircraft data from ADSB aggregators",
            "icon": "fas fa-plane",
            "category": "custom",
            "min_poll_interval": 5,
            "hide_cot_type": True,
            "config_fields": [
                PluginConfigField(
                    name="lat",
                    label="Latitude",
                    field_type="text",
                    required=False,
                    default_value=0,
                    help_text="Your latitude for use in standard API calls",
                ),
                PluginConfigField(
                    name="lon",
                    label="Longitude",
                    field_type="text",
                    required=False,
                    default_value=0,
                    help_text="Your longitude for use in standard API calls",
                ),
                PluginConfigField(
                    name="range",
                    label="Range(nm)",
                    field_type="text",
                    required=False,
                    default_value=0,
                    help_text="The desired display range for standard API calls",
                ),
                PluginConfigField(
                    name="api_key",
                    label="API Key",
                    field_type="password",
                    required=False,
                    sensitive=True,
                    help_text="API key if required by the tracker API",
                ),
                PluginConfigField(
                    name="url_select",
                    label="Standard APIs",
                    field_type="select",
                    required=True,
                    options=[
                        {
                            "value": "https://opendata.adsb.fi/api/v3/lat/_LAT_/lon/_LON_/dist/_RANGE_",
                            "label": "adsb.fi - Range around location",
                        },
                        {
                            "value": "https://opendata.adsb.fi/api/v2/hex/_URL_OPT_",
                            "label": "adsb.fi - ICAO Hex ID filter (fill desired id in Optional value)",
                        },
                        {
                            "value": "https://opendata.adsb.fi/api/v2/callsign/_URL_OPT_",
                            "label": "adsb.fi - Callsign filter (fill desired callsign in Optional value)",
                        },
                        {
                            "value": "https://opendata.adsb.fi/api/v2/registration/_URL_OPT_",
                            "label": "adsb.fi - Registration filter (fill desired registration in Optional value)",
                        },
                        {
                            "value": "https://opendata.adsb.fi/api/v2/sqk/_URL_OPT_",
                            "label": "adsb.fi - Squawk filter (fill desired squawk in Optional value)",
                        },
                        {
                            "value": "https://opendata.adsb.fi/api/v2/mil",
                            "label": "adsb.fi - Military aircraft filter",
                        },
                        {
                            "value": "_CUSTOM_",
                            "label": "Custom URL, enter below",
                        },
                    ],
                    help_text="Some commonly used aggregator APIs. Some require an API key to work",
                ),
                PluginConfigField(
                    name="url_opt",
                    label="Optional value",
                    field_type="text",
                    required=False,
                    placeholder="7700",
                    help_text="Optional value, e.g. for hex/icao or squawk endpoints",
                ),
                PluginConfigField(
                    name="server_url",
                    label="Tracker API URL",
                    field_type="url",
                    required=False,
                    placeholder="https://adsb.example.com/api/v2/aircraft",
                    help_text="Tracker API URL (ADSB-Exchange V2 compatible)",
                ),
                PluginConfigField(
                    name="cot_db_path",
                    label="Path to TAK-ADSB-ID JSON",
                    field_type="filepath",
                    required=False,
                    help_text="File containing known CoT details for ICAO hex IDs.",
                ),
                PluginConfigField(
                    name="countries_db_path",
                    label="Path to Countries DB JSON",
                    field_type="filepath",
                    required=False,
                    help_text="File containing country-based affiliation ranges for ICAO hex IDs.",
                ),
                PluginConfigField(
                    name="log_unknown",
                    label="Log unknown aircraft",
                    field_type="boolean",
                    required=False,
                    default_value=False,
                    help_text="Log details of unknown aircraft to console.",
                ),
            ],
            "help_sections": [
                {
                    "title": "Overview",
                    "content": [
                        "This plugin polls aircraft data from an ADSB-Exchange V2 compatible API.",
                        "It transforms the data into CoT format for use in TAK.",
                    ],
                }
            ],
        }

    def _get_api_url(self, config: Dict[str, Any]) -> Optional[str]:
        """Get the API URL based on plugin configuration."""
        url_select = cast(Optional[str], config.get("url_select"))

        if not url_select:
            logger.error("`url_select` is not configured.")
            return None

        if url_select == "_CUSTOM_":
            server_url = cast(str, config.get("server_url", "")).strip()
            if not server_url:
                logger.error(
                    "`url_select` is '_CUSTOM_' but 'Tracker API URL' is not set."
                )
                return None
            return server_url

        url = url_select

        # Map placeholders to their corresponding config field names and display labels
        placeholders = {
            "_LAT_": ("lat", "Latitude"),
            "_LON_": ("lon", "Longitude"),
            "_RANGE_": ("range", "Range"),
            "_URL_OPT_": ("url_opt", "Optional value"),
        }

        for placeholder, (field_name, label) in placeholders.items():
            if placeholder in url:
                value = config.get(field_name)
                # url_opt should not be empty, others just need to be not None
                if value is None or (placeholder == "_URL_OPT_" and not str(value)):
                    logger.error(
                        f"URL requires `{placeholder}` but `{label}` is not configured."
                    )
                    return None
                url = url.replace(placeholder, str(value))

        return url

    async def fetch_locations(
        self, session: aiohttp.ClientSession
    ) -> List[Dict[str, Any]]:
        """Fetch locations from the ADSB API"""
        config = self.get_decrypted_config()
        api_url = self._get_api_url(config)
        if not api_url:
            logger.error("Could not determine API URL due to configuration issues.")
            return [
                {
                    "_error": "configuration",
                    "_error_message": "Could not determine API URL. Please check plugin configuration.",
                }
            ]

        try:
            headers = {
                "User-Agent": "TrakBridge ADSB plugin vX.Y.Z",
            }
            if config.get("api_key"):
                headers.update({"Authorization": f"Bearer {config['api_key']}"})

            async with session.get(api_url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"API returned status {response.status}")
                    return [
                        {
                            "_error": str(response.status),
                            "_error_message": f"API returned status {response.status}",
                        }
                    ]
                data = await response.json()
                return self._transform_api_data(data, config)
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching locations: {e}")
            return [
                {
                    "_error": "network",
                    "_error_message": f"Error fetching locations: {e}",
                }
            ]

    def get_available_fields(self) -> List[FieldMetadata]:
        """
        No callsign mapping fields are available for this plugin.
        """
        return []

    def apply_callsign_mapping(
        self,
        tracker_data: List[Dict[str, Any]],
        field_name: str,
        callsign_map: Dict[str, str],
    ) -> None:
        """
        This plugin does not support callsign mapping.
        """

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to the ADSB API.
        """
        config = self.get_decrypted_config()
        api_url = self._get_api_url(config)
        if not api_url:
            return {
                "success": False,
                "error": "Configuration Error",
                "message": "ADSB API URL is not configured correctly. Please check plugin settings.",
            }
        headers = {
            "User-Agent": "TrakBridge ADSB plugin v0.2",
        }
        if config.get("api_key"):
            headers.update({"Authorization": f"Bearer {config['api_key']}"})

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status == 200:
                        return {
                            "success": True,
                            "message": "Successfully connected to ADSB API.",
                        }
                    return {
                        "success": False,
                        "message": f"API returned status {response.status}",
                    }
        except aiohttp.ClientError as e:
            return {"success": False, "message": f"Error connecting to API: {e}"}

    def validate_config(self) -> bool:
        """
        Validate the plugin configuration.
        """
        if not super().validate_config():
            return False

        config = self.get_decrypted_config()
        url_select = cast(Optional[str], config.get("url_select"))

        if url_select and "_URL_OPT_" in url_select:
            if not config.get("url_opt"):
                logger.error(
                    "`url_select` contains `_URL_OPT_` but `url_opt` is not set."
                )
                return False

        return self._get_api_url(config) is not None

    def _transform_api_data(
        self, api_data: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Transform API data to TrakBridge format"""
        locations = []
        now = datetime.now(timezone.utc)
        dt_d = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        cot_db = load_json_db(config.get("cot_db_path"))
        countries_db = load_json_db(config.get("countries_db_path"))
        log_unknown = config.get("log_unknown", False)

        # ADSB-Exchange v2 uses 'ac' key, while older versions use 'aircraft'
        aircraft_list = api_data.get("ac", api_data.get("aircraft", []))

        for item in aircraft_list:
            has_lat = "lat" in item
            has_lon = "lon" in item
            # Fallback for altitude keys
            alt_val = item.get("alt_geom", item.get("alt_baro", item.get("alt")))

            if not (has_lat and has_lon and alt_val is not None):
                continue

            hex_id = item.get("hex", "unknown")
            lat = item.get("lat")
            lon = item.get("lon")

            cot_details = get_cot_details(item, cot_db, countries_db, log_unknown)

            operator = cot_details["operator"]
            actype = cot_details["model"]
            reg = cot_details["reg"]
            cott = cot_details["cot_type"]
            icon_type = cot_details["icon_type"]
            country = cot_details["country"]

            try:
                # Some feeds might have 'ground' for altitude
                if alt_val == "ground":
                    alt = 0
                else:
                    alt = round(float(alt_val) * 0.3048)  # Convert feet to meters
            except (ValueError, TypeError):
                alt = 0

            course = item.get("track", item.get("mag_heading", 0))
            speed = (
                float(item.get("gs", item.get("ias", 0))) * 0.514444
            )  # Convert knots to m/s
            squawk = item.get("squawk", "----")

            if item.get("flight") is None:
                callsign = reg if reg != "unknown" else f"ICAO-{hex_id.lower()}"
            else:
                callsign = str(item["flight"]).strip()

            remarks_parts = [
                f"ID: {hex_id}, Squawk: {squawk}",
                f"Type: {actype}, Reg: {reg}",
            ]
            if country and country != "unknown":
                remarks_parts.append(f"Country: {country}")

            # Removed the debug line for CoT type
            # remarks_parts.append(f"CoT: {cott}")

            if operator:  # Only append operator if it's not empty
                remarks_parts.append(f"{operator} #ADSB")
            else:
                remarks_parts.append("#ADSB")

            remarks = "\n".join(remarks_parts)
            uid = f"ICAO-{hex_id.lower()}"

            icon_info = get_icon_info(cott, operator, icon_type)

            location_dict = {
                "uid": uid,
                "cot_type": cott,
                "lat": lat,
                "lon": lon,
                "hae": alt,
                "ce": str(item.get("nac_p", 999999)),
                "le": str(item.get("nac_v", 999999)),
                "name": callsign,
                "timestamp": dt_d,
                "speed": speed,
                "course": course,
                "description": remarks,
                "custom_cot_attrib": {"detail": icon_info},
            }
            locations.append(location_dict)

        return locations
