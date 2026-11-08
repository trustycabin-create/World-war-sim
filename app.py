from datetime import datetime
import json
import requests
import streamlit as st

# Streamlit Page Setup
st.set_page_config(
    page_title="WWII Grand Strategy 1933",
    page_icon="🎖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Turso Cloud Credentials
TURSO_DB_URL = "https://war-sim-db-trustycabin-create.aws-ap-south-1.turso.io"
TURSO_AUTH_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTQxNTIyNDgsImlkIjoiMDFhMWJiY2ItN2EwMS03MGFjLWJhNjgtMjRhZmRhYzU5MWUwIiwia2lkIjoiMzUzN2hMbnhCR0trV2hnbXdCN1Y4MnA2YTJrZ1JRN041eUk5TTRVc0NYUSIsInJpZCI6IjI3Njg3MGJhLTBiNWItNGQ4Mi1hYmEyLWYzNmFmYzQwNTkxNSJ9.2iDgRALderyIM_IcVFV7cAPF4zF9sJP5ijfBp9wtKkHmk7skMMKyNgY-0ppOwjz1kK73wMH_HgmNWfPCNz2vCw"


# Turso HTTP Pipeline
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
        result = (
            data.get("results", [{}])[0].get("response", {}).get("result", {})
        )
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
        res = requests.post(
            url, headers=headers, json={"requests": reqs}, timeout=10
        )
        return res.status_code == 200
    except Exception:
        return False


# Auto-initialize baseline tables if fresh
def ensure_db_init():
    try:
        res = query_turso("SELECT campaign_id FROM campaigns LIMIT 1;")
        if not res:
            from init_db import initialize_1933_world

            initialize_1933_world()
    except Exception:
        pass


ensure_db_init()


# Groq Dual-LLM Pipeline
def call_groq_llm(groq_key: str, system_prompt: str, user_prompt: str):
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json",
    }
    payload_primary = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 700,
    }
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload_primary,
            timeout=12,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except Exception:
        pass

    payload_fallback = {
        "model": "deepseek-r1-distill-llama-70b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 1000,
    }
    try:
        rf = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload_fallback,
            timeout=18,
        )
        if rf.status_code == 200:
            content = rf.json()["choices"][0]["message"]["content"]
            if "</think>" in content:
                content = content.split("</think>")[-1].strip()
            return content
    except Exception:
        pass
    return "TELETYPE NOTICE // DISPATCH CARRIER SEVERED // COURIER DELAY IN EFFECT."


# Sidebar Controls
with st.sidebar:
    st.title("🎖️ High Command")
    groq_api_key = st.text_input(
        "Groq API Key", type="password", placeholder="gsk_..."
    )
    time_mode = st.radio(
        "Clock Speed", ["1:1 Real-Time (Long Struggle)", "360x Fast Blitz"]
    )
    new_mult = 1.0 if "1:1" in time_mode else 360.0
    if st.button("Apply Speed"):
        execute_turso_batch([
            f"UPDATE campaigns SET time_multiplier = {new_mult} WHERE"
            " campaign_id = 'CMP-1933';"
        ])
        st.success(f"Speed set to {new_mult}x")
        st.rerun()

# Top HUD Metrics
stock = query_turso(
    "SELECT * FROM national_stockpiles WHERE nation = 'GERMANY' LIMIT 1;"
)
c1, c2, c3, c4 = st.columns(4)
if stock:
    s = stock[0]
    c1.metric("Date", "30 Jan 1933")
    c2.metric("Crude Oil", f"{float(s.get('crude_oil', 0)):,.0f} t")
    c3.metric("Steel", f"{float(s.get('high_grade_steel', 0)):,.0f} t")
    c4.metric("Chromium", f"{float(s.get('chromium', 0)):,.1f} t")

st.divider()

# Command Tabs
tab_inbox, tab_cabinet, tab_map, tab_industry = st.tabs([
    "📥 Intelligence Inbox",
    "🏛️ War Cabinet Hub",
    "🗺️ Operational Sectors",
    "⚙️ Metallurgical Stockpiles",
])

with tab_inbox:
    st.subheader("Situational Dispatches & Reconnaissance Feed")
    dispatches = query_turso(
        "SELECT * FROM intelligence_dispatches ORDER BY dispatch_id DESC"
        " LIMIT 8;"
    )
    for d in dispatches:
        st.info(
            f"[{d.get('classification')}] {d.get('headline')} —"
            f" {d.get('origin')}\n\n{d.get('body')}"
        )

with tab_cabinet:
    st.subheader("Issue Micro or Macro Decrees")
    user_decree = st.text_area(
        "Decree to High Command",
        placeholder=(
            "e.g. Order Krupp to redesign all standard 7.92mm cartridges with"
            " tungsten-carbide cores..."
        ),
    )
    if st.button("Transmit Directive", use_container_width=True):
        if not groq_api_key:
            st.error("Please enter your Groq API Key in the left sidebar first.")
        elif not user_decree.strip():
            st.warning("Please enter a directive.")
        else:
            with st.spinner(
                "Compiling order through General Staff reality validation..."
            ):
                sys_prompt = (
                    "You are the Oberkommando der Wehrmacht (OKW) General Staff"
                    " in 1933. Decompose user decree into logistical,"
                    " metallurgical, and geopolitical consequences. Terse"
                    " military dispatch tone."
                )
                response_text = call_groq_llm(
                    groq_api_key, sys_prompt, user_decree
                )
                dispatch_id = f"DISP-{datetime.utcnow().strftime('%M%S')}"
                clean_txt = response_text[:350].replace("'", "''")
                log_sql = (
                    "INSERT INTO intelligence_dispatches (dispatch_id,"
                    " timestamp, origin, classification, headline, body) VALUES"
                    f" ('{dispatch_id}', datetime('now'), 'War Cabinet',"
                    " 'DECREE-ACK', 'OPERATIONAL DIRECTIVE RECORDED',"
                    f" '{clean_txt}');"
                )
                execute_turso_batch([log_sql])
                st.success(response_text)

with tab_map:
    st.subheader("European Strategic Map Nodes (1933 Borders)")
    regions = query_turso(
        "SELECT region_id, name, owner_nation, terrain_type, rail_gauge,"
        " soil_moisture, is_demilitarized FROM regions;"
    )
    col_a, col_b = st.columns(2)
    for idx, r in enumerate(regions):
        target_col = col_a if idx % 2 == 0 else col_b
        demil = (
            "⚠️ DEMILITARIZED ZONE"
            if int(r.get("is_demilitarized", 0)) == 1
            else "ACTIVE MILITARY SECTOR"
        )
        with target_col:
            st.markdown(
                f"**{r.get('name')}** ({r.get('owner_nation')})  \n*{demil}* "
                f" \nTerrain: {r.get('terrain_type')} | Moisture:"
                f" {float(r.get('soil_moisture', 0.2)):.2f} | Rail:"
                f" {r.get('rail_gauge')}"
            )

with tab_industry:
    st.subheader("National Armaments & Chemical Balance")
    if stock:
        s = stock[0]
        i1, i2 = st.columns(2)
        with i1:
            st.write(
                f"**Crude Petroleum:** {float(s.get('crude_oil', 0)):,.1f} tons"
            )
            st.write(
                f"**Synthetic Fuel:** {float(s.get('synthetic_fuel', 0)):,.1f}"
                " tons"
            )
            st.write(
                f"**Lignite Coal:** {float(s.get('lignite_coal', 0)):,.1f} tons"
            )
            st.write(
                "**High-Grade Steel:**"
                f" {float(s.get('high_grade_steel', 0)):,.1f} tons"
            )
        with i2:
            st.write(
                f"**Chromium Alloy:** {float(s.get('chromium', 0)):,.1f} tons"
            )
            st.write(
                f"**Manganese Alloy:** {float(s.get('manganese', 0)):,.1f} tons"
            )
            st.write(
                f"**Tungsten (Wolfram):** {float(s.get('tungsten', 0)):,.1f}"
                " tons"
            )
            st.write(
                f"**Synthetic Rubber:** {float(s.get('rubber', 0)):,.1f} tons"
            )
            
