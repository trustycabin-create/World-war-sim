from datetime import datetime
import json
import numpy as np
import requests
import streamlit as st

# --- STREAMLIT MOBILE PWA CONFIG ---
st.set_page_config(
    page_title="WWII Grand Strategy 1933",
    page_icon="🎖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for crisp military teletype dashboard
st.markdown(
    """
    <style>
    .main { background-color: #0e1117; }
    .stTextInput > div > div > input { background-color: #1a1c24; color: #e0e0e0; font-family: monospace; }
    .teletype-box {
        background-color: #161a23;
        border-left: 4px solid #b8860b;
        padding: 12px;
        margin-bottom: 10px;
        font-family: monospace;
        font-size: 0.88rem;
        color: #d1d5db;
    }
    .metric-card {
        background: #1e222d;
        border-radius: 4px;
        padding: 8px 12px;
        border: 1px solid #2d3342;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- CONFIG & CREDENTIALS ---
TURSO_DB_URL = "https://war-sim-db-trustycabin-create.aws-ap-south-1.turso.io"
TURSO_AUTH_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTQxNTIyNDgsImlkIjoiMDFhMWJiY2ItN2EwMS03MGFjLWJhNjgtMjRhZmRhYzU5MWUwIiwia2lkIjoiMzUzN2hMbnhCR0trV2hnbXdCN1Y4MnA2YTJrZ1JRN041eUk5TTRVc0NYUSIsInJpZCI6IjI3Njg3MGJhLTBiNWItNGQ4Mi1hYmEyLWYzNmFmYzQwNTkxNSJ9.2iDgRALderyIM_IcVFV7cAPF4zF9sJP5ijfBp9wtKkHmk7skMMKyNgY-0ppOwjz1kK73wMH_HgmNWfPCNz2vCw"

# --- TURSO HTTP PIPELINE CLIENT ---
def query_turso(sql: str, params: list = None):
    url = f"{TURSO_DB_URL}/v2/pipeline"
    headers = {
        "Authorization": f"Bearer {TURSO_AUTH_TOKEN}",
        "Content-Type": "application/json",
    }
    stmt = {"sql": sql}
    if params:
        stmt["args"] = [{"type": "text", "value": str(p)} for p in params]

    payload = {"requests": [{"type": "execute", "stmt": stmt}, {"type": "close"}]}
    res = requests.post(url, headers=headers, json=payload, timeout=10)
    if res.status_code != 200:
        return []
    data = res.json()
    result = data.get("results", [{}])[0].get("response", {}).get("result", {})
    cols = [col["name"] for col in result.get("cols", [])]
    rows = []
    for r in result.get("rows", []):
        row_dict = {}
        for idx, col in enumerate(cols):
            row_dict[col] = r[idx].get("value")
        rows.append(row_dict)
    return rows

def execute_turso_batch(statements: list):
    url = f"{TURSO_DB_URL}/v2/pipeline"
    headers = {
        "Authorization": f"Bearer {TURSO_AUTH_TOKEN}",
        "Content-Type": "application/json",
    }
    reqs = [{"type": "execute", "stmt": {"sql": s}} for s in statements]
    reqs.append({"type": "close"})
    res = requests.post(url, headers=headers, json={"requests": reqs}, timeout=10)
    return res.status_code == 200

# Auto-initialize baseline tables if fresh database
def ensure_db_init():
    try:
        res = query_turso("SELECT campaign_id FROM campaigns LIMIT 1;")
        if not res:
            from init_db import initialize_1933_world
            initialize_1933_world()
    except Exception:
        pass

ensure_db_init()

# --- DELTA TIME ENGINE ---
def run_delta_simulation():
    camp = query_turso("SELECT * FROM campaigns WHERE campaign_id = 'CMP-1933' LIMIT 1;")
    if not camp:
        return
    camp = camp[0]
    time_mult = float(camp.get("time_multiplier", 1.0))
    last_real_str = camp.get("last_real_timestamp")
    last_game_str = camp.get("game_timestamp")

    now_real = datetime.utcnow()
    try:
        last_real = datetime.strptime(last_real_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        last_real = now_real

    delta_real_seconds = max(0, (now_real - last_real).total_seconds())
    sim_seconds_elapsed = delta_real_seconds * time_mult
    sim_hours_elapsed = sim_seconds_elapsed / 3600.0

    if sim_hours_elapsed > 0.05:  # Tick if more than 3 simulated minutes passed
        # Advance stockpiles (coal conversion, consumption)
        drain_oil = sim_hours_elapsed * 1.5
        drain_coal = sim_hours_elapsed * 45.0

        update_sqls = [
            f"""
            UPDATE national_stockpiles 
            SET crude_oil = MAX(0, crude_oil - {drain_oil}),
                lignite_coal = MAX(0, lignite_coal - {drain_coal})
            WHERE nation = 'GERMANY';
            """,
            f"""
            UPDATE campaigns 
            SET last_real_timestamp = '{now_real.strftime("%Y-%m-%d %H:%M:%S")}'
            WHERE campaign_id = 'CMP-1933';
            """,
        ]
        execute_turso_batch(update_sqls)

run_delta_simulation()

# --- DUAL-LLM FALLBACK RUNTIME (GROQ) ---
def call_groq_llm(groq_key: str, system_prompt: str, user_prompt: str):
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json",
    }
    # 1. Primary Model: Llama-3.3-70B Versatile
    primary_payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 700,
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=primary_payload, timeout=12)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except Exception:
        pass

    # 2. DeepSeek-R1 Fallback Pipeline
    fallback_payload = {
        "model": "deepseek-r1-distill-llama-70b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 1000,
    }
    try:
        rf = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=fallback_payload, timeout=18)
        if rf.status_code == 200:
            content = rf.json()["choices"][0]["message"]["content"]
            # Strip reasoning tokens if present
            if "</think>" in content:
                content = content.split("</think>")[-1].strip()
            return content
    except Exception:
        pass

    return "TELETYPE NOTICE // DISPATCH CARRIER SEVERED // COURIER DELAY IN EFFECT."

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.title("🎖️ High Command")
    groq_api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    
    st.subheader("Clock & Ratio Engine")
    time_mode = st.radio("Time Multiplier Mode", ["1:1 Real-Time (Long Struggle)", "360x Fast Blitz (6h / min)"])
    new_mult = 1.0 if "1:1" in time_mode else 360.0
    if st.button("Apply Multiplier"):
        execute_turso_batch([f"UPDATE campaigns SET time_multiplier = {new_mult} WHERE campaign_id = 'CMP-1933';"])
        st.success(f"Ratio set to {new_mult}x")
        st.rerun()

# --- TOP HUD METRICS ---
stock = query_turso("SELECT * FROM national_stockpiles WHERE nation = 'GERMANY' LIMIT 1;")
camp_data = query_turso("SELECT * FROM campaigns WHERE campaign_id = 'CMP-1933' LIMIT 1;")

c1, c2, c3, c4 = st.columns(4)
if stock and camp_data:
    s = stock[0]
    c = camp_data[0]
    c1.metric("Date (Sim)", "30 Jan 1933")
    c2.metric("Crude Oil", f"{float(s.get('crude_oil', 0)):,.0f} t")
    c3.metric("High-Grade Steel", f"{float(s.get('high_grade_steel', 0)):,.0f} t")
    c4.metric("Chromium", f"{float(s.get('chromium', 0)):,.1f} t")

st.divider()

# --- MAIN DASHBOARD TABS ---
tab_inbox, tab_cabinet, tab_map, tab_industry = st.tabs([
    "📥 Intelligence Inbox", 
    "🏛️ War Cabinet Hub", 
    "🗺️ Operational Sectors", 
    "⚙️ Metallurgical Stockpiles"
])

# 1. INTELLIGENCE INBOX
with tab_inbox:
    st.subheader("Situational Dispatches & Reconnaissance Feed")
    dispatches = query_turso("SELECT * FROM intelligence_dispatches ORDER BY dispatch_id DESC LIMIT 8;")
    for
  
