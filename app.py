import streamlit as st, requests, random, streamlit.components.v1 as components

st.set_page_config(page_title="WWII 1933 Grand Strategy", page_icon="🎖️", layout="wide")
TURSO_URL = "https://war-sim-db-trustycabin-create.aws-ap-south-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTQxNTIyNDgsImlkIjoiMDFhMWJiY2ItN2EwMS03MGFjLWJhNjgtMjRhZmRhYzU5MWUwIiwia2lkIjoiMzUzN2hMbnhCR0trV2hnbXdCN1Y4MnA2YTJrZ1JRN041eUk5TTRVc0NYUSIsInJpZCI6IjI3Njg3MGJhLTBiNWItNGQ4Mi1hYmEyLWYzNmFmYzQwNTkxNSJ9.2iDgRALderyIM_IcVFV7cAPF4zF9sJP5ijfBp9wtKkHmk7skMMKyNgY-0ppOwjz1kK73wMH_HgmNWfPCNz2vCw"

def si(v, d=0):
    try: return int(float(v)) if v is not None else d
    except: return d

def sf(v, d=0.0):
    try: return float(v) if v is not None else d
    except: return d

def db(sqls):
    if isinstance(sqls, str): sqls = [sqls]
    hdrs = {"Authorization": f"Bearer {TURSO_TOKEN}", "Content-Type": "application/json"}
    reqs = [{"type": "execute", "stmt": {"sql": s}} for s in sqls] + [{"type": "close"}]
    try:
        r = requests.post(f"{TURSO_URL}/v2/pipeline", headers=hdrs, json={"requests": reqs}, timeout=10)
        res = r.json().get("results", [{}])[0].get("response", {}).get("result", {})
        cols = [c["name"] for c in res.get("cols", [])]
        return [{cols[i]: row[i].get("value") for i in range(len(cols))} for row in res.get("rows", [])]
    except: return []

def log_news(head, body, tag="DIRECTIVE", org="High Command"):
    b, h = str(body)[:280].replace("'", "''"), str(head)[:60].replace("'", "''")
    db(f"INSERT INTO intelligence_dispatches VALUES ('DISP-{random.randint(1000,9999)}', datetime('now'), '{org}', '{tag}', '{h}', '{b}');")

db([
    "CREATE TABLE IF NOT EXISTS app_config (k TEXT PRIMARY KEY, v TEXT);",
    "ALTER TABLE regions ADD COLUMN garrison_strength INTEGER DEFAULT 30000;",
    "ALTER TABLE regions ADD COLUMN latitude REAL DEFAULT 50.0;",
    "ALTER TABLE regions ADD COLUMN longitude REAL DEFAULT 10.0;",
    "ALTER TABLE national_stockpiles ADD COLUMN munitions_tonnage REAL DEFAULT 45000.0;",
    "INSERT OR IGNORE INTO regions (region_id, name, owner_nation, terrain_type, is_demilitarized, garrison_strength, latitude, longitude) VALUES ('REG-BERLIN', 'Berlin-Brandenburg', 'GERMANY', 'URBAN', 0, 75000, 52.52, 13.40), ('REG-RUHR', 'Ruhr & Saarland', 'GERMANY', 'URBAN', 0, 25000, 51.45, 7.01), ('REG-RHINELAND', 'The Rhineland (DMZ)', 'GERMANY', 'PLAINS', 1, 0, 50.11, 7.50), ('REG-EASTPRUSSIA', 'East Prussia', 'GERMANY', 'PLAINS', 0, 15000, 54.71, 20.51), ('REG-AUSTRIA', 'Austria', 'AUSTRIA', 'HILLS', 0, 40000, 47.60, 14.10), ('REG-CZECH', 'Czechoslovakia', 'CZECHOSLOVAKIA', 'MOUNTAINS', 0, 80000, 49.80, 15.50), ('REG-PARIS', 'France', 'FRANCE', 'URBAN', 0, 140000, 46.80, 2.50), ('REG-WARSAW', 'Poland & Danzig Corridor', 'POLAND', 'PLAINS', 0, 95000, 52.10, 19.40), ('REG-MOSCOW', 'Soviet Union (USSR)', 'USSR', 'URBAN', 0, 250000, 55.75, 37.61);"
])

saved_k = (db("SELECT v FROM app_config WHERE k='groq_key';") or [{}])[0].get("v", "")

with st.sidebar:
    st.title("🎖️ High Command")
    new_k = st.text_input("Groq Key (Saved to Cloud DB)", value=saved_k, type="password", placeholder="Paste fresh gsk_ key...")
    if st.button("💾 Save Key Forever"):
        db(f"INSERT OR REPLACE INTO app_config VALUES ('groq_key', '{new_k.strip()}');")
        st.success("Key permanently saved in Turso DB!")
        st.rerun()
    men = si((db("SELECT SUM(garrison_strength) as t FROM regions WHERE owner_nation='GERMANY';") or [{}])[0].get("t"), 115000)
    st.metric("Wehrmacht Strength", f"{men:,} men")
    if men > 100000: st.warning("⚠️ Versailles 100k limit breached!")

def ask_groq(prompt, key):
    if not key: return "⚠️ Paste a fresh Groq key in the left sidebar and tap 'Save Key Forever'."
    hdrs = {"Authorization": f"Bearer {key.strip()}", "Content-Type": "application/json"}
    for m in ["llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b"]:
        try:
            p = {"model": m, "messages": [{"role": "system", "content": "You are OKW General Staff in 1933 Germany. Decompose orders into realistic military, industrial, and diplomatic actions. Terse dispatch tone."}, {"role": "user", "content": prompt}], "temperature": 0.3, "max_tokens": 450}
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=hdrs, json=p, timeout=12)
            if r.status_code == 200:
                t = r.json()["choices"][0]["message"]["content"]
                return t.split("</think>")[-1].strip() if "</think>" in t else t
            elif r.status_code == 401:
                return "❌ ERROR 401: Groq deactivated this key because it was posted on public GitHub. Create a new key at console.groq.com and save it in the sidebar!"
        except Exception as e: return f"Connection Error: {e}"
    return "DISPATCH ERROR."

stock = (db("SELECT * FROM national_stockpiles WHERE nation='GERMANY' LIMIT 1;") or [{}])[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Timeline", "1933 Interwar")
c2.metric("Crude Oil", f"{sf(stock.get('crude_oil')):,.0f} t")
c3.metric("Steel", f"{sf(stock.get('high_grade_steel')):,.0f} t")
c4.metric("Munitions", f"{sf(stock.get('munitions_tonnage', 45000)):,.0f} t")

t_map, t_war, t_ind, t_dec, t_inbox = st.tabs(["🗺️ 1933 Europe Map", "⚔️ Conquest", "⚙️ Industry", "🏛️ Cabinet", "📥 Dispatches"])

with t_map:
    regs = db("SELECT name, owner_nation, is_demilitarized, garrison_strength, latitude, longitude FROM regions;")
    cols = {"GERMANY": "#3d4849", "FRANCE": "#1b4f72", "POLAND": "#922b21", "USSR": "#78281f", "AUSTRIA": "#b7950b", "CZECHOSLOVAKIA": "#196f3d"}
    owners_map = {r["name"]: r["owner_nation"] for r in regs}
    m_js = []
    for r in regs:
        lat, lon = sf(r.get("latitude"), 50.0), sf(r.get("longitude"), 10.0)
        c = "#d35400" if si(r.get("is_demilitarized")) == 1 else cols.get(r.get("owner_nation"), "#555")
        label = f"<b>{r.get('name')}</b><br>Controlled by: {r.get('owner_nation')}<br>Troops: {si(r.get('garrison_strength')):,}"
        m_js.append(f"L.circleMarker([{lat},{lon}],{{radius:10,fillColor:'{c}',color:'#ffd700',weight:2,fillOpacity:0.95}}).addTo(map).bindPopup('{label}');")
    
    au_col = cols.get(owners_map.get("Austria", "AUSTRIA"), "#b7950b")
    cz_col = cols.get(owners_map.get("Czechoslovakia", "CZECHOSLOVAKIA"), "#196f3d")
    pl_col = cols.get(owners_map.get("Poland & Danzig Corridor", "POLAND"), "#922b21")
    fr_col = cols.get(owners_map.get("France", "FRANCE"), "#1b4f72")
    
    html = f"""<!DOCTYPE html><html><head><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>body{{margin:0;}} #map{{height:440px;width:100%;background:#1a1d20;border-radius:8px;}} .leaflet-tile-pane{{filter:sepia(25%) invert(90%) contrast(110%) hue-rotate(180deg);}}</style></head>
    <body><div id="map"></div><script>
    var map = L.map('map').setView([50.8, 14.5], 4);
    L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{maxZoom: 8, minZoom: 3}}).addTo(map);
    var cMap = {{'Germany':'#3d4849','Austria':'{au_col}','Czech Republic':'{cz_col}','Poland':'{pl_col}','France':'{fr_col}','Russia':'#78281f','Ukraine':'#78281f','Belarus':'#78281f'}};
    fetch('https://raw.githubusercontent.com/leakyMirror/map-of-europe/master/GeoJSON/europe.geojson').then(r=>r.json()).then(d=>{{
        L.geoJSON(d, {{style: function(f){{ var n=f.properties.NAME; return {{fillColor: cMap[n]||'#2c3e50', weight:1.5, color:'#111', fillOpacity:0.65}}; }}}}).addTo(map);
        {' '.join(m_js)}
    }}).catch(e=>{{ {' '.join(m_js)} }});
    </script></body></html>"""
    components.html(html, height=455)
    st.caption("🎖️ Dark Charcoal = Germany | Blue = France | Red = Poland & USSR | Gold = Austria | Green = Czechoslovakia | Orange Dot = Demilitarized Rhineland")

with t_war:
    r_list = db("SELECT * FROM regions;")
    opts = {f"{r['name']} ({r['owner_nation']})": r for r in r_list}
    t_reg = opts[st.selectbox("Select Strategic Target", list(opts.keys()))]
    demil = si(t_reg.get("is_demilitarized")) == 1
    act = st.radio("Operation", ["Remilitarize Rhineland", "Hold"] if (t_reg["owner_nation"]=="GERMANY" and demil) else (["Reinforce Garrison"] if t_reg["owner_nation"]=="GERMANY" else ["Launch Armed Blitzkrieg", "Diplomatic Annexation"]))
    commit = st.slider("Commit Forces (Men)", 5000, 150000, 35000, step=5000)
    if st.button("⚔️ EXECUTE MILITARY ORDER", use_container_width=True):
        rid, rname, emen = t_reg["region_id"], t_reg["name"], si(t_reg.get("garrison_strength"), 30000)
        if "Remilitarize" in act:
            db(f"UPDATE regions SET is_demilitarized=0, garrison_strength={commit} WHERE region_id='{rid}';")
            log_news("RHINELAND REMILITARIZED", "Wehrmacht battalions crossed the Rhine. Versailles buffer abolished.", "VICTORY")
            st.success("Rhineland remilitarized! Check the map.")
            st.rerun()
        elif "Blitzkrieg" in act:
            aloss, dloss = int(emen * 0.25 * random.uniform(0.7, 1.2)), int(commit * 0.45 * random.uniform(0.8, 1.3))
            if (commit - aloss) > (emen - dloss):
                db([f"UPDATE regions SET owner_nation='GERMANY', garrison_strength={max(5000, commit-aloss)} WHERE region_id='{rid}';", "UPDATE national_stockpiles SET crude_oil=MAX(0,crude_oil-500), munitions_tonnage=MAX(0,munitions_tonnage-350) WHERE nation='GERMANY';"])
                log_news(f"{rname.upper()} CONQUERED", f"Sector captured! Losses: Germany {aloss:,}, Defender {dloss:,}.", "CONQUEST")
                st.success(f"Victory! {rname} annexed into the Reich! Map territory updated.")
                st.rerun()
            else:
                db(f"UPDATE regions SET garrison_strength={max(5000, emen-dloss)} WHERE region_id='{rid}';")
                st.error(f"Assault repulsed! Suffered {aloss:,} casualties.")
        elif "Annexation" in act:
            if random.random() > 0.35:
                db(f"UPDATE regions SET owner_nation='GERMANY', garrison_strength={commit+emen} WHERE region_id='{rid}';")
                log_news(f"{rname.upper()} ANNEXED", f"{rname} capitulated to diplomatic ultimatum.", "ANNEXATION")
                st.success(f"{rname} peacefully annexed! Map borders updated.")
                st.rerun()
            else: st.warning("Foreign government rejected ultimatum.")

with t_ind:
    c1, c2 = st.columns(2)
    if c1.button("➕ Mobilize 15,000 Infantry (2,000t Steel)"):
        db(["UPDATE national_stockpiles SET high_grade_steel=high_grade_steel-2000, munitions_tonnage=munitions_tonnage-150 WHERE nation='GERMANY';", "UPDATE regions SET garrison_strength=garrison_strength+15000 WHERE region_id='REG-BERLIN';"])
        st.rerun()
    if c2.button("⛽ Synthesize 3,500t Fuel (10,000t Coal)"):
        db("UPDATE national_stockpiles SET lignite_coal=lignite_coal-10000, crude_oil=crude_oil+3500 WHERE nation='GERMANY';")
        st.rerun()

with t_dec:
    dec = st.text_area("Directive to OKW High Command", placeholder="e.g. Order General Staff to prepare Fall Otto (invasion plan for Austria)...")
    if st.button("Transmit Directive") and dec.strip():
        with st.spinner("Contacting General Staff..."):
            ans = ask_groq(dec, saved_k)
            if not ans.startswith(("⚠️", "❌", "Connection")): log_news("OKW DIRECTIVE", ans)
            st.info(ans)

with t_inbox:
    for d in db("SELECT * FROM intelligence_dispatches ORDER BY timestamp DESC LIMIT 8;"):
        st.info(f"[{d.get('classification')}] {d.get('headline')} — {d.get('origin')}\n\n{d.get('body')}")
    
