"""
ADSB Plugin for TrakBridge
"""

import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import aiohttp
from plugins.base_plugin import BaseGPSPlugin, PluginConfigField
from plugin.functions import get_cot, get_icon_info, MY_UID, MY_TYPE, MY_CALLSIGN


class ADSBPlugin(BaseGPSPlugin):  # type: ignore
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
            "config_fields": [
                PluginConfigField(
                    name="api_key",
                    label="API Key",
                    field_type="password",
                    required=False,
                    sensitive=True,
                    help_text="API key if required",
                ),
                PluginConfigField(
                    name="server_url",
                    label="API URL",
                    field_type="url",
                    required=True,
                    placeholder="https://api.mycustomtracker.com",
                    help_text="ADSB aggregator API URL",
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
                    default=False,
                    help_text="Log details of unknown aircraft to console.",
                ),
            ],
            "help_sections": [
                {
                    "title": "Overview",
                    "content": [
                        "This plugin polls aircraft ADSB data from any source which offers the ADSB-Exchange V2 API.",
                        "Connections with and without API keys are supported. Please be aware of the rate limits of your",
                        "data source and respect them. Ignoring rate limits will probably get you banned.",
                    ],
                }
            ],
        }

    async def fetch_locations(
        self, session: aiohttp.ClientSession
    ) -> List[Dict[str, Any]]:
        """Fetch locations from the ADSB API"""
        config = self.get_decrypted_config()

        # Set environment variables for functions.py
        original_cot_db_file = os.getenv("COTDB")
        original_countries_db_file = os.getenv("COUNTRIESDB")
        original_log_unk = os.getenv("LOGUNK")

        if config.get("cot_db_path"):
            os.environ["COTDB"] = config["cot_db_path"]
        if config.get("countries_db_path"):
            os.environ["COUNTRIESDB"] = config["countries_db_path"]
        os.environ["LOGUNK"] = str(config.get("log_unknown", False))

        try:
            headers = {
                "User-Agent": "TrakBridge ADSB plugin v0.1",
            }
            if config.get("api_key"):
                headers.update({"Authorization": f"Bearer: {config['api_key']}"})

            async with session.get(
                f"{config['server_url']}", headers=headers
            ) as response:
                if response.status != 200:
                    self.logger.error(f"API returned status {response.status}")
                    return []
                data = await response.json()
                return self._transform_locations(data)
        except aiohttp.ClientError as e:
            self.logger.error(f"Error fetching locations: {e}")
            return []
        finally:
            # Restore original environment variables
            if original_cot_db_file is None:
                os.environ.pop("COTDB", None)
            else:
                os.environ["COTDB"] = original_cot_db_file

            if original_countries_db_file is None:
                os.environ.pop("COUNTRIESDB", None)
            else:
                os.environ["COUNTRIESDB"] = original_countries_db_file

            if original_log_unk is None:
                os.environ.pop("LOGUNK", None)
            else:
                os.environ["LOGUNK"] = original_log_unk

    def _transform_locations(self, api_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform API data to TrakBridge format"""
        locations = []
        now = datetime.now(timezone.utc)
        dt_d = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        dt_ds = (now + timedelta(seconds=60)).strftime("%Y-%m-%dT%H:%M:%S.%f")[
            :-3
        ] + "Z"

        for item in api_data.get("aircraft", []):
            has_lat = "lat" in item or "rr_lat" in item
            has_lon = "lon" in item or "rr_lon" in item
            has_alt = "alt_geom" in item or "alt_baro" in item

            if not (has_lat and has_lon and has_alt):
                continue

            hex_id = item.get("hex", "unknown")
            lat = item.get("lat", item.get("rr_lat"))
            lon = item.get("lon", item.get("rr_lon"))

            cot_data = get_cot(item)

            operator = str(cot_data[3]) if len(cot_data) > 3 else "unknown"
            actype = str(cot_data[2]) if len(cot_data) > 2 else item.get("t", "unknown")
            reg = str(cot_data[1]) if len(cot_data) > 1 else "unknown"
            cott = str(cot_data[0])

            alt_val = item.get("alt_geom", item.get("alt_baro", 0))
            try:
                alt = round(float(alt_val) * 0.3048)
            except (ValueError, TypeError):
                alt = 0

            course = item.get("track", 0)
            speed = float(item.get("gs", 0)) * 0.514444
            squawk = item.get("squawk", "----")

            if item.get("flight") is None:
                callsign = reg if reg != "unknown" else f"ICAO-{hex_id.lower()}"
            else:
                callsign = str(item["flight"]).strip()

            remarks = (
                f"ID: {hex_id}, Squawk: {squawk}\n"
                f"Type: {actype}, Reg: {reg}\n"
                f"{operator} #ADSB"
            )
            uid = f"ICAO-{hex_id.lower()}"

            detail = {
                "contact": {"_attributes": {"callsign": callsign}},
                "precisionlocation": {
                    "_attributes": {"altsrc": "GPS", "geopointsrc": "GPS"}
                },
                "link": {
                    "_attributes": {
                        "uid": MY_UID,
                        "production_time": dt_d,
                        "type": MY_TYPE,
                        "parent_callsign": MY_CALLSIGN,
                        "relation": "p-p",
                    }
                },
                "track": {"_attributes": {"course": str(course), "speed": str(speed)}},
                "remarks": remarks,
            }

            icon_type = str(cot_data[4]) if len(cot_data) > 4 else None
            icon_info = get_icon_info(cott, operator, icon_type)
            detail.update(icon_info)

            location_dict = {
                "uid": uid,
                "type": cott,
                "how": "m-g",
                "time": dt_d,
                "start": dt_d,
                "stale": dt_ds,
                "point": {
                    "lat": str(lat),
                    "lon": str(lon),
                    "hae": str(alt),
                    "ce": str(item.get("nac_p", 999999)),
                    "le": str(item.get("nac_v", 999999)),
                },
                "detail": detail,
                "lat": lat,
                "lon": lon,
                "name": callsign,
                "timestamp": dt_d,
            }
            locations.append(location_dict)

        return locations
