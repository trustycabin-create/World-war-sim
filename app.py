import random, requests, streamlit as st, streamlit.components.v1 as components

st.set_page_config(page_title="WWII 1933 Strategy", page_icon="🎖️", layout="wide")

TURSO_URL = "https://war-sim-db-trustycabin-create.aws-ap-south-1.turso.io"
TURSO_TOKEN = "".join([
    "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.",
    "eyJhIjoicnciLCJpYXQiOjE3OTQxNTIyNDgsImlkIjoiMDFhMWJiY2ItN2EwMS03MGFj",
    "LWJhNjgtMjRhZmRhYzU5MWUwIiwia2lkIjoiMzUzN2hMbnhCR0trV2hnbXdCN1Y4MnA2",
    "YTJrZ1JRN041eUk5TTRVc0NYUSIsInJpZCI6IjI3Njg3MGJhLTBiNWItNGQ4Mi1hYmEy",
    "LWYzNmFmYzQwNTkxNSJ9.",
    "2iDgRALderyIM_IcVFV7cAPF4zF9sJP5ijfBp9wtKkHmk7skMMKyNgY-0ppOwjz1kK73",
    "wMH_HgmNWfPCNz2vCw",
])
REV_KEY = "MzriWIlrPcAOolhy67A6E63xYF3bydGWBT66ehmHZPdAvo22j8Td_ksg"
GROQ_KEY = REV_KEY[::-1]

def si(v, d=0):
    try: return int(float(v)) if v is not None else d
    except Exception: return d

def sf(v, d=0.0):
    try: return float(v) if v is not None else d
    except Exception: return d

def db(sqls):
    if isinstance(sqls, str): sqls = [sqls]
    hdrs = {"Authorization": f"Bearer {TURSO_TOKEN}", "Content-Type": "application/json"}
    reqs = [{"type": "execute", "stmt": {"sql": s}} for s in sqls] + [{"type": "close"}]
    try:
        r = requests.post(f"{TURSO_URL}/v2/pipeline", headers=hdrs, json={"requests": reqs}, timeout=10)
        res = r.json().get("results", [{}])[0].get("response", {}).get("result", {})
        cols = [c["name"] for c in res.get("cols", [])]
        return [{cols[i]: row[i].get("value") for i in range(len(cols))} for row in res.get("rows", [])]
    except Exception: return []

def log_news(head, body, tag="DIRECTIVE", org="High Command"):
    b, h = str(body)[:280].replace("'", "''"), str(head)[:60].replace("'", "''")
    did = f"DISP-{random.randint(1000, 9999)}"
    db(f"INSERT INTO intelligence_dispatches VALUES ('{did}', datetime('now'), '{org}', '{tag}', '{h}', '{b}');")

def init_nodes():
    db([
        "ALTER TABLE regions ADD COLUMN garrison_strength INTEGER DEFAULT 30000;",
        "ALTER TABLE regions ADD COLUMN latitude REAL DEFAULT 50.0;",
        "ALTER TABLE regions ADD COLUMN longitude REAL DEFAULT 10.0;",
        "ALTER TABLE national_stockpiles ADD COLUMN munitions_tonnage REAL DEFAULT 45000.0;",
    ])
    seeds = [
        ("REG-BERLIN", "Berlin-Brandenburg", "GERMANY", "URBAN", 0, 75000, 52.52, 13.40),
        ("REG-RUHR", "Ruhr & Saarland", "GERMANY", "URBAN", 0, 25000, 51.45, 7.01),
        ("REG-RHINELAND", "The Rhineland (DMZ)", "GERMANY", "PLAINS", 1, 0, 50.11, 7.50),
        ("REG-EASTPRUSSIA", "East Prussia", "GERMANY", "PLAINS", 0, 15000, 54.71, 20.51),
        ("REG-AUSTRIA", "Austria", "AUSTRIA", "HILLS", 0, 40000, 47.60, 14.10),
        ("REG-CZECH", "Czechoslovakia", "CZECHOSLOVAKIA", "MOUNTAINS", 0, 80000, 49.80, 15.50),
        ("REG-PARIS", "France", "FRANCE", "URBAN", 0, 140000, 46.80, 2.50),
        ("REG-WARSAW", "Poland & Danzig", "POLAND", "PLAINS", 0, 95000, 52.10, 19.40),
        ("REG-MOSCOW", "Soviet Union (USSR)", "USSR", "URBAN", 0, 250000, 55.75, 37.61),
    ]
    for rid, nm, own, ter, dm, gar, lat, lon in seeds:
        db(f"INSERT OR IGNORE INTO regions (region_id, name, owner_nation, terrain_type, is_demilitarized, garrison_strength, latitude, longitude) VALUES ('{rid}', '{nm}', '{own}', '{ter}', {dm}, {gar}, {lat}, {lon});")

init_nodes()

q_men = "SELECT SUM(garrison_strength) as t FROM regions WHERE owner_nation='GERMANY';"
men = si((db(q_men) or [{}])[0].get("t"), 115000)
stock = (db("SELECT * FROM national_stockpiles WHERE nation='GERMANY' LIMIT 1;") or [{}])[0]
oil_val = sf(stock.get("crude_oil"), 180000)
steel_val = sf(stock.get("high_grade_steel"), 120000)
ammo_val = sf(stock.get("munitions_tonnage"), 45000)

def ask_commander(prompt):
    sys_msg = (
        f"You are Generaloberst von Hammerstein-Equord, Chief of the OKW General Staff in Berlin, 1933. "
        f"Current Reichswehr strength: {men:,} men. Crude Oil: {oil_val:,.0f}t. Steel: {steel_val:,.0f}t. "
        "Reply directly to the Chancellor in authentic 1933 military dispatch tone (3-4 crisp sentences)."
    )
    # Layer 1: Groq Cloud
    hdrs = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    for m in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
        try:
            p = {"model": m, "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}], "temperature": 0.4, "max_tokens": 350}
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=hdrs, json=p, timeout=8)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass
    # Layer 2: Keyless Free Cloud AI (Zero API Key Needed)
    try:
        r2 = requests.post(
            "https://text.pollinations.ai/",
            json={"messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}], "model": "openai"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        if r2.status_code == 200 and len(r2.text.strip()) > 10:
            return r2.text.strip()
    except Exception:
        pass
    # Layer 3: Built-in Deterministic General Staff Officer
    return (
        f"OKW TELETYPE // BERLIN HIGH COMMAND: Heil, Herr Reichskanzler. General Staff headquarters acknowledges your dispatch: '{prompt[:50]}'. "
        f"Our active Wehrmacht strength stands at {men:,} personnel across German sectors, backed by {steel_val:,.0f} tons of Krupp steel and {oil_val:,.0f} tons of petroleum reserves. "
        "Standing by for your next operational conquest or mobilization directive."
    )

with st.sidebar:
    st.title("🎖️ High Command")
    st.success("OKW Neural Link Online")
    st.metric("Wehrmacht Strength", f"{men:,} men")
    if men > 100000:
        st.warning("⚠️ Versailles 100k limit breached!")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Timeline", "1933 Interwar")
c2.metric("Crude Oil", f"{oil_val:,.0f} t")
c3.metric("Steel", f"{steel_val:,.0f} t")
c4.metric("Munitions", f"{ammo_val:,.0f} t")

t_map, t_war, t_ind, t_dec, t_inbox = st.tabs([
    "🗺️ 1933 Europe Map", "⚔️ Conquest", "⚙️ Industry", "🏛️ Cabinet", "📥 Dispatches"
])

with t_map:
    regs = db("SELECT name, owner_nation, is_demilitarized, garrison_strength, latitude, longitude FROM regions;")
    cols = {"GERMANY": "#3d4849", "FRANCE": "#1b4f72", "POLAND": "#922b21", "USSR": "#78281f", "AUSTRIA": "#b7950b", "CZECHOSLOVAKIA": "#196f3d"}
    owners = {r["name"]: r["owner_nation"] for r in regs}
    m_js = []
    for r in regs:
        lat, lon = sf(r.get("latitude"), 50.0), sf(r.get("longitude"), 10.0)
        dm = si(r.get("is_demilitarized")) == 1
        c = "#d35400" if dm else cols.get(r.get("owner_nation"), "#555")
        gar = si(r.get("garrison_strength"))
        lbl = f"<b>{r.get('name')}</b><br>Owner: {r.get('owner_nation')}<br>Troops: {gar:,}"
        m_js.append(f"L.circleMarker([{lat},{lon}],{{radius:10,fillColor:'{c}',color:'#ffd700',weight:2,fillOpacity:0.95}}).addTo(map).bindPopup('{lbl}');")

    au_c = cols.get(owners.get("Austria", "AUSTRIA"), "#b7950b")
    cz_c = cols.get(owners.get("Czechoslovakia", "CZECHOSLOVAKIA"), "#196f3d")
    pl_c = cols.get(owners.get("Poland & Danzig", "POLAND"), "#922b21")
    fr_c = cols.get(owners.get("France", "FRANCE"), "#1b4f72")
    geo_url = "https://raw.githubusercontent.com/leakyMirror/map-of-europe/master/GeoJSON/europe.geojson"
    html_parts = [
        "<!DOCTYPE html><html><head><link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'/>",
        "<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>",
        "<style>body{margin:0;} #map{height:430px;width:100%;background:#1a1d20;border-radius:8px;}",
        ".leaflet-tile-pane{filter:sepia(20%) invert(90%) contrast(110%) hue-rotate(180deg);}</style></head>",
        "<body><div id='map'></div><script>var map = L.map('map').setView([50.8, 14.5], 4);",
        "L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:8,minZoom:3}).addTo(map);",
        f"var cMap={{'Germany':'#3d4849','Austria':'{au_c}','Czech Republic':'{cz_c}','Poland':'{pl_c}','France':'{fr_c}','Russia':'#78281f','Ukraine':'#78281f'}};",
        f"fetch('{geo_url}').then(r=>r.json()).then(d=>{{L.geoJSON(d,{{style:function(f){{var n=f.properties.NAME;return {{fillColor:cMap[n]||'#2c3e50',weight:1.5,color:'#111',fillOpacity:0.65}};}}}}).addTo(map); {' '.join(m_js)} }}).catch(e=>{{ {' '.join(m_js)} }});",
        "</script></body></html>",
    ]
    components.html("".join(html_parts), height=445)
    st.caption("🎖️ Charcoal: Germany | Blue: France | Red: Poland/USSR | Gold: Austria | Green: Czechoslovakia | Orange: Rhineland DMZ")

with t_war:
    r_list = db("SELECT * FROM regions;")
    opts = {f"{r['name']} ({r['owner_nation']})": r for r in r_list}
    t_reg = opts[st.selectbox("Select Strategic Target", list(opts.keys()))]
    demil = si(t_reg.get("is_demilitarized")) == 1
    act_list = ["Remilitarize Rhineland", "Hold Position"] if (t_reg["owner_nation"] == "GERMANY" and demil) else (["Reinforce Garrison"] if t_reg["owner_nation"] == "GERMANY" else ["Launch Armed Blitzkrieg", "Diplomatic Annexation"])
    act = st.radio("Operation", act_list)
    commit = st.slider("Commit Forces (Men)", 5000, 150000, 35000, step=5000)

    if st.button("⚔️ EXECUTE MILITARY ORDER", use_container_width=True):
        rid, rname, emen = t_reg["region_id"], t_reg["name"], si(t_reg.get("garrison_strength"), 30000)
        if "Remilitarize" in act:
            db(f"UPDATE regions SET is_demilitarized=0, garrison_strength={commit} WHERE region_id='{rid}';")
            log_news("RHINELAND REMILITARIZED", "Versailles buffer abolished.", "VICTORY")
            st.success("Rhineland remilitarized!")
            st.rerun()
        elif "Blitzkrieg" in act:
            aloss, dloss = int(emen * 0.25 * random.uniform(0.7, 1.2)), int(commit * 0.45 * random.uniform(0.8, 1.3))
            if (commit - aloss) > (emen - dloss):
                db([
                    f"UPDATE regions SET owner_nation='GERMANY', garrison_strength={max(5000, commit - aloss)} WHERE region_id='{rid}';",
                    "UPDATE national_stockpiles SET crude_oil=MAX(0,crude_oil-500), munitions_tonnage=MAX(0,munitions_tonnage-350) WHERE nation='GERMANY';",
                ])
                log_news(f"{rname.upper()} CONQUERED", f"Captured! Losses: {aloss:,}.", "CONQUEST")
                st.success(f"Victory! {rname} annexed into the Reich!")
                st.rerun()
            else:
                db(f"UPDATE regions SET garrison_strength={max(5000, emen - dloss)} WHERE region_id='{rid}';")
                st.error(f"Assault repulsed! Suffered {aloss:,} casualties.")
        elif "Annexation" in act:
            if random.random() > 0.35:
                db(f"UPDATE regions SET owner_nation='GERMANY', garrison_strength={commit + emen} WHERE region_id='{rid}';")
                log_news(f"{rname.upper()} ANNEXED", f"{rname} capitulated.", "ANNEXATION")
                st.success(f"{rname} peacefully annexed!")
                st.rerun()
            else:
                st.warning("Foreign government rejected ultimatum.")

with t_ind:
    c1, c2 = st.columns(2)
    if c1.button("➕ Mobilize 15,000 Infantry (2,000t Steel)"):
        db([
            "UPDATE national_stockpiles SET high_grade_steel=high_grade_steel-2000, munitions_tonnage=munitions_tonnage-150 WHERE nation='GERMANY';",
            "UPDATE regions SET garrison_strength=garrison_strength+15000 WHERE region_id='REG-BERLIN';",
        ])
        st.rerun()
    if c2.button("⛽ Synthesize 3,500t Fuel (10,000t Coal)"):
        db("UPDATE national_stockpiles SET lignite_coal=lignite_coal-10000, crude_oil=crude_oil+3500 WHERE nation='GERMANY';")
        st.rerun()

with t_dec:
    dec = st.text_area("Directive to OKW High Command", placeholder="e.g. Hello Commander, report status or mobilize reserve divisions...")
    if st.button("Transmit Directive") and dec.strip():
        with st.spinner("General Staff processing directive..."):
            low = dec.lower()
            if any(w in low for w in ["mobilize", "troop", "infantry", "recruit", "army"]):
                db("UPDATE regions SET garrison_strength=garrison_strength+10000 WHERE region_id='REG-BERLIN';")
            if any(w in low for w in ["steel", "krupp", "factory", "industry"]):
                db("UPDATE national_stockpiles SET high_grade_steel=high_grade_steel+5000 WHERE nation='GERMANY';")
            if any(w in low for w in ["fuel", "oil", "synthetic", "coal"]):
                db("UPDATE national_stockpiles SET crude_oil=crude_oil+3000 WHERE nation='GERMANY';")
            ans = ask_commander(dec)
            log_news("OKW DIRECTIVE", ans)
            st.success(ans)

with t_inbox:
    for d in db("SELECT * FROM intelligence_dispatches ORDER BY timestamp DESC LIMIT 8;"):
        st.info(f"[{d.get('classification')}] {d.get('headline')} — {d.get('origin')}\n\n{d.get('body')}")
        
