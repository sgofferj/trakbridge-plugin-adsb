# tests/test_adsb.py from https://github.com/sgofferj/trakbridge-plugin-adsb.git
#
# Copyright Stefan Gofferje
#
# Licensed under the Gnu General Public License Version 3 or higher (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.gnu.org/licenses/gpl-3.0.en.html

from plugin.adsb import get_type, get_affil


def test_get_type():
    assert get_type("A6") == "-F-F"
    assert get_type("A7") == "-H"
    assert get_type("B1") == "-F"
    assert get_type("UNKNOWN") == ""


def test_get_affil():
    countries_db = [
        {"start": "3C0000", "end": "3C3FFF", "affil": "f", "country": "Germany"},
        {"start": "440000", "end": "447FFF", "affil": "f", "country": "Austria"},
    ]

    # Test match
    result = get_affil("3C0001", countries_db)
    assert result["country"] == "Germany"
    assert result["affil"] == "f"

    # Test no match
    result = get_affil("FFFFFF", countries_db)
    assert result["country"] == "unknown"
    assert result["affil"] == "u"

    # Test empty DB
    result = get_affil("3C0001", [])
    assert result["country"] == "unknown"
