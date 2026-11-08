import streamlit as st, requests, random, streamlit.components.v1 as components

# --- CREDENTIALS & SETUP ---
st.set_page_config(page_title="WWII Grand Strategy 1933", page_icon="🎖️", layout="wide")
TURSO_URL = "https://war-sim-db-trustycabin-create.aws-ap-south-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTQxNTIyNDgsImlkIjoiMDFhMWJiY2ItN2EwMS03MGFjLWJhNjgtMjRhZmRhYzU5MWUwIiwia2lkIjoiMzUzN2hMbnhCR0trV2hnbXdCN1Y4MnA2YTJrZ1JRN041eUk5TTRVc0NYUSIsInJpZCI6IjI3Njg3MGJhLTBiNWItNGQ4Mi1hYmEyLWYzNmFmYzQwNTkxNSJ9.2iDgRALderyIM_IcVFV7cAPF4zF9sJP5ijfBp9wtKkHmk7skMMKyNgY-0ppOwjz1kK73wMH_HgmNWfPCNz2vCw"
GROQ_KEY = "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"

def safe_i(v, d=0):
    try: return int(float(v)) if v is not None else d
    except: return d

def safe_f(v, d=0.0):
    try: return float(v) if v is not None else d
    except: return d

def run_turso(sqls):
    if isinstance(sqls, str): sqls = [sqls]
    url = f"{TURSO_URL}/v2/pipeline"
    hdrs = {"Authorization": f"Bearer {TURSO_TOKEN}", "Content-Type": "application/json"}
    reqs = [{"type": "execute", "stmt": {"sql": s}} for s in sqls] + [{"type": "close"}]
    try:
        r = requests.post(url, headers=hdrs, json={"requests": reqs}, timeout=10)
        res = r.json().get("results", [{}])[0].get("response", {}).get("result", {})
        cols = [c["name"] for c in res.get("cols", [])]
        return [{cols[i]: row[i].get("value") for i in range(len(cols))} for row in res.get("rows", [])]
    except: return []

def send_dispatch(head, body, tag="DIRECTIVE", org="High Command"):
    b = str(body)[:280].replace("'", "''")
    h = str(head)[:60].replace("'", "''")
    run_turso(f"INSERT INTO intelligence_dispatches VALUES ('DISP-{random.randint(1000,9999)}', datetime('now'), '{org}', '{tag}', '{h}', '{b}');")

# Init nodes if needed
run_turso([
    "ALTER TABLE regions ADD COLUMN garrison_strength INTEGER DEFAULT 30000;",
    "ALTER TABLE regions ADD COLUMN latitude REAL DEFAULT 50.0;",
    "ALTER TABLE regions ADD COLUMN longitude REAL DEFAULT 10.0;",
    "ALTER TABLE national_stockpiles ADD COLUMN munitions_tonnage REAL DEFAULT 45000.0;",
    "INSERT OR REPLACE INTO regions (region_id, name, owner_nation, terrain_type, is_demilitarized, garrison_strength, latitude, longitude) VALUES ('REG-BERLIN', 'Berlin-Brandenburg', 'GERMANY', 'URBAN', 0, 75000, 52.52, 13.40), ('REG-RUHR', 'Ruhr Valley', 'GERMANY', 'URBAN', 0, 25000, 51.45, 7.01), ('REG-RHINELAND', 'The Rhineland', 'GERMANY', 'PLAINS', 1, 0, 50.11, 7.50), ('REG-EASTPRUSSIA', 'East Prussia', 'GERMANY', 'PLAINS', 0, 15000, 54.71, 20.51), ('REG-AUSTRIA', 'Austria (Vienna)', 'AUSTRIA', 'HILLS', 0, 40000, 48.20, 16.37), ('REG-CZECH', 'Czechoslovakia', 'CZECHOSLOVAKIA', 'MOUNTAINS', 0, 80000, 50.07, 14.43), ('REG-PARIS', 'Paris (France)', 'FRANCE', 'URBAN', 0, 140000, 48.85, 2.35), ('REG-WARSAW', 'Warsaw (Poland)', 'POLAND', 'PLAINS', 0, 95000, 52.23, 21.01), ('REG-MOSCOW', 'Moscow (USSR)', 'USSR', 'URBAN', 0, 250000, 55.75, 37.61);"
])

def ask_groq(prompt):
    hdrs = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    for m in ["llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b"]:
        try:
            p = {"model": m, "messages": [{"role": "system", "content": "You are OKW General Staff 1933. Terse military tone."}, {"role": "user", "content": prompt}], "temperature": 0.3, "max_tokens": 400}
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=hdrs, json=p, timeout=10)
            if r.status_code == 200:
                t = r.json()["choices"][0]["message"]["content"]
                return t.split("</think>")[-1].strip() if "</think>" in t else t
        except: pass
    return "DISPATCH CARRIER DELAYED."

# --- HUD & SIDEBAR ---
men = safe_i((run_turso("SELECT SUM(garrison_strength) as t FROM regions WHERE owner_nation = 'GERMANY';") or [{}])[0].get("t"), 115000)
with st.sidebar:
    st.title("🎖️ High Command")
    st.metric("Total Troops", f"{men:,} men")
    if men > 100000: st.warning("⚠️ Versailles 100k troop limit breached!")

stock = (run_turso("SELECT * FROM national_stockpiles WHERE nation = 'GERMANY' LIMIT 1;") or [{}])[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Date", "1933 Sim")
c2.metric("Crude Oil", f"{safe_f(stock.get('crude_oil')):,.0f} t")
c3.metric("Steel", f"{safe_f(stock.get('high_grade_steel')):,.0f} t")
c4.metric("Munitions", f"{safe_f(stock.get('munitions_tonnage', 45000)):,.0f} t")
st.divider()

# --- TABS ---
t_map, t_war, t_ind, t_dec, t_inbox = st.tabs(["🗺️ Map", "⚔️ Conquest", "⚙️ Industry", "🏛️ Cabinet", "📥 Dispatches"])

with t_map:
    regs = run_turso("SELECT name, owner_nation, is_demilitarized, garrison_strength, latitude, longitude FROM regions;")
    cols = {"GERMANY": "#5c6b73", "FRANCE": "#1f77b4", "POLAND": "#e377c2", "USSR": "#d62728", "AUSTRIA": "#bcbd22", "CZECHOSLOVAKIA": "#2ca02c"}
    m_js = []
    for r in regs:
        lat, lon = safe_f(r.get("latitude"), 50.0), safe_f(r.get("longitude"), 10.0)
        c = "#e6a23c" if safe_i(r.get("is_demilitarized")) == 1 else cols.get(r.get("owner_nation"), "#999")
        txt = f"{r.get('name')} ({r.get('owner_nation')}) - Garrison: {safe_i(r.get('garrison_strength')):,}"
        m_js.append(f"L.circleMarker([{lat}, {lon}], {{radius: 11, fillColor: '{c}', color: '#fff', weight: 2, fillOpacity: 0.85}}).addTo(map).bindPopup('{txt}');")
    components.html(f"<html><head><link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'/><script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script><style>#map{{height:380px;border-radius:8px;background:#0b0e14;}}</style></head><body><div id='map'></div><script>var map=L.map('map').setView([51.5, 13], 4); L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map); {' '.join(m_js)}</script></body></html>", height=400)
    st.caption("Gray: Germany | Blue: France | Pink: Poland | Red: USSR | Gold: Austria | Orange: Demilitarized")

with t_war:
    r_list = run_turso("SELECT * FROM regions;")
    opts = {f"{r['name']} ({r['owner_nation']})": r for r in r_list}
    choice = st.selectbox("Select Target Region", list(opts.keys()))
    t_reg = opts[choice]
    demil = safe_i(t_reg.get("is_demilitarized")) == 1
    action = st.radio("Order Type", ["Remilitarize Buffer", "Maintain Watch"] if (t_reg["owner_nation"] == "GERMANY" and demil) else (["Reinforce Sector", "Stand Down"] if t_reg["owner_nation"] == "GERMANY" else ["Armed Blitzkrieg", "Diplomatic Annexation"]))
    commit = st.slider("Personnel to Commit", 5000, 150000, 30000, step=5000)
    if st.button("⚔️ Execute Operation", use_container_width=True):
        rid, rname, enemy_men = t_reg["region_id"], t_reg["name"], safe_i(t_reg.get("garrison_strength"), 30000)
        if "Remilitarize" in action:
            run_turso(f"UPDATE regions SET is_demilitarized = 0, garrison_strength = {commit} WHERE region_id = '{rid}';")
            send_dispatch("RHINELAND RECLAIMED", "Wehrmacht crossed the Rhine bridges. Sovereign military zone restored.", "VICTORY")
            st.success("Rhineland remilitarized successfully!")
            st.rerun()
        elif "Blitzkrieg" in action:
            a_loss = int(enemy_men * 0.28 * random.uniform(0.7, 1.2))
            d_loss = int(commit * 0.45 * random.uniform(0.8, 1.3))
            rem_a, rem_d = max(0, commit - a_loss), max(0, enemy_men - d_loss)
            if rem_a > rem_d:
                run_turso([f"UPDATE regions SET owner_nation = 'GERMANY', garrison_strength = {rem_a} WHERE region_id = '{rid}';", "UPDATE national_stockpiles SET crude_oil = MAX(0, crude_oil - 400), munitions_tonnage = MAX(0, munitions_tonnage - 300) WHERE nation = 'GERMANY';"])
                send_dispatch(f"{rname.upper()} SEIZED", f"Province fell. Losses: Wehrmacht {a_loss:,}, Enemy {d_loss:,}.", "CONQUEST")
                st.success(f"{rname} captured!")
                st.rerun()
            else:
                run_turso(f"UPDATE regions SET garrison_strength = {rem_d} WHERE region_id = '{rid}';")
                st.error(f"Offensive stalled. Suffered {a_loss:,} casualties.")
        elif "Annexation" in action:
            if random.random() > 0.4:
                run_turso(f"UPDATE regions SET owner_nation = 'GERMANY', garrison_strength = {commit + enemy_men} WHERE region_id = '{rid}';")
                send_dispatch(f"{rname.upper()} ANNEXED", f"{rname} absorbed into the Reich with zero casualties.", "INTEGRATION")
                st.success(f"{rname} annexed without resistance!")
                st.rerun()
            else: st.warning("Diplomatic ultimatum rejected by foreign cabinet.")

with t_ind:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Mobilize 15,000 Infantry**")
        st.caption("Consumes: 2,000t Steel, 150t Munitions")
        if st.button("Mobilize Divisions"):
            run_turso(["UPDATE national_stockpiles SET high_grade_steel = high_grade_steel - 2000, munitions_tonnage = munitions_tonnage - 150 WHERE nation = 'GERMANY';", "UPDATE regions SET garrison_strength = garrison_strength + 15000 WHERE region_id = 'REG-BERLIN';"])
            st.success("15,000 infantry mobilized!")
            st.rerun()
    with c2:
        st.markdown("**Fischer-Tropsch Fuel Synthesis**")
        st.caption("Consumes: 10,000t Coal -> Yields: 3,500t Fuel")
        if st.button("Synthesize Fuel"):
            run_turso("UPDATE national_stockpiles SET lignite_coal = lignite_coal - 10000, synthetic_fuel = synthetic_fuel + 3500, crude_oil = crude_oil + 1500 WHERE nation = 'GERMANY';")
            st.success("3,500t fuel produced!")
            st.rerun()

with t_dec:
    decree = st.text_area("Issue Directives to High Command", placeholder="e.g. Expand clandestine submarine construction...")
    if st.button("Transmit Directive"):
        if decree.strip():
            with st.spinner("General Staff processing..."):
                r = ask_groq(decree)
                send_dispatch("DECREE PROCESSED", r, "DIRECTIVE", "War Cabinet")
                st.info(r)

with t_inbox:
    for d in run_turso("SELECT * FROM intelligence_dispatches ORDER BY timestamp DESC LIMIT 6;"):
        st.info(f"[{d.get('classification')}] {d.get('headline')} — {d.get('origin')}\n\n{d.get('body')}")
    
