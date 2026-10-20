import os, time
from functools import lru_cache
from typing import TypedDict
from dotenv import load_dotenv
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START, END
import db

load_dotenv()
db.init()

# ---------- model per agent (all free-tier by default) ----------
DEFAULTS = {
    "receptionist": "groq:llama-3.3-70b-versatile",
    "doctor": "gemini:gemini-2.5-flash",
    "diagnostics": "openrouter:meta-llama/llama-3.3-70b-instruct:free",
    "prescriber": "gemini:gemini-2.5-flash",
}

def spec(role):
    return os.getenv(f"{role.upper()}_MODEL", DEFAULTS[role])

def make_llm(s):
    provider, model = s.split(":", 1)
    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(model=model, temperature=0)
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, temperature=0)
    if provider == "openrouter":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, temperature=0,
                          base_url="https://openrouter.ai/api/v1",
                          api_key=os.getenv("OPENROUTER_API_KEY"))
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, temperature=0)
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, temperature=0)
    raise ValueError(f"unknown provider {provider}")

# ---------- role-limited tools ----------
def _need(pid):
    return None if db.patient_exists(pid) else f"ERROR: patient_id {pid} not found"

@tool
def find_patient(name: str) -> str:
    """Find patients by (partial) name. Returns matching rows with patient_id."""
    return str(db.read("SELECT * FROM patients WHERE name LIKE ?", (f"%{name}%",)))

@tool
def add_patient(name: str, age: int, gender: str, phone: str, complaint: str) -> str:
    """Register a new patient. Returns the new patient_id."""
    pid = db.write("INSERT INTO patients(name,age,gender,phone,complaint) VALUES(?,?,?,?,?)",
                   (name, age, gender, phone, complaint))
    return f"Registered patient_id={pid}"

@tool
def book_appointment(patient_id: int, doctor: str, slot: str, reason: str) -> str:
    """Book an appointment for an existing patient_id."""
    if e := _need(patient_id): return e
    aid = db.write("INSERT INTO appointments(patient_id,doctor,slot,reason) VALUES(?,?,?,?)",
                   (patient_id, doctor, slot, reason))
    return f"Booked appt_id={aid}"

@tool
def list_appointments() -> str:
    """List all appointments."""
    return str(db.read("SELECT * FROM appointments"))

@tool
def get_patient(patient_id: int) -> str:
    """Read a patient's record."""
    if e := _need(patient_id): return e
    return str(db.read("SELECT * FROM patients WHERE patient_id=?", (patient_id,)))

@tool
def add_diagnosis(patient_id: int, diagnosis: str, notes: str) -> str:
    """Write a diagnosis and clinical notes for a patient_id."""
    if e := _need(patient_id): return e
    did = db.write("INSERT INTO diagnoses(patient_id,diagnosis,notes) VALUES(?,?,?)",
                   (patient_id, diagnosis, notes))
    return f"Saved diag_id={did}"

@tool
def order_scan(patient_id: int, scan_type: str) -> str:
    """Order a diagnostic scan (e.g. 'Chest X-ray', 'ECG') for a patient_id."""
    if e := _need(patient_id): return e
    oid = db.write("INSERT INTO scan_orders(patient_id,scan_type) VALUES(?,?)",
                   (patient_id, scan_type))
    return f"Ordered order_id={oid}"

@tool
def get_pending_scans(patient_id: int) -> str:
    """List pending scan orders for a patient_id."""
    return str(db.read("SELECT * FROM scan_orders WHERE patient_id=? AND status='pending'",
                       (patient_id,)))

@tool
def add_scan_result(order_id: int, findings: str) -> str:
    """Record findings for a scan order_id and mark it done."""
    if not db.read("SELECT 1 FROM scan_orders WHERE order_id=?", (order_id,)):
        return f"ERROR: order_id {order_id} not found"
    db.write("UPDATE scan_orders SET findings=?, status='done' WHERE order_id=?",
             (findings, order_id))
    return f"Result saved for order_id={order_id}"

@tool
def get_case(patient_id: int) -> str:
    """Read patient record, diagnoses and scan results."""
    if e := _need(patient_id): return e
    return str({
        "patient": db.read("SELECT * FROM patients WHERE patient_id=?", (patient_id,)),
        "diagnoses": db.read("SELECT * FROM diagnoses WHERE patient_id=?", (patient_id,)),
        "scans": db.read("SELECT * FROM scan_orders WHERE patient_id=?", (patient_id,)),
    })

@tool
def write_prescription(patient_id: int, medication: str, dosage: str, instructions: str) -> str:
    """Write a prescription for a patient_id."""
    if e := _need(patient_id): return e
    rid = db.write("INSERT INTO prescriptions(patient_id,medication,dosage,instructions) VALUES(?,?,?,?)",
                   (patient_id, medication, dosage, instructions))
    return f"Saved rx_id={rid}"

ROLES = {
    "receptionist": ([find_patient, add_patient, book_appointment, list_appointments],
        "You are the hospital receptionist. Register patients, book appointments, "
        "answer schedule questions. Use find_patient before assuming a patient_id. "
        "Never invent IDs. Be brief."),
    "doctor": ([get_patient, add_diagnosis, order_scan],
        "You are the doctor. Read the patient record, write a diagnosis with notes, "
        "and order exactly one appropriate scan. Reply with a 2-line summary."),
    "diagnostics": ([get_pending_scans, add_scan_result],
        "You are the diagnostics lab. For each pending scan, record realistic SYNTHETIC "
        "findings. Reply with a 1-line summary."),
    "prescriber": ([get_case, write_prescription],
        "You are the prescriber. Read the full case, then write one prescription "
        "consistent with the diagnosis and scan findings. Reply with a 1-line summary. "
        "This is a demo with synthetic data."),
}

@lru_cache(maxsize=None)
def agent(role):
    tools, prompt = ROLES[role]
    return create_react_agent(make_llm(spec(role)), tools, prompt=prompt)

def text(msg):
    c = msg.content
    if isinstance(c, list):
        return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in c)
    return c

def call(role, messages, tries=3):
    for i in range(tries):
        try:
            out = agent(role).invoke({"messages": messages}, {"recursion_limit": 15})
            return text(out["messages"][-1])
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))  # backoff for free-tier rate limits

# ---------- LangGraph pipeline: doctor -> diagnostics -> prescriber ----------
class State(TypedDict):
    patient_id: int
    log: list

STEPS = [
    ("doctor", "Patient {pid} is here. Read the record, diagnose, and order one scan."),
    ("diagnostics", "Process the pending scans for patient {pid}."),
    ("prescriber", "Review the full case for patient {pid} and write a prescription."),
]

def _node(role, instr):
    def run(state: State):
        reply = call(role, [("user", instr.format(pid=state["patient_id"]))])
        return {"log": state["log"] + [(role, reply)]}
    return run

def build_pipeline():
    g = StateGraph(State)
    for role, instr in STEPS:
        g.add_node(role, _node(role, instr))
    g.add_edge(START, STEPS[0][0])
    for (a, _), (b, _) in zip(STEPS, STEPS[1:]):
        g.add_edge(a, b)
    g.add_edge(STEPS[-1][0], END)
    return g.compile()
