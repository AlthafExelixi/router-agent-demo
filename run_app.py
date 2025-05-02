import os
import json
import re
import streamlit as st
from openai import OpenAI


# --- 1. Initialize OpenAI client ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- 2. Departments and descriptions ---
departments = [
    {"name": "HR Assistant",         "description": "Handles leave applications, benefits, onboarding, policies, appraisals, etc."},
    {"name": "IT Support Assistant", "description": "Resolves IT issues: email, VPN, device setup, logins, printers, network, etc."},
    {"name": "Finance Assistant",     "description": "Manages reimbursements, expense tracking, invoices, payroll, budgets, etc."},
    {"name": "Admin Assistant",       "description": "Takes care of office admin: ID cards, seating, office supplies, meeting rooms, etc."},
    {"name": "Travel Assistant",      "description": "Assists with booking flights, hotels, visas, itineraries, travel policies, etc."},
    {"name": "General Assistant",     "description": "Handles any general or uncategorized queries not covered by other departments. even Hi there!, Hello, how are you? these kind of generic questions and sentences comes to general assistant."}
]

def get_system_prompt():
    dept_list = "\n".join(f"- **{d['name']}**: {d['description']}" for d in departments)
    return f"""
You are a routing assistant. You will receive a block of user text that may contain one or more separate questions or requests.
Your job:
  1. Split the text into discrete prompts/questions.
  2. For each prompt, determine the single best department to handle it.
  3. If a prompt does not clearly belong to any department, assign it to **General Assistant**.
  4. Return *only* a raw JSON array of objects, each with:
       - \"prompt\": the question (string)
       - \"agent\": the exact department name (string)
Do NOT wrap the JSON in markdown or code fences. Do NOT return any extra text.
Here are the departments:
{dept_list}
"""

@st.cache_data
def classify_and_split(user_text: str, model: str = "gpt-4o") -> list[dict]:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system",  "content": get_system_prompt()},
            {"role": "user",    "content": user_text}
        ],
        temperature=0.0
    )
    raw = resp.choices[0].message.content.strip()
    raw = re.sub(r"^```json\s*|```$", "", raw, flags=re.MULTILINE).strip()
    return json.loads(raw)

# 4. Handler map
handler_map = {
    "HR Assistant": lambda prompt: ("👩‍💼 HR Assistant", prompt),
    "IT Support Assistant": lambda prompt: ("💻 IT Support Assistant", prompt),
    "Finance Assistant": lambda prompt: ("💰 Finance Assistant", prompt),
    "Admin Assistant": lambda prompt: ("📋 Admin Assistant", prompt),
    "Travel Assistant": lambda prompt: ("✈️ Travel Assistant", prompt),
    "General Assistant": lambda prompt: ("🆓 General Assistant", prompt),
}

# --- Streamlit layout ---
st.set_page_config(page_title="Employee Router Agent", page_icon="🤖", layout="wide")
st.title("🤖 Internal Employee Assistant")
st.markdown("Ask me anything related to HR, IT, Finance, Admin, Travel, or general queries.")

# Initialize session state
if "history" not in st.session_state:
    st.session_state.history = []

# Chat container
chat_container = st.container()

def display_chat():
    with chat_container:
        for role, text in st.session_state.history:
            if role == "user":
                st.chat_message("user").markdown(text)
            else:
                st.chat_message("assistant").markdown(text)

# Input
if prompt := st.chat_input(placeholder="Type your question here..."):
    # Add user message
    st.session_state.history.append(("user", prompt))

    # Classify and split
    try:
        routing = classify_and_split(prompt)
        # For each item, call handler and add to chat
        for item in routing:
            agent_name, agent_prompt = handler_map.get(item["agent"], handler_map["General Assistant"])(item["prompt"])
            response_text = f"**{agent_name} Activated**. Prompt: {agent_prompt}"
            st.session_state.history.append(("assistant", response_text))
    except Exception as e:
        st.session_state.history.append(("assistant", f"❌ Error: {e}"))

# Display chat
display_chat()
