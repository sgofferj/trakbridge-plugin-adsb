# Flow
- Fetch data from adsb.fi and compatible APIs
- Check if ICAO hex is in TAK-ADSB-ID
- If yes, use CoT from TAK-ADSB-ID
- If not, create CoT based on country DB and ADSB aircraft data

# Config fields
- URL
- API key
==> if API key is set, add appropriate authorization header
- Path to country DB
- Path to TAK-ADSB-ID
- Buttons to download both

# Example CoT
```xml
<event version="2.0" uid="ICAO-4a35cf" type="a-f-A-C-H" how="m-g" time="2025-11-03T08:26:30Z" start="2025-11-03T08:26:30.075Z" stale="2025-11-03T08:27:30.075Z">
  <point lat="45.685062" lon="25.897385" hae="808" ce="999999" le="999999"/>
  <detail>
    <contact callsign="336"/>
    <precisionlocation altsrc="GPS" geopointsrc="GPS"/>
    <link uid="adsb-one-feeder" production_time="2025-11-03T08:26:30.075Z" type="a-f-G-U" parent_callsign="adsb.one" relation="p-p"/>
    <track course="110.8" speed="52.987732"/>
    <remarks>ID: 4a35cf, Squawk: 6712, Type: EC135, Reg: 336, ROU SMURD #EMS #ADSB</remarks>
    <__milsym id="SFAPCH---------"/>
    <usericon iconsetpath="66f14976-4b62-4023-8edb-d8d2ebeaa336/Public Safety Air/EMS_ROTOR_RESCUE.png"/>
  </detail>
</event>
```
# Notes
- `<detail><__milsym/></detail>` and `<detail><usericon/></detail>` need to be added to trakbridge