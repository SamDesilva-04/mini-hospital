# Mini Hospital

A multi-agent AI hospital workflow demo with a patient portal. Built with LangGraph and Streamlit.

**All data is synthetic. This is a prototype, not a medical tool and not medical advice.**

## What it does

Four AI agents, each with its own role, its own model and access only to its own tools, work from one shared patient database:

| Agent | Role |
|---|---|
| Receptionist | Registers patients, books appointments |
| Doctor | Reviews the complaint, writes a diagnosis, orders a scan |
| Diagnostics lab | Records scan results |
| Prescriber | Reads the full case and writes a prescription |

**Patient portal** (Patient login button): a demo patient signs in with an ID and PIN and sees a diabetes dashboard with blood sugar and HbA1c charts, medicines, upcoming checkup and scan dates, and a diet assistant.

**Diet guides:** the assistant answers from a table of 30 common conditions, with plain-language names and the medical term in brackets. These entries are drafts and must be reviewed by a qualified dietitian or doctor before any patient use.

## Run locally

```
pip install -r requirements.txt
python -m streamlit run app.py
```

Create a `.env` file next to `app.py`:

```
GROQ_API_KEY=
GOOGLE_API_KEY=
OPENROUTER_API_KEY=

RECEPTIONIST_MODEL=groq:openai/gpt-oss-120b
DOCTOR_MODEL=gemini:gemini-3.8-flash
DIAGNOSTICS_MODEL=groq:openai/gpt-oss-20b
PRESCRIBER_MODEL=groq:openai/gpt-oss-120b
```

Models use the format `provider:model`. Supported providers are `groq`, `gemini`, `openrouter`, `openai` and `anthropic`. Free-tier keys are enough for the demo. Optionally set `REQUIRE_APPROVED=1` to make the diet assistant use only guides marked `approved`.

## Demo patient logins

| Patient ID | PIN |
|---|---|
| MH-1001 | 1234 |
| MH-1002 | 2345 |
| MH-1003 | 3456 |

## Files

- `app.py`: Streamlit app (staff console, dark/light theme)
- `agents.py`: agent roles, tools and the LangGraph visit pipeline
- `db.py`: SQLite schema and seed data
- `diet_kb.py`: diet guide knowledge base and search
- `patient_portal.py`: patient login, dashboard and diet assistant

## Limits

- The SQLite database resets when the hosted app restarts.
- Free-tier model APIs have rate limits.
- Demo PINs are stored in the code. Real patients would need proper authentication.
