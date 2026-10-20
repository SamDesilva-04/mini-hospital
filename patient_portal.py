"""Patient portal: demo login, synthetic diabetes dashboard, WHO-grounded diet assistant."""
import datetime as dt
import os
import random

import altair as alt
import pandas as pd
import streamlit as st

import agents
import diet_kb

TODAY = dt.date.today()

# Synthetic demo patients. Not real people, not real data.
PATIENTS = {
    "MH-1001": dict(pin="1234", name="Asha Rao", age=34, seed=1, base=118, trend=-0.4,
                    hba1c=[7.9, 7.6, 7.2, 6.9, 6.8, 6.6], adherence=[96, 93, 100, 96, 97],
                    checkup=12, scan=40, scan_name="Retinal eye exam",
                    meds=[("Metformin", "500 mg", "Twice daily, with meals", "Lowers sugar made by the liver")]),
    "MH-1002": dict(pin="2345", name="Ravi Kumar", age=52, seed=2, base=152, trend=0.6,
                    hba1c=[7.4, 7.7, 7.9, 8.1, 8.2, 8.4], adherence=[82, 75, 68, 71, 64],
                    checkup=5, scan=21, scan_name="Kidney function panel",
                    meds=[("Metformin", "1000 mg", "Twice daily, with meals", "Lowers sugar made by the liver"),
                          ("Glimepiride", "2 mg", "Once daily, before breakfast", "Helps the body release insulin"),
                          ("Atorvastatin", "10 mg", "Once daily, evening", "Protects the heart by lowering cholesterol")]),
    "MH-1003": dict(pin="3456", name="Meera Iyer", age=61, seed=3, base=176, trend=1.1,
                    hba1c=[8.2, 8.6, 9.0, 9.3, 9.6, 9.9], adherence=[60, 52, 58, 45, 48],
                    checkup=2, scan=9, scan_name="Foot and nerve check",
                    meds=[("Metformin", "1000 mg", "Twice daily, with meals", "Lowers sugar made by the liver"),
                          ("Insulin glargine", "18 units", "Once daily, bedtime", "Long-acting insulin"),
                          ("Amlodipine", "5 mg", "Once daily, morning", "Lowers blood pressure")]),
}

WHO_GUIDE = """Base all food advice on WHO healthy-diet guidance:
- Eat at least 400 g (5 portions) of fruit and vegetables a day. Potatoes, sweet potatoes, cassava and other starchy roots do not count.
- Prefer legumes, nuts and whole grains (oats, brown rice, unprocessed maize, millet) over refined grains.
- Free sugars: under 10% of total energy, ideally under 5%. Avoid sugary drinks, sweets and sweetened snacks.
- Salt: under 5 g a day (about one teaspoon). Limit salty processed foods.
- Fats: total under 30% of energy, saturated under 10%, trans fat under 1%. Prefer unsaturated fats (fish, avocado, nuts, olive or sunflower oil) over butter, ghee and lard.
- Drink water, limit alcohol, eat regular meals with sensible portions."""


def series(p):
    r = random.Random(p["seed"])
    days = [TODAY - dt.timedelta(days=29 - i) for i in range(30)]
    vals = [max(70, round(p["base"] + p["trend"] * (i - 29) + r.gauss(0, 14))) for i in range(30)]
    return pd.DataFrame({"date": pd.to_datetime(days), "glucose": vals})


def status(a1c):
    if a1c < 7.0:
        return "Well controlled", "#2fbf9b"
    if a1c < 8.5:
        return "Needs attention", "#f0b24a"
    return "High risk", "#ef5b5b"


def style(ch, T):
    return (ch.properties(height=230, background="transparent")
            .configure_view(strokeWidth=0)
            .configure_axis(labelColor=T["muted"], titleColor=T["muted"],
                            gridColor=T["border"], domainColor=T["border"]))


def charts(p, T):
    g = series(p)
    band = pd.DataFrame({"lo": [80], "hi": [130]})
    glu = (alt.Chart(band).mark_rect(color=T["accent"], opacity=0.12).encode(y="lo:Q", y2="hi:Q")
           + alt.Chart(g).mark_line(color=T["accent"], point=True).encode(
               x=alt.X("date:T", title=None),
               y=alt.Y("glucose:Q", title="mg/dL", scale=alt.Scale(domain=[60, 260])),
               tooltip=["date:T", "glucose:Q"]))
    h = pd.DataFrame({"q": ["Q-5", "Q-4", "Q-3", "Q-2", "Q-1", "Latest"], "a1c": p["hba1c"]})
    h["i"] = range(6)
    a1c = (alt.Chart(pd.DataFrame({"y": [7.0]})).mark_rule(strokeDash=[5, 4], color=T["muted"]).encode(y="y:Q")
           + alt.Chart(h).mark_line(color="#f0954a", point=True).encode(
               x=alt.X("q:N", sort=list(h["q"]), title=None, axis=alt.Axis(labelAngle=0)),
               y=alt.Y("a1c:Q", title="HbA1c %", scale=alt.Scale(domain=[5.5, 11])),
               tooltip=["q", "a1c"]))
    w = pd.DataFrame({"week": [f"Wk {i + 1}" for i in range(5)], "pct": p["adherence"]})
    adh = alt.Chart(w).mark_bar(color="#5b8def", cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("week:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("pct:Q", title="Doses taken %", scale=alt.Scale(domain=[0, 100])), tooltip=["week", "pct"])
    return g, style(glu, T), style(a1c, T), style(adh, T)


def table(rows, cols):
    df = pd.DataFrame(rows, columns=cols).to_html(index=False, border=0, classes="tbl", escape=True)
    st.markdown(f'<div class="tbl-wrap">{df}</div>', unsafe_allow_html=True)


def ask(p, hist):
    last = p["hba1c"][-1]
    ctx = (f"Patient: {p['name']}, age {p['age']}, type 2 diabetes. Latest HbA1c {last}%. "
           f"Medicines: {', '.join(f'{m[0]} {m[1]}' for m in p['meds'])}. Demo data.")
    query = " ".join(m for r, m in hist if r == "user")[-400:]
    ref = diet_kb.as_prompt(diet_kb.search(query, ("diabetes",))) or "(no matching reference entry)"
    system = ("You are a friendly diet assistant in a patient portal. Use ONLY the WHO baseline and the "
              "REFERENCE entries below for food advice.\n" + WHO_GUIDE + "\nREFERENCE ENTRIES:\n" + ref +
              "\nRules: rewrite the reference in short, simple, warm language; always give the everyday name first "
              "and the medical term in brackets, for example high blood sugar condition (diabetes mellitus); "
              "give 3 to 5 specific foods with portion ideas; if the question is not covered by the reference "
              "entries, say you have no reviewed guidance on it and suggest asking their doctor or dietitian; "
              "if an entry's status is draft, add: This guidance is a draft awaiting dietitian review; "
              "never start, stop or change medicines or doses; if the patient mentions very high or very low sugar, "
              "confusion, vomiting, chest pain or fainting, or an entry's urgent signs, tell them to contact their "
              "doctor or emergency services now; do not invent citations or links. "
              "End with: General guidance, not medical advice.\n" + ctx)
    llm = agents.make_llm(os.getenv("PORTAL_MODEL", "groq:openai/gpt-oss-120b"))
    return agents.text(llm.invoke([("system", system)] + hist))


def login(T):
    st.markdown('<p class="title">Patient login</p><p class="sub">View your health dashboard and ask the diet assistant.</p>',
                unsafe_allow_html=True)
    with st.form("login"):
        pid = st.text_input("Patient ID", placeholder="MH-1001")
        pin = st.text_input("PIN", type="password")
        if st.form_submit_button("Sign in", type="primary"):
            p = PATIENTS.get(pid.strip().upper())
            if p and p["pin"] == pin:
                st.session_state.pid, st.session_state.phist = pid.strip().upper(), []
                st.rerun()
            st.error("Patient ID or PIN not recognised.")
    st.markdown('<div class="empty">Demo patients (synthetic): MH-1001 / 1234, MH-1002 / 2345, MH-1003 / 3456</div>',
                unsafe_allow_html=True)


def render(T):
    pid = st.session_state.get("pid")
    if not pid:
        return login(T)
    p = PATIENTS[pid]
    g, glu, a1c, adh = charts(p, T)
    label, color = status(p["hba1c"][-1])
    c1, c2 = st.columns([5, 1])
    c1.markdown(f'<p class="title">Hello, {p["name"].split()[0]}</p><p class="sub">Patient ID {pid} · Demo data</p>',
                unsafe_allow_html=True)
    if c2.button("Sign out"):
        st.session_state.pid = None
        st.rerun()
    adh30 = round(sum(p["adherence"]) / len(p["adherence"]))
    st.markdown(
        f'<div class="board"><div><b style="color:{color}">{label}</b><span>Diabetes status</span></div>'
        f'<div><b>{p["hba1c"][-1]}%</b><span>Latest HbA1c</span></div>'
        f'<div><b>{round(g["glucose"].tail(7).mean())}</b><span>Avg fasting sugar, 7 days (mg/dL)</span></div>'
        f'<div><b>{adh30}%</b><span>Doses taken, last 5 weeks</span></div></div>', unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["Overview", "Medicines and care", "Diet assistant"])
    with t1:
        a, b = st.columns(2)
        a.markdown("**Fasting blood sugar, last 30 days**  \nShaded band is the demo target range, 80 to 130 mg/dL.")
        a.altair_chart(glu, theme=None, width="stretch")
        b.markdown("**HbA1c over time**  \nDashed line marks 7%, a common target. Your doctor sets yours.")
        b.altair_chart(a1c, theme=None, width="stretch")
        st.markdown("**Medicine adherence by week**")
        st.altair_chart(adh, theme=None, width="stretch")
    with t2:
        st.markdown("**Your medicines**")
        table([(m[0], m[1], m[2], m[3]) for m in p["meds"]], ["Medicine", "Dose", "When", "What it does"])
        st.markdown("**Upcoming**")
        table([("Doctor checkup", (TODAY + dt.timedelta(days=p["checkup"])).strftime("%d %b %Y")),
               (p["scan_name"], (TODAY + dt.timedelta(days=p["scan"])).strftime("%d %b %Y"))],
              ["Appointment", "Date"])
        st.markdown(f"""**Why every dose matters**
- **Days:** sugar rises, with thirst, frequent urination, tiredness and blurred vision. Very high levels can need urgent care.
- **Months:** HbA1c climbs and sugar swings get harder to control. You took {adh30}% of doses recently.
- **Years:** higher risk of damage to eyes, kidneys, nerves and feet, and of heart disease and stroke.

Never stop or change a dose without asking your doctor.""")
    with t3:
        st.caption("Food guidance follows the WHO healthy diet and diabetes fact sheets. General guidance, not medical advice.")
        hist, pending = st.session_state.phist, None
        if not hist:
            cols = st.columns(3)
            for c, q in zip(cols, ["Can you explain my medical condition?", "Which snacks are safe?",
                                   "Which foods should I limit?"]):
                if c.button(q, width="stretch"):
                    pending = q
        for role, msg in hist:
            st.chat_message(role).write(msg)
        prompt = st.chat_input("Ask about food and diabetes") or pending
        if prompt:
            hist.append(("user", prompt))
            st.chat_message("user").write(prompt)
            with st.spinner("thinking on a food advice..."):
                try:
                    reply = ask(p, hist)
                except Exception as e:
                    reply = f"The assistant is unavailable right now ({e}). Please try again in a minute."
            hist.append(("assistant", reply))
            st.chat_message("assistant").write(reply)
