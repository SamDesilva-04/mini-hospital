import html

import pandas as pd
import streamlit as st

import agents
import db

st.set_page_config(page_title="Mini Hospital", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")
st.session_state.setdefault("dark", True)
st.session_state.setdefault("hist", [])

# ---------- theme tokens ----------
THEMES = {
    "dark": dict(bg="#0d1520", card="#141f2e", border="#25354a", text="#e8eef6",
                 muted="#8ea0b8", accent="#3dd6c3", onaccent="#06201c"),
    "light": dict(bg="#f2f5f8", card="#ffffff", border="#dbe3ec", text="#16222f",
                  muted="#5b6b7e", accent="#0b7a75", onaccent="#ffffff"),
}
T = THEMES["dark" if st.session_state.dark else "light"]

# role -> (label, colour, what it does)
ROLE = {
    "receptionist": ("Receptionist", "#5b8def", "Registers patients, books visits"),
    "doctor": ("Doctor", "#2fbf9b", "Diagnoses and orders scans"),
    "diagnostics": ("Diagnostics lab", "#a07cf0", "Records scan results"),
    "prescriber": ("Prescriber", "#f0954a", "Writes the prescription"),
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400&display=swap');
html, body, .stApp, button, input, textarea { font-family: 'IBM Plex Sans', sans-serif !important; }
.stApp { background: %bg%; color: %text%; }
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] { visibility: hidden; height: 0; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; max-width: 1100px; }
[data-testid="stSidebar"] { background: %card%; border-right: 1px solid %border%; }
.stMarkdown, .stMarkdown p, .stMarkdown li, [data-testid="stWidgetLabel"] *,
[data-testid="stCaptionContainer"] * { color: %text%; }

.stMarkdown p.title { font-size: 2rem; font-weight: 600; letter-spacing: -0.02em; margin: 0; color: %text%; }
.stMarkdown p.sub { color: %muted%; margin: 2px 0 18px; font-size: 1rem; }
.board { display: flex; flex-wrap: wrap; border: 1px solid %border%; border-radius: 10px;
         background: %card%; margin-bottom: 20px; }
.board div { flex: 1 1 120px; padding: 12px 18px; border-right: 1px solid %border%; }
.board div:last-child { border-right: none; }
.board b { display: block; font-size: 1.6rem; font-weight: 500; color: %text%; }
.board span { color: %muted%; font-size: .85rem; }

.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid %border%; }
.stTabs [data-baseweb="tab"] { color: %muted%; padding: 8px 14px; }
.stTabs [aria-selected="true"] { color: %accent% !important; }
.stTabs [data-baseweb="tab-highlight"] { background: %accent%; }

.stButton > button { border-radius: 8px; border: 1px solid %border%; background: %card%;
                     color: %text%; font-weight: 500; }
.stButton > button:hover { border-color: %accent%; color: %accent%; }
.stButton > button[kind="primary"] { background: %accent%; color: %onaccent%; border-color: %accent%; }
[data-baseweb="select"] > div, .stTextInput input { background: %card% !important;
    color: %text% !important; border-color: %border% !important; }
div[data-baseweb="popover"] ul { background: %card% !important; }
div[data-baseweb="popover"] li { color: %text% !important; }
[data-testid="stBottom"] > div { background: %bg%; }
[data-testid="stChatInput"] > div, [data-testid="stChatInput"] textarea {
    background: %card% !important; color: %text% !important; border-color: %border% !important; }
[data-testid="stChatMessage"] { background: %card%; border: 1px solid %border%;
    border-radius: 10px; padding: 10px 14px; margin-bottom: 8px; }
[data-testid="stChatMessage"] * { color: %text%; }

.empty { border: 1px dashed %border%; border-radius: 10px; padding: 18px; color: %muted%; }
.step { position: relative; margin-left: 8px; padding: 0 0 16px 24px; border-left: 2px solid %border%; }
.step:last-child { border-left-color: transparent; }
.step .dot { position: absolute; left: -7px; top: 3px; width: 12px; height: 12px; border-radius: 50%; }
.step .head { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }
.step .name { font-weight: 600; color: %text%; }
.step code { font-family: 'IBM Plex Mono', monospace; font-size: .78rem; color: %muted%; background: none; }
.step .state { margin-left: auto; font-size: .8rem; color: %muted%; }
.step .body { margin-top: 6px; border: 1px solid %border%; background: %card%; border-radius: 8px;
              padding: 10px 14px; color: %text%; line-height: 1.5; }
.step.wait { opacity: .55; }
.agent { display: flex; gap: 10px; margin-bottom: 14px; }
.agent .dot { width: 10px; height: 10px; border-radius: 50%; margin-top: 6px; flex: none; }
.agent b { color: %text%; font-weight: 600; }
.agent small { display: block; color: %muted%; }
.agent code { font-family: 'IBM Plex Mono', monospace; font-size: .72rem; color: %muted%; background: none; padding: 0; }
.tbl-wrap { overflow-x: auto; border: 1px solid %border%; border-radius: 10px; background: %card%; }
table.tbl { width: 100%; border-collapse: collapse; font-size: .9rem; }
.tbl th { text-align: left; color: %muted%; font-weight: 500; padding: 9px 14px; border-bottom: 1px solid %border%; }
.tbl td { padding: 9px 14px; border-bottom: 1px solid %border%; color: %text%; }
.tbl tr:last-child td { border-bottom: none; }
.stMarkdown p.credit { color: %muted%; font-size: .8rem; margin-top: 28px; }
</style>
"""
for k, v in T.items():
    CSS = CSS.replace(f"%{k}%", v)
st.markdown(CSS, unsafe_allow_html=True)

TABLES = ["patients", "appointments", "diagnoses", "scan_orders", "prescriptions"]
LABELS = {"patients": "Patients", "appointments": "Appointments", "diagnoses": "Diagnoses",
          "scan_orders": "Scans", "prescriptions": "Prescriptions"}


def esc(s):
    return html.escape(str(s)).replace("\n", "<br>")


def step_html(role, body, state):
    label, color, _ = ROLE[role]
    status = {"wait": "Waiting", "run": "Working…", "done": "Done"}[state]
    cls = "step wait" if state == "wait" else "step"
    return (f'<div class="{cls}"><span class="dot" style="background:{color}"></span>'
            f'<div class="head"><span class="name">{label}</span><code>{esc(agents.spec(role))}</code>'
            f'<span class="state">{status}</span></div>'
            f'<div class="body">{esc(body)}</div></div>')


# ---------- sidebar ----------
with st.sidebar:
    st.toggle("Dark mode", key="dark")
    st.markdown("**Agents**")
    for r, (label, color, what) in ROLE.items():
        st.markdown(f'<div class="agent"><span class="dot" style="background:{color}"></span>'
                    f'<div><b>{label}</b><small>{what}</small><code>{esc(agents.spec(r))}</code></div></div>',
                    unsafe_allow_html=True)
    if st.button("Patient login", type="primary"):
        st.session_state.view = "portal"
        st.rerun()
    if st.button("Clear chat"):
        st.session_state.hist = []
        st.rerun()

# ---------- patient portal ----------
if st.session_state.get("view") == "portal":
    import patient_portal
    if st.sidebar.button("Back to staff console"):
        st.session_state.view = "staff"
        st.rerun()
    patient_portal.render(T)
    st.stop()

# ---------- header + ward board ----------
h1, h2 = st.columns([5, 1])
h1.markdown('<p class="title">Mini Hospital</p>'
            '<p class="sub">Four AI agents, one shared patient record. Synthetic data only.</p>',
            unsafe_allow_html=True)
if h2.button("Patient login", type="primary", key="login_main", width="stretch"):
    st.session_state.view = "portal"
    st.rerun()
counts = {t: db.read(f"SELECT COUNT(*) AS c FROM {t}")[0]["c"] for t in TABLES}
st.markdown('<div class="board">' + "".join(
    f"<div><b>{counts[t]}</b><span>{LABELS[t]}</span></div>" for t in TABLES) + "</div>",
    unsafe_allow_html=True)

chat_tab, visit_tab, rec_tab = st.tabs(["Reception", "Care pathway", "Records"])

# ---------- reception ----------
with chat_tab:
    hist = st.session_state.hist
    pending = None
    if not hist:
        st.markdown('<div class="empty">Ask the receptionist to register a patient, book a visit, '
                    'or look up a schedule.</div>', unsafe_allow_html=True)
        cols = st.columns(3)
        quick = ["Register Maria Lopez, 29, F, 555-0150, back pain",
                 "Show all appointments",
                 "Find patient Asha Rao and book Dr. Mehta tomorrow 11am"]
        for c, q in zip(cols, quick):
            if c.button(q, width="stretch"):
                pending = q
    for role, content in hist:
        st.chat_message(role).write(content)
    prompt = st.chat_input("Message the receptionist") or pending
    if prompt:
        hist.append(("user", prompt))
        st.chat_message("user").write(prompt)
        with st.spinner("Receptionist is working…"):
            try:
                reply = agents.call("receptionist", hist)
            except Exception as e:
                reply = f"Could not reach the model: {e}"
        hist.append(("assistant", reply))
        st.chat_message("assistant").write(reply)

# ---------- care pathway ----------
with visit_tab:
    pts = db.read("SELECT patient_id, name, complaint FROM patients")
    if not pts:
        st.markdown('<div class="empty">No patients yet. Register one in Reception.</div>',
                    unsafe_allow_html=True)
    else:
        pick = st.selectbox("Patient", pts,
                            format_func=lambda p: f"{p['patient_id']}. {p['name']}: {p['complaint']}")
        go = st.button("Run visit", type="primary")
        order = ["doctor", "diagnostics", "prescriber"]
        slots = {r: st.empty() for r in order}
        for i, r in enumerate(order):
            slots[r].markdown(step_html(r, "Not started yet.", "wait"), unsafe_allow_html=True)
        if go:
            slots[order[0]].markdown(step_html(order[0], "Reading the patient record…", "run"),
                                     unsafe_allow_html=True)
            try:
                for upd in agents.build_pipeline().stream(
                        {"patient_id": pick["patient_id"], "log": []}, stream_mode="updates"):
                    for _, val in upd.items():
                        role, msg = val["log"][-1]
                        slots[role].markdown(step_html(role, msg, "done"), unsafe_allow_html=True)
                        i = order.index(role)
                        if i + 1 < len(order):
                            nxt = order[i + 1]
                            slots[nxt].markdown(step_html(nxt, "Working on the case…", "run"),
                                                unsafe_allow_html=True)
                st.success("Visit complete. The new records are in the Records tab.")
            except Exception as e:
                st.error(f"Visit stopped: {e}\n\nThis is usually a rate limit or a bad key. "
                         "Wait a minute, or change that agent's model in .env.")

# ---------- records ----------
RECORD_TABLES = TABLES + ["diet_guides"]
LABELS["diet_guides"] = "Diet guides"
with rec_tab:
    for tab, t in zip(st.tabs([LABELS[t] for t in RECORD_TABLES]), RECORD_TABLES):
        with tab:
            rows = db.read(f"SELECT * FROM {t}")
            if rows:
                tbl = pd.DataFrame(rows).to_html(index=False, border=0, classes="tbl", escape=True)
                st.markdown(f'<div class="tbl-wrap">{tbl}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="empty">No records yet.</div>', unsafe_allow_html=True)

st.markdown('<p class="credit">Credits: Creator (Sam+TeknoSystems)</p>', unsafe_allow_html=True)
