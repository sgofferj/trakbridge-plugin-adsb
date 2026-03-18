# update_version.py
import toml
import re
import os
import sys

def update_version_in_adsb_plugin():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pyproject_path = os.path.join(script_dir, "pyproject.toml")
    adsb_plugin_path = os.path.join(script_dir, "plugin", "adsb.py")

    # Read version from pyproject.toml
    try:
        with open(pyproject_path, "r") as f:
            pyproject_content = toml.load(f)
            version = pyproject_content["project"]["version"]
    except FileNotFoundError:
        print(f"Error: {pyproject_path} not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {pyproject_path}: {e}")
        sys.exit(1)

    # Read adsb.py content
    try:
        with open(adsb_plugin_path, "r") as f:
            adsb_content = f.read()
    except FileNotFoundError:
        print(f"Error: {adsb_plugin_path} not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {adsb_plugin_path}: {e}")
        sys.exit(1)

    # Define the regex pattern for the User-Agent line
    # It looks for "User-Agent": "TrakBridge ADSB plugin vX.Y.Z", where X.Y.Z can be any version
    user_agent_pattern = r'("User-Agent": "TrakBridge ADSB plugin v)\d+\.\d+\.\d+"'
    replacement_string = rf'\1{version}"'

    # Check if the User-Agent line exists
    if not re.search(user_agent_pattern, adsb_content):
        print(f"Warning: User-Agent line not found in {adsb_plugin_path}. Please add a line like '"User-Agent": "TrakBridge ADSB plugin vX.Y.Z"' for automation.")
        sys.exit(0) # Exit with 0 as it's not a critical error if line doesn't exist yet

    # Update User-Agent string
    new_adsb_content = re.sub(
        user_agent_pattern,
        replacement_string,
        adsb_content,
        count=1,
    )

    if new_adsb_content != adsb_content:
        try:
            with open(adsb_plugin_path, "w") as f:
                f.write(new_adsb_content)
            print(f"Updated plugin/adsb.py User-Agent to v{version}")
        except Exception as e:
            print(f"Error writing to {adsb_plugin_path}: {e}")
            sys.exit(1)
    else:
        print(f"plugin/adsb.py User-Agent is already v{version}")

if __name__ == "__main__":
    update_version_in_adsb_plugin()
