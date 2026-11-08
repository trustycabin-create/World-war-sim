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
        padding: 12px;
        margin-bottom: 12px;
        font-family: monospace;
        font-size: 0.85rem;
    }
    .metric-card {
        background: #161b22;
        border-radius: 6px;
        padding: 10px;
        border: 1px solid #30363d;
        margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# 🗄️ TURSO CLOUD PIPELINE ENGINE
# ==============================================================================
def query_turso(sql: str):
    url = f"{TURSO_DB_URL}/v2/pipeline"
    headers = {
        "Authorization": f"Bearer {TURSO_AUTH_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "requests": [{"type": "execute", "stmt": {"sql": sql}}, {"type": "close"}]
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        if res.status_code != 200:
            return []
        data = res.json()
        result = data.get("results", [{}])[0].get("response", {}).get("result", {})
        cols = [col["name"] for col in result.get("cols", [])]
        rows = []
        for r in result.get("rows", []):
            rows.append({cols[i]: r[i].get("value") for i in range(len(cols))})
        return rows
    except Exception:
        return []


def execute_turso_batch(statements: list):
    url = f"{TURSO_DB_URL}/v2/pipeline"
    headers = {
        "Authorization": f"Bearer {TURSO_AUTH_TOKEN}",
        "Content-Type": "application/json",
    }
    reqs = [{"type": "execute", "stmt": {"sql": s}} for s in statements]
    reqs.append({"type": "close"})
    try:
        res = requests.post(url, headers=headers, json={"requests": reqs}, timeout=10)
        return res.status_code == 200
    except Exception:
        return False


def ensure_conquest_schema():
    try:
        execute_turso_batch([
            """ALTER TABLE regions ADD COLUMN garrison_strength INTEGER DEFAULT 30000;""",
            """ALTER TABLE regions ADD COLUMN latitude REAL DEFAULT 50.0;""",
            """ALTER TABLE regions ADD COLUMN longitude REAL DEFAULT 10.0;""",
            """
            INSERT OR REPLACE INTO regions (region_id, name, owner_nation, terrain_type, rail_gauge, soil_moisture, temperature_c, population, caloric_intake, terror_index, resistance_network, infrastructure_hp, is_demilitarized, garrison_strength, latitude, longitude)
            VALUES 
            ('REG-BERLIN', 'Berlin-Brandenburg', 'GERMANY', 'URBAN', 'STANDARD', 0.25, 0.5, 4300000, 2350.0, 8.0, 1.2, 100.0, 0, 75000, 52.52, 13.40),
            ('REG-RUHR', 'Ruhr Valley', 'GERMANY', 'URBAN', 'STANDARD', 0.30, 2.0, 3800000, 2400.0, 6.0, 2.5, 100.0, 0, 25000, 51.45, 7.01),
            ('REG-RHINELAND', 'The Rhineland', 'GERMANY', 'PLAINS', 'STANDARD', 0.28, 3.0, 2900000, 2400.0, 4.0, 1.0, 100.0, 1, 0, 50.11, 7.50),
            ('REG-EASTPRUSSIA', 'East Prussia (Königsberg)', 'GERMANY', 'PLAINS', 'STANDARD', 0.35, -2.5, 2300000, 2200.0, 5.0, 0.5, 95.0, 0, 15000, 54.71, 20.51),
            ('REG-AUSTRIA', 'Austria (Vienna)', 'AUSTRIA', 'HILLS', 'STANDARD', 0.22, 2.0, 6700000, 2450.0, 3.0, 0.0, 100.0, 0, 40000, 48.20, 16.37),
            ('REG-CZECH', 'Bohemia & Sudetenland', 'CZECHOSLOVAKIA', 'MOUNTAINS', 'STANDARD', 0.30, 1.0, 7200000, 2500.0, 5.0, 0.0, 100.0, 0, 80000, 50.07, 14.43),
            ('REG-PARIS', 'Paris & Alsace', 'FRANCE', 'URBAN', 'STANDARD', 0.25, 4.0, 4500000, 2600.0, 2.0, 0.0, 100.0, 0, 140000, 48.85, 2.35),
            ('REG-WARSAW', 'Warsaw Province', 'POLAND', 'PLAINS', 'STANDARD', 0.40, -1.0, 3100000, 2100.0, 4.0, 0.0, 90.0, 0, 95000, 52.23, 21.01),
            ('REG-MOSCOW', 'Moscow Oblast', 'USSR', 'URBAN', 'BROAD', 0.50, -12.0, 4000000, 2050.0, 45.0, 0.0, 85.0, 0, 250000, 55.75, 37.61);
            """
        ])
    except Exception:
        pass


ensure_conquest_schema()


# ==============================================================================
# 🤖 GROQ DUAL-LLM PIPELINE
# ==============================================================================
def call_groq_llm(key: str, sys_prompt: str, user_prompt: str):
    if not key:
        return "ERROR: Groq API Key is not configured."

    headers = {
        "Authorization": f"Bearer {key.strip()}",
        "Content-Type": "application/json",
    }

    models = ["llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b"]
    for model in models:
        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 800,
                },
                timeout=12,
            )
            if res.status_code == 200:
                txt = res.json()["choices"][0]["message"]["content"]
                if "</think>" in txt:
                    txt = txt.split("</think>")[-1].strip()
                return txt
        except Exception:
            continue
    return "TELETYPE NOTICE // DISPATCH CARRIER SEVERED // COURIER DELAY IN EFFECT."


# ==============================================================================
# 🧭 SIDEBAR HIGH COMMAND CONTROLS
# ==============================================================================
with st.sidebar:
    st.title("🎖️ High Command")
    st.success("Groq Neural Pipeline Online")

    st.subheader("Wehrmacht Mobilization")
    army_row = query_turso("""SELECT SUM(garrison_strength) as total_men FROM regions WHERE owner_nation = 'GERMANY';""")
    current_men = army_row[0].get("total_men", 115000) if army_row else 115000
    st.metric("Total Armed Personnel", f"{int(current_men):,} men")
    if current_men > 100000:
        st.warning("⚠️ Versailles 100,000-man military cap breached! Allied surveillance alerted.")

# ==============================================================================
# 📊 TOP HUD STOCKPILES (1933 REALISM)
# ==============================================================================
stock = query_turso("""SELECT * FROM national_stockpiles WHERE nation = 'GERMANY' LIMIT 1;""")
c1, c2, c3, c4 = st.columns(4)
if stock:
    s = stock[0]
    c1.metric("Date", "1933 Simulation")
    c2.metric("Crude Oil", f"{float(s.get('crude_oil', 0)):,.0f} t")
    c3.metric("Steel", f"{float(s.get('high_grade_steel', 0)):,.0f} t")
    c4.metric("Munitions", f"{float(s.get('munitions_tonnage', 0)):,.0f} t")

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

# --- 1. OPERATIONAL EUROPEAN MAP ---
with tab_map:
    st.subheader("European Theater of Operations (1933 Strategic Nodes)")

    regions_data = query_turso("""SELECT region_id, name, owner_nation, terrain_type, is_demilitarized, garrison_strength, latitude, longitude FROM regions;""")

    color_map = {
        "GERMANY": "#5c6b73",
        "FRANCE": "#1f77b4",
        "POLAND": "#e377c2",
        "USSR": "#d62728",
        "AUSTRIA": "#bcbd22",
        "CZECHOSLOVAKIA": "#2ca02c",
    }

    markers_js = []
    for r in regions_data:
        lat = float(r.get("latitude") or 50.0)
        lon = float(r.get("longitude") or 10.0)
        owner = r.get("owner_nation")
        name = r.get("name")
        garrison = int(r.get("garrison_strength") or 0)
        is_demil = int(r.get("is_demilitarized") or 0)

        marker_color = "#e6a23c" if is_demil else color_map.get(owner, "#999999")
        status_txt = "⚠️ DEMILITARIZED BUFFER" if is_demil else f"Garrison: {garrison:,} men"
        popup = f"<b>{name}</b><br>Owner: {owner}<br>{status_txt}<br>Terrain: {r.get('terrain_type')}"

        markers_js.append(
            f"L.circleMarker([{lat}, {lon}], {{radius: 12, fillColor: '{marker_color}', color: '#ffffff', weight: 2, fillOpacity: 0.85}}).addTo(map).bindPopup('{popup}');"
        )

    all_markers = "\n".join(markers_js)

    map_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            #map { height: 420px; width: 100%; border-radius: 8px; background: #0b0e14; }
            .leaflet-popup-content-wrapper { background: #161b22; color: #e6edf3; font-family: monospace; border: 1px solid #30363d; }
            .leaflet-popup-tip { background: #161b22; }
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            var map = L.map('map').setView([51.5, 13.0], 4);
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                maxZoom: 7,
                minZoom: 3,
                attribution: '&copy; CartoDB'
            }).addTo(map);
            __MARKERS__
        </script>
    </body>
    </html>
    """
    final_map_html = map_template.replace("__MARKERS__", all_markers)
    components.html(final_map_html, height=440)
    st.caption("🗺️ Map Legend: Gray = Germany | Blue = France | Pink = Poland | Red = USSR | Gold = Austria | Orange = Demilitarized")

# --- 2. WAR THEATER & CONQUEST ---
with tab_conquer:
    st.subheader("Operational War Theater: Execute Invasions & Remilitarization")

    all_regions = query_turso("""SELECT * FROM regions;""")
    region_options = {f"{r['name']} ({r['owner_nation']})": r for r in all_regions}

    col_target, col_action = st.columns(2)
    with col_target:
        selected_label = st.selectbox("Select Target Sector", list(region_options.keys()))
        target_region = region_options[selected_label]

    with col_action:
        if target_region["owner_nation"] == "GERMANY" and int(target_region.get("is_demilitarized") or 0) == 1:
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
        curr_garrison = int(target_region.get("garrison_strength") or 30000)

        # Rhineland Remilitarization
        if "Remilitarize" in action_type:
            with st.spinner("Marching Reichswehr infantry battalions across the Rhine bridges..."):
                if random.random() < 0.85:
                    outcome = "SUCCESS // Allied Powers lodged formal diplomatic protests in Geneva, but French divisions remain locked behind the Maginot Line. Rhineland re-integrated into the Reich!"
                    sql_updates = [
                        f"""UPDATE regions SET is_demilitarized = 0, garrison_strength = {troops_committed} WHERE region_id = '{reg_id}';""",
                        f"""INSERT INTO intelligence_dispatches VALUES ('DISP-{random.randint(1000,9999)}', datetime('now'), 'OKW High Command', 'VICTORY', 'RHINELAND REMILITARIZED', '{outcome}');"""
                    ]
                    execute_turso_batch(sql_updates)
                    st.success(outcome)
                    st.rerun()
                else:
                    outcome = "CRISIS // French High Command initiates partial mobilization! Severe diplomatic blockade imposed."
                    st.error(outcome)

        # Armed Blitzkrieg (Lanchester Combat Model)
        elif "Armed Blitzkrieg" in action_type:
            with st.spinner(f"Assaulting {reg_name} against {curr_owner} forces..."):
                attacker_loss = int(curr_garrison * 0.28 * random.uniform(0.7, 1.2))
                defender_loss = int(troops_committed * 0.45 * random.uniform(0.8, 1.3))

                remaining_attacker = max(0, troops_committed - attacker_loss)
                remaining_defender = max(0, curr_garrison - defender_loss)

                fuel_burnt = (troops_committed / 1000.0) * 12.0
                ammo_burnt = (troops_committed / 1000.0) * 8.5

                if remaining_attacker > remaining_defender:
                    outcome = f"PROVINCE CAPTURED // {reg_name} has fallen! Wehrmacht casualties: {attacker_loss:,} men. Enemy losses: {defender_loss:,} men. Province annexed!"
                    sql_updates = [
                        f"""UPDATE regions SET owner_nation = 'GERMANY', garrison_strength = {remaining_attacker} WHERE region_id = '{reg_id}';""",
                        f"""UPDATE national_stockpiles SET crude_oil = MAX(0, crude_oil - {fuel_burnt}), munitions_tonnage = MAX(0, munitions_tonnage - {ammo_burnt}) WHERE nation = 'GERMANY';""",
                        f"""INSERT INTO intelligence_dispatches VALUES ('DISP-{random.randint(1000,9999)}', datetime('now'), 'Frontline Command', 'CONQUEST', '{reg_name.upper()} SEIZED', '{outcome}');"""
                    ]
                    execute_turso_batch(sql_updates)
                    st.success(outcome)
                    st.rerun()
                else:
                    outcome = f"OFFENSIVE REPULSED // Attack stalled in {reg_name}. Wehrmacht suffered {attacker_loss:,} casualties."
                    sql_updates = [
                        f"""UPDATE regions SET garrison_strength = {remaining_defender} WHERE region_id = '{reg_id}';""",
                        f"""UPDATE national_stockpiles SET crude_oil = MAX(0, crude_oil - {fuel_burnt}), munitions_tonnage = MAX(0, munitions_tonnage - {ammo_burnt}) WHERE nation = 'GERMANY';"""
                    ]
                    execute_turso_batch(sql_updates)
                    st.error(outcome)

        # Diplomatic Annexation
        elif "Annexation" in action_type:
            with st.spinner(f"Coordinating diplomatic ultimatums with fifth-columnists in {reg_name}..."):
                if random.random() > 0.40:
                    outcome = f"ANNEXATION COMPLETE // Local cabinet capitulated to ultimatums. {reg_name} absorbed into the Reich with zero combat losses!"
                    sql_updates = [
                        f"""UPDATE regions SET owner_nation = 'GERMANY', garrison_strength = {troops_committed + curr_garrison} WHERE region_id = '{reg_id}';""",
                        f"""INSERT INTO intelligence_dispatches VALUES ('DISP-{random.randint(1000,9999)}', datetime('now'), 'Foreign Ministry', 'INTEGRATION', '{reg_name.upper()} ANNEXED', '{outcome}');"""
                    ]
                    execute_turso_batch(sql_updates)
                    st.success(outcome)
                    st.rerun()
                else:
                    st.warning("DIPLOMATIC STALEMATE // The local government refused ultimatums; border garrisons reinforced.")

# --- 3. ARMAMENT WORKS & RECRUITMENT ---
with tab_industry:
    st.subheader("Industrial Mobilization & Equipment Production")
    col_prod1, col_prod2 = st.columns(2)

    with col_prod1:
        st.markdown("**Recruit Wehrmacht Divisions**")
        st.caption("Consumes: 2,000t High-Grade Steel + 150t Munitions")
        if st.button("Mobilize 15,000 Infantry Cadre"):
            sql = [
                """UPDATE national_stockpiles SET high_grade_steel = high_grade_steel - 2000, munitions_tonnage = munitions_tonnage - 150 WHERE nation = 'GERMANY';""",
                """UPDATE regions SET garrison_strength = garrison_strength + 15000 WHERE region_id = 'REG-BERLIN';"""
            ]
            execute_turso_batch(sql)
            st.success("15,000 fresh infantry inducted into Berlin Reserve Cadre!")
            st.rerun()

    with col_prod2:
        st.markdown("**Fischer-Tropsch Synthetic Fuel Synthesis**")
        st.caption("Consumes: 10,000t Lignite Coal -> Yields: 3,500t Synthetic Fuel")
        if st.button("Synthesize Synthetic Fuel"):
            sql = [
                """UPDATE national_stockpiles SET lignite_coal = lignite_coal - 10000, synthetic_fuel = synthetic_fuel + 3500, crude_oil = crude_oil + 1500 WHERE nation = 'GERMANY';"""
            ]
            execute_turso_batch(sql)
            st.success("Refineries produced 3,500t synthetic petroleum!")
            st.rerun()

# --- 4. WAR CABINET DECREES ---
with tab_decrees:
    st.subheader("Issue Unscripted Directives to High Command")
    decree_txt = st.text_area("Decree", placeholder="e.g. Order Krupp to redesign 7.92mm cartridges with tungsten-carbide cores...")

    if st.button("Transmit Directive"):
        if not decree_txt.strip():
            st.warning("Please type a directive.")
        else:
            with st.spinner("General Staff reality gatekeeper processing..."):
                sys_prompt = (
                    "You are the OKW General Staff reality gatekeeper in 1933. "
                    "Decompose the user's unscripted decree into realistic metallurgical, logistical, "
                    "and geopolitical consequences. Use a terse, sterile 1930s military dispatch style."
                )
                resp = call_groq_llm(GROQ_API_KEY, sys_prompt, decree_txt)
                clean_txt = resp[:350].replace("'", "''")
                disp_id = f"DISP-{random.randint(1000,9999)}"
                execute_turso_batch([
                    f"""INSERT INTO intelligence_dispatches VALUES ('{disp_id}', datetime('now'), 'War Cabinet', 'DIRECTIVE', 'DECREE ACKNOWLEDGED', '{clean_txt}');"""
                ])
                st.info(resp)

# --- 5. INTELLIGENCE DISPATCHES ---
with tab_inbox:
    st.subheader("Intelligence Teletype Feed")
    disp = query_turso("""SELECT * FROM intelligence_dispatches ORDER BY timestamp DESC LIMIT 8;""")
    for d in disp:
        st.markdown(
            f"""
            <div class="teletype">
                <b>[{d.get('classification')}] {d.get('headline')}</b> — <i
