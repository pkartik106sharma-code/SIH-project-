import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import serial
import serial.tools.list_ports
import requests
import urllib3.util.connection as urllib3_cn

# Force IPv4 socket resolution to prevent Windows DNS socket errors
urllib3_cn.allowed_gai_family = lambda: urllib3_cn.socket.AF_INET

st.set_page_config(page_title="PRAVAH - Flash Flood & Landslide Warning System", layout="wide")

# ----------------- LIVE WEATHER INGESTION FUNCTION -----------------
@st.cache_data(ttl=600)
def get_live_weather(lat, lon, api_key):
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            rain_val = 0.0
            if "rain" in data:
                rain_val = data["rain"].get("1h", data["rain"].get("3h", 0.0))
            temp_val = data.get("main", {}).get("temp", 15.0)
            return float(rain_val), float(temp_val), True
    except Exception:
        pass
    return 0.0, 15.0, False

# ----------------- 30-VILLAGE SLOPE & MORPHOMETRIC DATASET -----------------
VILLAGE_DATABASE = [
    {"id": 1, "name": "Palchan", "sub_district": "Manali", "lat": 32.2967, "lon": 77.2050, "slope": 31.8, "aspect": "NE", "stream": "Solang / Beas", "dist_stream_m": 80},
    {"id": 2, "name": "UP Muhal Solang", "sub_district": "Manali", "lat": 32.3126, "lon": 77.1603, "slope": 28.6, "aspect": "E", "stream": "Solang Nullah", "dist_stream_m": 120},
    {"id": 3, "name": "Bashisht", "sub_district": "Manali", "lat": 32.3120, "lon": 77.1770, "slope": 25.8, "aspect": "S", "stream": "Beas Upper", "dist_stream_m": 150},
    {"id": 4, "name": "Muhal Manali", "sub_district": "Manali", "lat": 32.2390, "lon": 77.1880, "slope": 16.2, "aspect": "E", "stream": "Manalsu Khad", "dist_stream_m": 110},
    {"id": 5, "name": "Fojal", "sub_district": "Manali", "lat": 32.1480, "lon": 77.1500, "slope": 35.6, "aspect": "SW", "stream": "Fojal Khad", "dist_stream_m": 90},
    {"id": 6, "name": "Bandrol", "sub_district": "Kullu", "lat": 32.1150, "lon": 77.1350, "slope": 27.4, "aspect": "SE", "stream": "Beas Trunk", "dist_stream_m": 70},
    {"id": 7, "name": "Mapak", "sub_district": "Kullu", "lat": 32.1300, "lon": 77.1450, "slope": 34.7, "aspect": "E", "stream": "Side Gully", "dist_stream_m": 160},
    {"id": 8, "name": "Nangabag", "sub_district": "Kullu", "lat": 32.1230, "lon": 77.1510, "slope": 41.2, "aspect": "S", "stream": "Beas Escarpment", "dist_stream_m": 130},
    {"id": 9, "name": "Harabag", "sub_district": "Kullu", "lat": 32.1190, "lon": 77.1580, "slope": 29.5, "aspect": "SW", "stream": "Khad Confluence", "dist_stream_m": 140},
    {"id": 10, "name": "Bagu Nalha", "sub_district": "Kullu", "lat": 32.1080, "lon": 77.1620, "slope": 38.1, "aspect": "W", "stream": "Bagu Nullah", "dist_stream_m": 60},
    {"id": 11, "name": "Bajaura", "sub_district": "Kullu", "lat": 31.9310, "lon": 77.1260, "slope": 22.6, "aspect": "NW", "stream": "Beas Floodplain", "dist_stream_m": 95},
    {"id": 12, "name": "Malana", "sub_district": "Kullu", "lat": 32.0710, "lon": 77.3210, "slope": 45.8, "aspect": "NE", "stream": "Malana Nullah", "dist_stream_m": 50},
    {"id": 13, "name": "Manikarn", "sub_district": "Kullu", "lat": 32.0140, "lon": 77.3380, "slope": 33.9, "aspect": "E", "stream": "Parbati River", "dist_stream_m": 40},
    {"id": 14, "name": "Jari", "sub_district": "Kullu", "lat": 32.0200, "lon": 77.3500, "slope": 26.7, "aspect": "SE", "stream": "Parbati Gorge", "dist_stream_m": 100},
    {"id": 15, "name": "Kotla", "sub_district": "Banjar", "lat": 31.6410, "lon": 77.3820, "slope": 32.4, "aspect": "S", "stream": "Tirthan Khad", "dist_stream_m": 75},
    {"id": 16, "name": "Chakurtha", "sub_district": "Banjar", "lat": 31.6480, "lon": 77.3900, "slope": 37.6, "aspect": "SW", "stream": "Tirthan River", "dist_stream_m": 120},
    {"id": 17, "name": "Kanon", "sub_district": "Banjar", "lat": 31.6550, "lon": 77.3980, "slope": 29.8, "aspect": "W", "stream": "Jibhi Stream", "dist_stream_m": 85},
    {"id": 18, "name": "Shanshar", "sub_district": "Banjar", "lat": 31.7100, "lon": 77.3500, "slope": 43.5, "aspect": "NW", "stream": "Sainj Headwaters", "dist_stream_m": 55},
    {"id": 19, "name": "Shangarh", "sub_district": "Banjar", "lat": 31.4000, "lon": 77.3550, "slope": 25.4, "aspect": "N", "stream": "Sainj Feeder Nullah", "dist_stream_m": 180},
    {"id": 20, "name": "Chanon", "sub_district": "Banjar", "lat": 31.6200, "lon": 77.4100, "slope": 39.2, "aspect": "NE", "stream": "Gushaini Chute", "dist_stream_m": 90},
    {"id": 21, "name": "Bahu", "sub_district": "Banjar", "lat": 31.6700, "lon": 77.4300, "slope": 34.6, "aspect": "E", "stream": "Bahu Khad", "dist_stream_m": 115},
    {"id": 22, "name": "Karshaigad", "sub_district": "Anni", "lat": 31.4600, "lon": 77.4800, "slope": 41.8, "aspect": "SE", "stream": "Anni Khad Upper", "dist_stream_m": 65},
    {"id": 23, "name": "Bishla Dhar", "sub_district": "Anni", "lat": 31.4700, "lon": 77.4900, "slope": 36.5, "aspect": "S", "stream": "Kurpan Khad", "dist_stream_m": 140},
    {"id": 24, "name": "Khani", "sub_district": "Anni", "lat": 31.4850, "lon": 77.5050, "slope": 28.7, "aspect": "SW", "stream": "Anni Drainage", "dist_stream_m": 130},
    {"id": 25, "name": "Kungash", "sub_district": "Anni", "lat": 31.4450, "lon": 77.5200, "slope": 44.1, "aspect": "W", "stream": "Badhali Gorge", "dist_stream_m": 50},
    {"id": 26, "name": "Franali", "sub_district": "Anni", "lat": 31.4250, "lon": 77.5350, "slope": 31.6, "aspect": "NW", "stream": "Sutlej River tributary", "dist_stream_m": 110},
    {"id": 27, "name": "Chail", "sub_district": "Nirmand", "lat": 31.3300, "lon": 77.5100, "slope": 26.3, "aspect": "N", "stream": "Kurpan Tributary", "dist_stream_m": 160},
    {"id": 28, "name": "Sarahan", "sub_district": "Nirmand", "lat": 31.3350, "lon": 77.5250, "slope": 39.7, "aspect": "NE", "stream": "Nirmand Khad", "dist_stream_m": 85},
    {"id": 29, "name": "Jhaler", "sub_district": "Nirmand", "lat": 31.3450, "lon": 77.5350, "slope": 47.2, "aspect": "E", "stream": "Steep Escarpment Stream", "dist_stream_m": 45},
    {"id": 30, "name": "Nermand", "sub_district": "Nirmand", "lat": 31.4250, "lon": 77.5600, "slope": 35.9, "aspect": "SE", "stream": "Kurpan River", "dist_stream_m": 95}
]

# ----------------- 40-YEAR HP SDMA HISTORICAL REVIEW (1986-2026) -----------------
HISTORICAL_INCIDENTS = [
    {"year": 1988, "location": "Solang / Dhundi", "district": "Kullu", "lat": 32.3126, "lon": 77.1603, "impact": "15 houses washed away, NH-3 breach, fatalities", "trigger": "Cloudburst & Glacial Surge"},
    {"year": 1994, "location": "Manimahesh / Chamba-Bharmour", "district": "Chamba", "lat": 32.3950, "lon": 76.6200, "impact": "62 km road washed away, >50 deaths, 2000 stranded", "trigger": "Cloudburst / GLOF Surge"},
    {"year": 1995, "location": "Kullu Valley Trunk", "district": "Kullu", "lat": 31.9579, "lon": 77.1095, "impact": "Severe agricultural and horticultural losses along Beas", "trigger": "Prolonged Excessive Rainfall"},
    {"year": 1997, "location": "Kullu District Valleys", "district": "Kullu", "lat": 32.1150, "lon": 77.1350, "impact": "Widespread flash flood disaster, major casualties", "trigger": "High-intensity Cloudbursts"},
    {"year": 2001, "location": "Chhota Bhangal / Baijnath", "district": "Kangra", "lat": 32.0500, "lon": 76.6500, "impact": "12 deaths, livestock and bridges washed away", "trigger": "Khad Flash Flood"},
    {"year": 2001, "location": "Sainj Valley (Jeeba Nallah)", "district": "Kullu", "lat": 31.7800, "lon": 77.2900, "impact": "Catchment cloudburst destroyed farmlands & bridges", "trigger": "Cloudburst & Debris Dam"},
    {"year": 2001, "location": "Anni (Badhali / Sarli)", "district": "Kullu", "lat": 31.4600, "lon": 77.4800, "impact": "Houses, livestock, and farms washed into gorge", "trigger": "Torrential Slope Wash"},
    {"year": 2003, "location": "Gharsa / Kangni Nalla / Bahang", "district": "Kullu", "lat": 32.2200, "lon": 77.1950, "impact": "Fatalities, landslide damming, NH collapse", "trigger": "Flash Flood & Slope Breach"},
    {"year": 2005, "location": "Tirthan Khad", "district": "Mandi", "lat": 31.6410, "lon": 77.3820, "impact": "Riparian buildings washed away, road cutoff", "trigger": "Riverbed Overflow"},
    {"year": 2009, "location": "Dharampur & Higher Kangra", "district": "Mandi/Kangra", "lat": 31.8000, "lon": 76.8200, "impact": "Severe urban and bus depot flooding, casualties", "trigger": "Cloudburst Drainage Inundation"},
    {"year": 2015, "location": "Dharampur Bus Stand", "district": "Mandi", "lat": 31.8000, "lon": 76.8200, "impact": "Buses submerged, cowsheds and markets ruined", "trigger": "Khad Overflow"},
    {"year": 2023, "location": "Pandoh / Mandi / Beas System", "district": "Mandi", "lat": 31.7087, "lon": 76.9320, "impact": "Historic flooding, bridge sweeps, major road collapse", "trigger": "Extreme Multi-day Monsoon"},
    {"year": 2023, "location": "Beas-Parbati-Sainj System", "district": "Kullu", "lat": 31.9579, "lon": 77.1095, "impact": "NH-3 severed, severe valley floor destruction", "trigger": "Heavy Rain + Debris Choking"},
    {"year": 2025, "location": "Khaniyara / Manuni Khad", "district": "Kangra", "lat": 32.2200, "lon": 76.3500, "impact": "Sudden surge swept commercial stalls and slate mines", "trigger": "Dhauladhar Cloudburst"}
]

# Primary River Centerlines (Water Stream Vectors)
REGIONAL_RIVERS = {
    "Kullu (Upper Beas & Parbati Basin)": [
        [32.3500, 77.1600], [32.3126, 77.1603], [32.2967, 77.2050], 
        [32.2390, 77.1880], [32.1150, 77.1350], [31.9579, 77.1095], 
        [31.9310, 77.1260], [31.7800, 77.2900]
    ],
    "Mandi (Beas Gorges & Suketi Khad)": [
        [31.7500, 77.0200], [31.7200, 76.9600], [31.7087, 76.9320], 
        [31.6900, 76.9200], [31.6720, 76.9900], [31.5000, 76.9000]
    ],
    "Dharamshala / Kangra (Manuni & Manjhi Khad)": [
        [32.2500, 76.3300], [32.2200, 76.3500], [32.2190, 76.3234], 
        [32.2000, 76.2200], [32.1000, 76.1500]
    ],
    "Chamba / Mani Mahesh (Ravi & Budhil)": [
        [32.4200, 76.6400], [32.3950, 76.6200], [32.3600, 76.5800], 
        [32.5500, 76.1200], [32.7000, 76.0000]
    ]
}

# ----------------- SIDEBAR: PARAMETERS & ARDUINO -----------------
st.sidebar.title("🎛️ Basin Telemetry & Controls")
active_basin = st.sidebar.selectbox("Active Watershed Basin", list(REGIONAL_RIVERS.keys()))

village_names = [v["name"] for v in VILLAGE_DATABASE]
selected_village_name = st.sidebar.selectbox("Focal Riparian Node", village_names)
focal_village = next(v for v in VILLAGE_DATABASE if v["name"] == selected_village_name)

st.sidebar.markdown("---")
st.sidebar.subheader("🌧️ Precipitation & Environmental Factors")
OWM_API_KEY = "6faca06e4cfc7c9c23a4e0f1f1ab28f5"
use_live_weather = st.sidebar.checkbox("Fetch Live OpenWeatherMap Feed", value=False)

if use_live_weather:
    live_rain, live_temp, ok = get_live_weather(focal_village["lat"], focal_village["lon"], OWM_API_KEY)
    if ok:
        st.sidebar.success(f"Live Weather: {live_rain:.1f} mm/h | {live_temp:.1f}°C")
        rainfall_sim = live_rain if live_rain > 0 else 12.0
        temp_anomaly = max(-2.0, live_temp - 10.0)
    else:
        st.sidebar.warning("API timeout; using calibrated sliders.")
        rainfall_sim = st.sidebar.slider("Rainfall Rate (mm / 3h)", 0, 150, 65)
        temp_anomaly = st.sidebar.slider("Catchment Temp Anomaly (°C)", -2.0, 10.0, 4.2)
else:
    rainfall_sim = st.sidebar.slider("Precipitation Rate (mm / 3h)", 0, 150, 65)
    temp_anomaly = st.sidebar.slider("Alpine Temp Anomaly (°C above normal)", -2.0, 10.0, 4.2)

construction_pressure = st.sidebar.slider("Road-Cutting / Debris Severity", 0, 100, 80, help="Fresh slope excavation along NH/road corridors")

# ----------------- ARDUINO HARDWARE SLOT -----------------
st.sidebar.markdown("---")
st.sidebar.subheader("📡 Live Arduino River Gauge")
use_arduino = st.sidebar.checkbox("Connect Live Arduino Board (USB)")
water_level_cm = 32.0
sensor_triggered = False

if use_arduino:
    ports = [p.device for p in serial.tools.list_ports.comports()]
    selected_port = st.sidebar.selectbox("Select COM Port", ports if ports else ["None Detected"])
    if selected_port and selected_port != "None Detected":
        try:
            ser = serial.Serial(selected_port, 9600, timeout=1)
            raw = ser.readline().decode('utf-8', errors='ignore').strip()
            if raw:
                digits = ''.join([c for c in raw if c.isdigit() or c == '.'])
                if digits:
                    water_level_cm = float(digits)
                    st.sidebar.success(f"Hardware Level: {water_level_cm:.1f} cm")
            ser.close()
        except Exception as e:
            st.sidebar.warning(f"Waiting for hardware on {selected_port}...")
    else:
        st.sidebar.info("Arduino ready for connection.")
else:
    water_level_cm = st.sidebar.slider("Manual Water Column Height (cm)", 0, 200, 45)

if water_level_cm > 120:
    sensor_triggered = True

# ----------------- RISK COMPUTATION ENGINE -----------------
def compute_village_ffri(v, rain, temp_anom, constr, gauge_val, hard_trip):
    # 1. Rainfall score
    r_score = min(100.0, (rain / 80.0) * 100.0)
    
    # 2. Slope angle risk classification
    s = v["slope"]
    if s < 15:
        s_score = 20.0
    elif 15 <= s <= 25:
        s_score = 45.0
    elif 25 < s <= 35:
        s_score = 75.0
    elif 35 < s <= 45:
        s_score = 90.0
    else:
        s_score = 100.0
        
    # 3. Stream proximity factor
    prox_score = max(0.0, 100.0 - (v["dist_stream_m"] * 0.5))
    
    # 4. Glacial melt factor
    g_score = min(100.0, 45.0 + (temp_anom * 5.5))
    
    # 5. Anthropogenic & Gauge
    i_score = float(constr)
    w_score = min(100.0, (gauge_val / 150.0) * 100.0)
    
    # Composite Multi-Factor Flash Flood Risk Index (FFRI)
    ffri = (0.30 * r_score) + (0.25 * s_score) + (0.15 * prox_score) + (0.10 * g_score) + (0.10 * i_score) + (0.10 * w_score)
    if hard_trip:
        ffri = max(ffri, 94.0)
    return round(ffri, 1)

focal_ffri = compute_village_ffri(focal_village, rainfall_sim, temp_anomaly, construction_pressure, water_level_cm, sensor_triggered)

if focal_ffri < 35:
    status_label, hex_color, badge = "LOW RISK / ROUTINE", "#2ecc71", "🟢 NORMAL"
elif focal_ffri < 60:
    status_label, hex_color, badge = "ADVISORY / ELEVATED DISCHARGE", "#f1c40f", "🟡 ADVISORY"
elif focal_ffri < 80:
    status_label, hex_color, badge = "WARNING / ACTIVE SURGE", "#e67e22", "🟠 WARNING"
else:
    status_label, hex_color, badge = "CRITICAL EVACUATION ALERT", "#e74c3c", "🔴 SEVERE"

# ----------------- MAIN UI -----------------
st.title("🌊 PRAVAH: Multi-Source Flash Flood Early Warning System")
st.caption(f"Sector: **{focal_village['name']} ({focal_village['sub_district']})** | Primary Stream: **{focal_village['stream']}** | Threat: **{badge}**")

# Top KPI Metric Cards
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Precipitation Feed", f"{rainfall_sim:.1f} mm", "Cloudburst Risk" if rainfall_sim > 70 else "Normal")
k2.metric("Slope Angle", f"{focal_village['slope']}°", f"Facing {focal_village['aspect']}")
k3.metric("Stream Distance", f"{focal_village['dist_stream_m']} m", "High Riparian Inundation" if focal_village['dist_stream_m'] < 80 else "Corridor Buffer")
k4.metric("Road Excavation", f"{construction_pressure}%", "Toe Slump Vulnerability")
k5.metric("Water Column Level", f"{water_level_cm:.1f} cm", "SURGE CONFIRMED" if sensor_triggered else "Sub-critical")

st.markdown(f"""
<div style="padding: 14px; border-radius: 8px; background-color: {hex_color}; color: white; font-size: 20px; font-weight: bold; text-align: center; margin: 15px 0;">
    ACTIVE THREAT LEVEL: {status_label} (FFRI Score: {focal_ffri:.1f} / 100)
</div>
""", unsafe_allow_html=True)

# ----------------- HIGH-RISK STREAM PROXIMITY TABLE -----------------
st.subheader("📋 Riparian Village Risk Matrix (Sorted by Stream Proximity & Slope Vulnerability)")

table_data = []
for v in VILLAGE_DATABASE:
    v_ffri = compute_village_ffri(v, rainfall_sim, temp_anomaly, construction_pressure, water_level_cm, sensor_triggered)
    if v_ffri >= 80:
        v_class = "🔴 CRITICAL (EVACUATE)"
    elif v_ffri >= 60:
        v_class = "🟠 WARNING"
    elif v_ffri >= 35:
        v_class = "🟡 ADVISORY"
    else:
        v_class = "🟢 NORMAL"
        
    table_data.append({
        "Village / City": v["name"],
        "Sub-District": v["sub_district"],
        "Adjacent Water Stream": v["stream"],
        "Distance to Stream (m)": v["dist_stream_m"],
        "Slope Angle (°)": v["slope"],
        "Aspect": v["aspect"],
        "FFRI Score": v_ffri,
        "Risk Level": v_class
    })

df_risk = pd.DataFrame(table_data).sort_values(by="FFRI Score", ascending=False)
st.dataframe(df_risk, use_container_width=True, hide_index=True)

# ----------------- ORIGINAL SATELLITE & HAZARD MAP -----------------
st.subheader(f"🛰️ High-Resolution Satellite Corridor Mapping: {active_basin}")

m = folium.Map(
    location=[focal_village["lat"], focal_village["lon"]], 
    zoom_start=12, 
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles &copy; Esri World Imagery",
    name="Original Satellite View"
)

folium.TileLayer(
    tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attr="Map data: OpenTopoMap",
    name="Topographic Elevation"
).add_to(m)

folium.TileLayer("OpenStreetMap", name="Street Map").add_to(m)

# 1. Primary River Stream Bed
river_coords = REGIONAL_RIVERS[active_basin]
folium.PolyLine(
    locations=river_coords,
    color="#00ffff",
    weight=6,
    opacity=0.9,
    tooltip="Active River / Khad Bed Flow Line"
).add_to(m)

# 2. Dynamic Inundation Danger Corridor Buffer
for pt in river_coords:
    folium.Circle(
        location=pt,
        radius=400,
        color=hex_color,
        fill=True,
        fill_color=hex_color,
        fill_opacity=0.45,
        weight=2,
        tooltip=f"Floodplain Threat: {status_label}"
    ).add_to(m)

# 3. Plot 30 Villages with Proximity & Slope Data
for v in VILLAGE_DATABASE:
    v_ffri = compute_village_ffri(v, rainfall_sim, temp_anomaly, construction_pressure, water_level_cm, sensor_triggered)
    marker_color = "red" if v_ffri >= 80 else ("orange" if v_ffri >= 60 else ("yellow" if v_ffri >= 35 else "green"))
    
    folium.CircleMarker(
        location=[v["lat"], v["lon"]],
        radius=6 if v["name"] != focal_village["name"] else 12,
        color="#ffffff" if v["name"] == focal_village["name"] else marker_color,
        fill=True,
        fill_color=marker_color,
        fill_opacity=0.9,
        weight=3 if v["name"] == focal_village["name"] else 1,
        popup=f"<b>Village: {v['name']}</b><br>Stream: {v['stream']} ({v['dist_stream_m']}m)<br>Slope: {v['slope']}° ({v['aspect']})<br>FFRI: {v_ffri}"
    ).add_to(m)

# 4. Plot 40-Year HP SDMA Historical Review Points (1986-2026)
for incident in HISTORICAL_INCIDENTS:
    folium.Marker(
        location=[incident["lat"], incident["lon"]],
        popup=f"<b>{incident['year']} - {incident['location']}</b><br>Trigger: {incident['trigger']}<br>Impact: {incident['impact']}",
        icon=folium.Icon(color="darkred", icon="warning-sign")
    ).add_to(m)

folium.LayerControl(position="topright").add_to(m)

st_folium(m, width="100%", height=560)

# ----------------- 40-YEAR HISTORICAL LOG & SOP MATRIX -----------------
col_sop, col_hist = st.columns([1, 1])

with col_sop:
    st.subheader("🚨 Standard Operating Procedure (SOP)")
    if focal_ffri >= 80:
        st.error(f"""
        **RED EVACUATION ALERT FOR {focal_village['name'].upper()}**:
        - Immediate evacuation of settlements within 150m of {focal_village['stream']}.
        - Halt traffic across highway bridges and slope-cut stretches.
        - Trigger riverbank alert sirens; mobilize SDRF/NDRF.
        """)
    elif focal_ffri >= 60:
        st.warning(f"""
        **ORANGE FLOOD WARNING**:
        - Clear tourism, camping, and mining from {focal_village['stream']} banks.
        - Deploy earthmovers to clear culverts choking from road debris.
        """)
    else:
        st.info("🟢 **GREEN MONITORING**: Hydrological conditions within stable operating parameters.")

with col_hist:
    st.subheader("📜 HP SDMA 40-Year Record (1986–2026)")
    with st.expander("View Documented Flash Floods & Cloudbursts", expanded=False):
        for h in HISTORICAL_INCIDENTS:
            st.markdown(f"**{h['year']} — {h['location']} ({h['district']})**: {h['impact']} *(Cause: {h['trigger']})*")