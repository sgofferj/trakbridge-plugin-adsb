# trakbridge-plugin-adsb

ADSB Plugin for [TrakBridge](https://github.com/emfoursolutions/trakbridge).

&copy; 2026 Stefan Gofferje

> [!CAUTION]
> This is currently being worked on. It's only on Github for collaboration and test purposes.
> No guarantees, no support.

## Description

The ADSB Plugin for TrakBridge enables the integration of live aircraft tracking data into Team Awareness Kit (TAK) environments. It polls data from ADSB aggregators using the ADSB-Exchange V2 API (and compatible ones like [adsb.fi](https://adsb.fi)) and transforms it into Cursor-on-Target (CoT) messages.

## Features

- **ADSB-Exchange V2 API Compatibility:** Works with various aggregators and local feeders providing V2 JSON data.
- **Rich CoT Transformation:** Converts raw ADSB data into standardized CoT types with MIL-STD-2525 symbology.
- **Smart Affiliation Mapping:** Automatically determines aircraft affiliation (Friend/Hostile/Unknown) based on ICAO hex ranges.
- **Specialized Iconography:** Custom icon support for:
  - Law Enforcement (LEO) aircraft.
  - Emergency Medical Services (EMS) and Fire rotor/fixed-wing aircraft.
- **Custom Databases:** Supports external JSON databases for fine-grained control over CoT types and affiliation.
- **Rate Limiting:** Implements cross-worker rate limit synchronization to prevent API over-usage.
- **Filtering:** Built-in support for filtering by range, ICAO hex, callsign, registration, or squawk via standard API endpoints.

## Configuration

The plugin is configured within the TrakBridge interface. Key configuration fields include:

| Field | Type | Description |
| :--- | :--- | :--- |
| `api_key` | password | API key for the selected aggregator (if required). |
| `url_select` | select | Pre-configured standard API endpoints (e.g., adsb.fi filters). |
| `url_opt` | text | Optional value for filters (e.g., specific hex, squawk, or callsign). |
| `server_url` | url | Custom Tracker API URL if not using a preset. |
| `cot_db_path` | filepath | Path to a `TAK-ADSB-ID` JSON file for custom CoT mappings. |
| `countries_db_path` | filepath | Path to a Countries DB JSON file for affiliation mapping. |
| `log_unknown` | boolean | If enabled, unknown aircraft details are logged to the console. |

## Installation

This plugin is designed to be used within a TrakBridge installation.

1. Ensure TrakBridge is installed and running.
2. Place the `plugin/` directory of this repository into your TrakBridge plugins folder.
3. Install dependencies using Poetry:
   ```bash
   poetry install
   ```
4. Restart TrakBridge and configure the plugin via the dashboard.

## Development

The project uses Poetry for dependency management and follows strict quality standards:
- **Formatting:** Black
- **Type Checking:** MyPy (Strict)
- **Linting:** PyLint
- **Testing:** PyTest with asynchronous support

To run quality checks:
```bash
poetry run black .
poetry run mypy plugin
poetry run pylint plugin/ tests/
poetry run pytest
```

## License

This project is licensed under the GNU General Public License Version 3 or higher. See the `LICENSE` file for details.
