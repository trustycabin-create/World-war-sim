from datetime import datetime
import json
import random
import requests
import streamlit as st
import streamlit.components.v1 as components

# ==============================================================================
# 🔑 PERMANENT CREDENTIALS
# ==============================================================================
TURSO_DB_URL = "https://war-sim-db-trustycabin-create.aws-ap-south-1.turso.io"
TURSO_AUTH_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTQxNTIyNDgsImlkIjoiMDFhMWJiY2ItN2EwMS03MGFjLWJhNjgtMjRhZmRhYzU5MWUwIiwia2lkIjoiMzUzN2hMbnhCR0trV2hnbXdCN1Y4MnA2YTJrZ1JRN041eUk5TTRVc0NYUSIsInJpZCI6IjI3Njg3MGJhLTBiNWItNGQ4Mi1hYmEyLWYzNmFmYzQwNTkxNSJ9.2iDgRALderyIM_IcVFV7cAPF4zF9sJP5ijfBp9wtKkHmk7skMMKyNgY-0ppOwjz1kK73wMH_HgmNWfPCNz2vCw"
GROQ_API_KEY = "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"

# ==============================================================================
# 📱 MOBILE PWA DASHBOARD CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="WWII Grand Strategy 1933",
    page_icon="🎖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #0b0e14; color: #c9d1d9; }
    .teletype {
        background-color: #161b22;
        border-left: 4px solid #d29922;
        padding: 10px;
        margin-bottom: 10px;
        font-family: monospace;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 🛠️ ROBUST DATA TYPE HELPERS
# ==============================================================================
def safe_int(val, default=0):
    try:
        return int(float(val)) if val is not None else default
    except (ValueError, TypeError):
        return default

def safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default

# ==============================================================================
# 🗄️ TURSO DATABASE PIPELINE
# ==============================================================================
def query_turso(sql: str):
    url = f"{TURSO_DB_URL}/v2/pipeline"
    headers = {"Authorization": f"Bearer {TURSO_AUTH_TOKEN}", "Content-Type": "application/json"}
    payload = {"requests": [{"type": "execute", "stmt": {"sql": sql}}, {"type": "close"}]}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        if res.status_code != 200:
            return []
        result = res.json().get("results", [{}])[0].get("response", {}).get("result", {})
        cols = [c["name"] for c in result.get("cols", [])]
        rows = []
        for r in result.get("rows", []):
            rows.append({cols[i]: r[i].get("value") for i in range(len(cols))})
        return rows
    except Exception:
        return []

def execute_turso_batch(statements: list):
    url = f"{TURSO_DB_URL}/v2/pipeline"
    headers = {"Authorization": f"Bearer {TURSO_AUTH_TOKEN}", "Content-Type": "application/json"}
    reqs = [{"type": "execute", "stmt": {"sql": s}} for s in statements]
    reqs.append({"type": "close"})
    try:
        res = requests.post(url, headers=headers, json={"requests": reqs}, timeout=10)
        return res.status_code == 200
    except Exception:
        return False

def add_dispatch(headline: str, body: str, classification: str = "DIRECTIVE", origin: str = "High Command"):
    safe_body = str(body)[:350].replace("'", "''")
    safe_head = str(headline)[:80].replace("'", "''")
    disp_id = f"DISP-{random.randint(1000, 9999)}"
    sql = f"INSERT INTO intelligence_dispatches (dispatch_id, timestamp, origin, classification, headline, body) VALUES ('{disp_id}', datetime('now'), '{origin}', '{classification}', '{safe_head}', '{safe_body}');"
    execute_turso_batch([sql])

def ensure_conquest_schema():
    patches = [
        "ALTER TABLE regions ADD COLUMN garrison_strength INTEGER DEFAULT 30000;",
        "ALTER TABLE regions ADD COLUMN latitude REAL DEFAULT 50.0;",
        "ALTER TABLE regions ADD COLUMN longitude REAL DEFAULT 10.0;",
        "ALTER TABLE national_stockpiles ADD COLUMN munitions_tonnage REAL DEFAULT 45000.0;",
        "UPDATE national_stockpiles SET munitions_tonnage = 45000.0 WHERE munitions_tonnage IS NULL;",
        "INSERT OR REPLACE INTO regions (region_id, name, owner_nation, terrain_type, rail_gauge, soil_moisture, temperature_c, population, caloric_intake, terror_index, resistance_network, infrastructure_hp, is_demilitarized, garrison_strength, latitude, longitude) VALUES ('REG-BERLIN', 'Berlin-Brandenburg', 'GERMANY', 'URBAN', 'STANDARD', 0.25, 0.5, 4300000, 2350.0, 8.0, 1.2, 100.0, 0, 75000, 52.52, 13.40);",
        "INSERT OR REPLACE INTO regions (region_id, name, owner_nation, terrain_type, rail_gauge, soil_moisture, temperature_c, population, caloric_intake, terror_index, resistance_network, infrastructure_hp, is_demilitarized, garrison_strength, latitude, longitude) VALUES ('REG-RUHR', 'Ruhr Valley', 'GERMANY', 'URBAN', 'STANDARD', 0.30, 2.0, 3800000, 2400.0, 6.0, 2.5, 100.0, 0, 25000, 51.45, 7.01);",
        "INSERT OR REPLACE INTO regions (region_id, name, owner_nation, terrain_type, rail_gauge, soil_moisture, temperature_c, population, caloric_intake, terror_index, resistance_network, infrastructure_hp, is_demilitarized, garrison_strength, latitude, longitude) VALUES ('REG-RHINELAND', 'The Rhineland', 'GERMANY', 'PLAINS', 'STANDARD', 0.28, 3.0, 2900000, 2400.0, 4.0, 1.0, 100.0, 1, 0, 50.11, 7.50);",
        "INSERT OR REPLACE INTO regions (region_id, name, owner_nation, terrain_type, rail_gauge, soil_moisture, temperature_c, population, caloric_intake, terror_index, resistance_network, infrastructure_hp, is_demilitarized, garrison_strength, latitude, longitude) VALUES ('REG-EASTPRUSSIA', 'East Prussia (Königsberg)', 'GERMANY', 'PLAINS', 'STANDARD', 0.35, -2.5, 2300000, 2200.0, 5.0, 0.5, 95.0, 0, 15000, 54.71, 20.51);",
        "INSERT OR REPLACE INTO regions (region_id, name, owner_nation, terrain_type, rail_gauge, soil_moisture, temperature_c, population, caloric_intake, terror_index, resistance_network, infrastructure_hp, is_demilitarized, garrison_strength, latitude, longitude) VALUES ('REG-AUSTRIA', 'Austria (Vienna)', 'AUSTRIA', 'HILLS', 'STANDARD', 0.22, 2.0, 6700000, 2450.0, 3.0, 0.0, 100.0, 0, 40000, 48.20, 16.37);",
        "INSERT OR REPLACE INTO regions (region_id, name, owner_nation, terrain_type, rail_gauge, soil_moisture, temperature_c, population, caloric_intake, terror_index, resistance_network, infrastructure_hp, is_demilitarized, garrison_strength, latitude, longitude) VALUES ('REG-CZECH', 'Bohemia & Sudetenland', 'CZECHOSLOVAKIA', 'MOUNTAINS', 'STANDARD', 0.30, 1.0, 7200000, 2500.0, 5.0, 0.0, 100.0, 0, 80000, 50.07, 14.43);",
        "INSERT OR REPLACE INTO regions (region_id, name, owner_nation, terrain_type, rail_gauge, soil_moisture, temperature_c, population, caloric_intake, terror_index, resistance_network, infrastructure_hp, is_demilitarized, garrison_strength, latitude, longitude) VALUES ('REG-PARIS', 'Paris & Alsace', 'FRANCE', 'URBAN', 'STANDARD', 0.25, 4.0, 4500000, 2600.0, 2.0, 0.0, 100.0, 0, 140000, 48.85, 2.35);",
        "INSERT OR REPLACE INTO regions (region_id, name, owner_nation, terrain_type, rail_gauge, soil_moisture, temperature_c, population, caloric_intake, terror_index, resistance_network, infrastructure_hp, is_demilitarized, garrison_strength, latitude, longitude) VALUES ('REG-WARSAW', 'Warsaw Province', 'POLAND', 'PLAINS', 'STANDARD', 0.40, -1.0, 3100000, 2100.0, 4.0, 0.0, 90.0, 0, 95000, 52.23, 21.01);",
        "INSERT OR REPLACE INTO regions (region_id, name, owner_nation, terrain_type, rail_gauge, soil_moisture, temperature_c, population, caloric_intake, terror_index, resistance_network, infrastructure_hp, is_demilitarized, garrison_strength, latitude, longitude) VALUES ('REG-MOSCOW', 'Moscow Oblast', 'USSR', 'URBAN', 'BROAD', 0.50, -12.0, 4000000, 2050.0, 45.0, 0.0, 85.0, 0, 250000, 55.75, 37.61);"
    ]
    for patch in patches:
        try:
            execute_turso_batch([patch])
        except Exception:
            pass

ensure_conquest_schema()

# ==============================================================================
# 🤖 GROQ AI DIRECTIVE ENGINE
# ==============================================================================
def call_groq_llm(key: str, sys_prompt: str, user_prompt: str):
    headers = {"Authorization": f"Bearer {key.strip()}", "Content-Type": "application/json"}
    for model in ["llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b"]:
        try:
            payload = {
                "model": model,
                "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}],
                "temperature": 0.3,
                "max_tokens": 700,
            }
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=12)
            if res.status_code == 200:
                txt = res.json()["choices"][0]["message"]["content"]
                return txt.split("</think>")[-1].strip() if "</think>" in txt else txt
        except Exception:
            continue
    return "TELETYPE NOTICE // DISPATCH CARRIER SEVERED // COURIER DELAY IN EFFECT."

# ==============================================================================
# 🧭 SIDEBAR HIGH COMMAND
# ==============================================================================
with st.sidebar:
    st.title("🎖️ High Command")
    st.success("Groq Neural Pipeline Active")
    army_row = query_turso("SELECT SUM(garrison_strength) as total_men FROM regions WHERE owner_nation = 'GERMANY';")
    raw_men = army_row[0].get("total_men") if army_row else None
    current_men = safe_int(raw_men, 115000)
    st.metric("Total Armed Personnel", f"{current_men:,} men")
    if current_men > 100000:
        st.warning("⚠️ Versailles 100,000-man military cap breached!")[span_1](start_span)[span_1](end_span)

# ==============================================================================
# 📊 TOP HUD STOCKPILES
# ==============================================================================
stock = query_turso("SELECT * FROM national_stockpiles WHERE nation = 'GERMANY' LIMIT 1;")
c1, c2, c3, c4 = st.columns(4)
if stock:
    s = stock[0]
    c1.metric("Date", "1933 Simulation")
    c2.metric("Crude Oil", f"{safe_float(s.get('crude_oil'), 0.0):,.0f} t")
    c3.metric("Steel", f"{safe_float(s.get('high_grade_steel'), 0.0):,.0f} t")
    c4.metric("Munitions", f"{safe_float(s.get('munitions_tonnage'), 45000.0):,.0f} t")

st.divider()

# ==============================================================================
# 🎮 DASHBOARD TABS
# ==============================================================================
tab_map, tab_conquer, tab_industry, tab_decrees, tab_inbox = st.tabs([
    "🗺️ Operational Map",
    "⚔️ War Theater & Conquest",
    "⚙️ Armament Works",
    "🏛️ War Cabinet Hub",
    "📥 Intelligence Inbox",
])

# 1. MAP
with tab_map:
    st.subheader("European Theater of Operations (1933 Strategic Nodes)")
    regions_data = query_turso("SELECT region_id, name, owner_nation, terrain_type, is_demilitarized, garrison_strength, latitude, longitude FROM regions;")
    color_map = {
        "GERMANY": "#5c6b73", "FRANCE": "#1f77b4", "POLAND": "#e377c2",
        "USSR": "#d62728", "AUSTRIA": "#bcbd22", "CZECHOSLOVAKIA": "#2ca02c"
    }
    markers_js = []
    for r in regions_data:
        lat = safe_float(r.get("latitude"), 50.0)
        lon = safe_float(r.get("longitude"), 10.0)
        owner = str(r.get("owner_nation") or "UNKNOWN")
        name = str(r.get("name") or "Sector")
        garrison = safe_int(r.get("garrison_strength"), 0)
        is_demil = safe_int(r.get("is_demilitarized"), 0)
        m_color = "#e6a23c" if is_demil else color_map.get(owner, "#999999")
        status_txt = "DEMILITARIZED BUFFER" if is_demil else f"Garrison: {garrison:,} men"
        popup = f"{name} ({owner}) - {status_txt}"
        markers_js.append(f"L.circleMarker([{lat}, {lon}], {{radius: 12, fillColor: '{m_color}', color: '#ffffff', weight: 2, fillOpacity: 0.85}}).addTo(map).bindPopup('{popup}');")

    all_markers = "\n".join(markers_js)
    leaflet_code = f"""<!DOCTYPE html><html><head><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><style>#map {{ height: 420px; width: 100%; border-radius: 8px; background: #0b0e14; }}</style></head><body><div id="map"></div><script>var map = L.map('map').setView([51.5, 13.0], 4); L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{ maxZoom: 7, minZoom: 3 }}).addTo(map); {all_markers} </script></body></html>"""
    components.html(leaflet_code, height=440)
    st.caption("Map Legend: Gray = Germany | Blue = France | Pink = Poland | Red = USSR | Gold = Austria | Orange = Demilitarized")

# 2. CONQUEST & INVASION
with tab_conquer:
    st.subheader("Operational War Theater: Execute Invasions & Remilitarization")
    all_regions = query_turso("SELECT * FROM regions;")
    region_options = {f"{r['name']} ({r['owner_nation']})": r for r in all_regions}

    col_target, col_action = st.columns(2)
    with col_target:
        selected_label = st.selectbox("Select Target Sector", list(region_options.keys()))
        target_region = region_options[selected_label]

    with col_action:
        is_target_demil = safe_int(target_region.get("is_demilitarized"), 0)
        if target_region["owner_nation"] == "GERMANY" and is_target_demil == 1:
            action_type = st.radio("Operation Type", ["Remilitarize Sector (Breach Versailles)", "Maintain Observation"])
        elif target_region["owner_nation"] == "GERMANY":
            action_type = st.radio("Operation Type", ["Reinforce Garrison", "Redeploy Divisions"])
        else:
            action_type = st.radio("Operation Type", ["Launch Armed Blitzkrieg", "Diplomatic Subversion / Annexation"])

    troops_committed = st.slider("Divisions / Personnel to Commit", 5000, 150000, 35000, step=5000)

    if st.button("⚔️ EXECUTE GENERAL STAFF ORDER", use_container_width=True):
        reg_id = target_region["region_id"]
        reg_name = target_region["name"]
        curr_owner = target_region["owner_nation"]
        curr_garrison = safe_int(target_region.get("garrison_strength"), 30000)

        if "Remilitarize" in action_type:
            with st.spinner("Marching Reichswehr columns across the Rhine..."):
                if random.random() < 0.85:
                    outcome = "SUCCESS // French forces remain static behind Maginot Line. Rhineland sovereign military zone restored[span_2](start_span)!"[span_2](end_span)
                    execute_turso_batch([f"UPDATE regions SET is_demilitarized = 0, garrison_strength = {troops_committed} WHERE region_id = '{reg_id}';"])
                    add_dispatch("RHINELAND REMILITARIZED", outcome, "VICTORY", "OKW High Command")
                    st.success(outcome)
                    st.rerun()
                else:
                    outcome = "CRISIS // French High Command initiates partial mobilization! Diplomatic blockade in effect."
                    st.error(outcome)

        elif "Armed Blitzkrieg" in action_type:
            with st.spinner(f"Assaulting {reg_name}..."):
                attacker_loss = int(curr_garrison * 0.28 * random.uniform(0.7, 1.2))
                defender_loss = int(troops_committed * 0.45 * random.uniform(0.8, 1.3))
                remaining_attacker = max(0, troops_committed - attacker_loss)
                remaining_defender = max(0, curr_garrison - defender_loss)
                fuel_burnt = (troops_committed / 1000.0) * 12.0
                ammo_burnt = (troops_committed / 1000.0) * 8.5

                if remaining_attacker > remaining_defender:
                    outcome = f"PROVINCE CAPTURED // {reg_name} has fallen! Wehrmacht casualties: {attacker_loss:,} men. Enemy losses: {defender_loss:,} men."
                    execute_turso_batch([
                        f"UPDATE regions SET owner_nation = 'GERMANY', garrison_strength = {remaining_attacker} WHERE region_id = '{reg_id}';",
                        f"UPDATE national_stockpiles SET crude_oil = MAX(0, crude_oil - {fuel_burnt}), munitions_tonnage = MAX(0, munitions_tonnage - {ammo_burnt}) WHERE nation = 'GERMANY';"
                    ])
                    add_dispatch(f"{reg_name.upper()} SEIZED", outcome, "CONQUEST", "Frontline Command")
                    st.success(outcome)
                    st.rerun()
                else:
                    outcome = f"OFFENSIVE REPULSED // Assault stalled in {reg_name}. Wehrmacht suffered {attacker_loss:,} casualties."
                    execute_turso_batch([
                        f"UPDATE regions SET garrison_strength = {remaining_defender} WHERE region_id = '{reg_id}';",
                        f"UPDATE national_stockpiles SET crude_oil = MAX(0, crude_oil - {fuel_burnt}), munitions_tonnage = MAX(0, munitions_tonnage - {ammo_burnt}) WHERE nation = 'GERMANY';"
                    ])
                    st.error(outcome)

        elif "Annexation" in action_type:
            with st.spinner(f"Sending ultimatums to {reg_name}..."):
                if random.random() > 0.40:
                    outcome = f"ANNEXATION COMPLETE // Local cabinet capitulated. {reg_name} absorbed into the Reich with zero casualties!"
                    execute_turso_batch([f"UPDATE regions SET owner_nation = 'GERMANY', garrison_strength = {troops_committed + curr_garrison} WHERE region_id = '{reg_id}';"])
                    add_dispatch(f"{reg_name.upper()} ANNEXED", outcome, "INTEGRATION", "Foreign Ministry")
                    st.success(outcome)
                    st.rerun()
                else:
                    st.warning("DIPLOMATIC STALEMATE // The local government refused ultimatums; border garrisons reinforced.")

# 3. INDUSTRIAL PRODUCTION
with tab_industry:
    st.subheader("Industrial Mobilization & Production")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Recruit Wehrmacht Divisions**")
        st.caption("Consumes: 2,000t Steel + 150t Munitions")
        if st.button("Mobilize 15,000 Infantry Cadre"):
            execute_turso_batch([
                "UPDATE national_stockpiles SET high_grade_steel = high_grade_steel - 2000, munitions_tonnage = munitions_tonnage - 150 WHERE nation = 'GERMANY';",
                "UPDATE regions SET garrison_strength = garrison_strength + 15000 WHERE region_id = 'REG-BERLIN';"
            ])
            st.success("15,000 fresh infantry inducted into Berlin Reserve Cadre!")
            st.rerun()

    with col2:
        st.markdown("**Fischer-Tropsch Synthetic Fuel Synthesis**")[span_3](start_span)[span_3](end_span)
        st.caption("Consumes: 10,000t Coal -> Yields: 3,500t Fuel")
        if st.button("Synthesize Synthetic Fuel"):
            execute_turso_batch([
                "UPDATE national_stockpiles SET lignite_coal = lignite_coal - 10000, synthetic_fuel = synthetic_fuel + 3500, crude_oil = crude_oil + 1500 WHERE nation = 'GERMANY';"
            ])
            st.success("Refineries produced 3,500t synthetic petroleum!")
            st.rerun()

# 4. WAR CABINET DECREES
with tab_decrees:
    st.subheader("Issue Unscripted Directives to High Command")
    decree_txt = st.text_area("Decree", placeholder="e.g. Expand clandestine submarine construction under decoy corporation...")
    if st.button("Transmit Directive"):
        if not decree_txt.strip():
            st.warning("Please type a directive.")
        else:
            with st.spinner("General Staff reality gat
