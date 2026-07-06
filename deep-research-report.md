# Personalized Networking Assistant – Project Requirements & Implementation Plan

## Project Requirements  
- **Core Features:** An AI-powered web app that helps users network by generating personalized conversation starters. It must allow a user to enter an event description and interests, then return 2–3 relevant conversation prompts. It should also let the user query quick facts (e.g. conference topics) and receive concise summaries.  
- **User Scenarios:** As gleaned from the project overview:  
  - *Smart Starter Generation:* Input an event like “AI for Sustainable Cities” plus interests (“climate change”, “urban planning”) to get starter questions or comments.  
  - *Quick Fact Verification:* Input a topic (e.g. “blockchain in healthcare”) to retrieve a summarized reference using Wikipedia.  
  - *History Review:* View a “History” or “Previous Suggestions” page showing past queries and results (encouraging iterative improvement).  
- **Functional Scope:** The app needs input forms or text fields for the above features, buttons to trigger processing, and display areas for results. It should include separate sections/pages (e.g., tabs or sidebar) for “Generate Starters”, “Fact Check”, and “History”. Mentions in the UI suggest including fields to add a demo link and GitHub link (mentor review requirements).  
- **Data & Persistence:** Store user interactions and results (event descriptions, queries, generated prompts) in a database so the “History” can display them. An ER (entity-relationship) diagram is expected, meaning deliverables should define the data model (entities like `User`, `Query`, `Starter`, etc.).  
- **Non-Functional Requirements:** Follow specified system requirements: use Python 3.10+, FastAPI backend, Streamlit frontend. Ensure compatibility with Windows/Linux/macOS. Required packages include FastAPI, a Wikipedia API library, and any LLM interface. Internet access is needed for LLM calls and Wikipedia. 

## Technical Stack & Libraries  
- **Backend Framework (FastAPI):** We will use FastAPI to build the HTTP API. FastAPI is a high-performance Python web framework for building APIs with Python 3.8+. It natively supports asynchronous endpoints, data validation (via Pydantic), and automatic OpenAPI docs, which speeds development of JSON-based services.  
- **Frontend (Streamlit):** The UI will be built with Streamlit, an open-source Python framework for creating interactive web apps for data and AI workflows. Streamlit lets us write a simple script (with `st.text_input`, `st.button`, etc.) to create a live web interface. It’s ideal for rapid prototyping and requires minimal frontend code.  
- **LLM / AI Integration:** For generating conversation starters, we will call a large-language model API. The project spec mentions a “Google Gemini API Key,” so likely a Gemini (or OpenAI GPT) API will be used. This requires installing an HTTP client (e.g. `requests` or an official SDK) to send prompts and receive generated text. (No citation needed, using standard REST API techniques.)  
- **Wikipedia Lookup:** For fact-checking, use a Python Wikipedia library. For example, the [`wikipedia-api`](https://pypi.org/project/Wikipedia-API/) wrapper lets us fetch page summaries easily. This avoids dealing with raw HTTP calls to Wikimedia. Example: `page = wiki.page(query)` and then `page.summary`.  
- **Database:** Use SQLite or PostgreSQL to store query history. Since the UI suggests an ER diagram, we’ll define tables like `Query` (fields: id, user_id, input_text, result_text, timestamp, etc.) and possibly `User` if needed (though user auth isn’t specified). SQLAlchemy or similar ORM can manage this, but even a simple SQLite file with direct queries suffices given the short timeline.  
- **Other Tools:** Git for version control, `uvicorn` or `gunicorn` to run FastAPI, and an editor/IDE (VSCode or PyCharm as listed). No GUI frameworks beyond Streamlit are needed.

## Implementation Tasks & Epics  
We break down the work into logical epics and tasks, focusing on a Minimum Viable Product:

- **Epic 1: Model & Architecture Setup**  
  - *Choose and test LLM API:* Obtain Google Gemini (or OpenAI) API key. Write a small script to test prompt-response (generate conversation starters). This informs prompt design.  
  - *Design backend routes:* Plan API endpoints (e.g. `POST /generate` for starters, `GET /fact_check` for Wikipedia queries, `GET/POST /history` for stored data). Define request/response schemas.  
  - *ER Diagram:* Draft an ER diagram for storing history. For example, entities might include `EventInput` and `StarterOutput` or a single `Interaction` with fields (query, type, response, timestamp). Document the entities and relationships.  
- **Epic 2: Core Functionalities Development**  
  - *Endpoint – Generate Starters:* Implement FastAPI endpoint `/generate`. In the handler, accept JSON (e.g. `{"event": "...", "interests": "..."}`), build a prompt string, call the LLM API, and return the generated list (e.g. `{"starters": ["...", "..."]}`).  
  - *Endpoint – Fact Checking:* Implement `/fact_check` endpoint. Accept a query string, use `wikipediaapi` (or similar) to fetch a page summary. Return it in JSON (e.g. `{"query": "...", "summary": "..."}`). **Citation:** Wikipedia-API usage is simple and efficient.  
  - *Database & History:* Define a simple schema (e.g. `Interaction(id, type, input, output, timestamp)`). In each endpoint above, after generating output, save the interaction to the DB. Also create endpoints (or allow the frontend to fetch) for retrieving history by querying the DB (e.g. `GET /history`).  
- **Epic 3: Main Application Logic**  
  - *Integration:* Ensure that the logic flows end-to-end. For example, when `/generate` runs, it also writes to history. Validate JSON inputs and handle errors.  
  - *Authentication (optional):* If needed, add simple checks (though not specified). Likely skip due to time.  
  - *Environment & Config:* Set up configuration (e.g. API keys in environment variables), and a requirements file (`requirements.txt`) with all Python dependencies (FastAPI, Streamlit, Wikipedia-API, SQLAlchemy, etc.).  
- **Epic 4: Frontend UI Using Streamlit**  
  - *Layout:* Create a Streamlit app with multiple sections or tabs. For instance, use `st.sidebar.selectbox` or `st.tabs` with options “Generate Starters”, “Fact Check”, and “History”. Each section has its own inputs and outputs.  
  - *Interaction:* In “Generate Starters”, use `st.text_input` for event/interests, and a button that on click sends a request to our FastAPI (using `requests.post`). Display returned starters as text or markdown.  
  - *Fact Check UI:* Similarly, have a text input for query and a button that calls `/fact_check`, then display the Wikipedia summary.  
  - *History UI:* Add a section that fetches and shows the past interactions from our DB (could use `requests.get(".../history")`) in a table or list.  
  - *Other UI Elements:* Add text fields (per instructions) for “Demo Link” and “GitHub Link” so the mentor can copy them (these would just be editable text outputs). Use `st.write` or `st.text_input` for this.  
- **Epic 5: Testing, Polish & Deployment**  
  - *Local Testing:* Test all API endpoints manually (e.g. via curl or built-in docs at `/docs`). Ensure CORS isn’t an issue (Streamlit can be on localhost too). Write minimal unit tests if time permits (e.g. test Wikipedia lookup).  
  - *Time Management:* With only ~6 hours, focus on getting a working pipeline first. Edge-case handling (e.g. missing Wikipedia pages) should be basic.  
  - *Deployment Prep:* Run the FastAPI app with Uvicorn (`uvicorn main:app --reload`) and ensure the Streamlit app runs (`streamlit run app.py`). Prepare a README with steps and include “Demo”/“GitHub” links if applicable.  
  - *Documentation:* Fill any needed comments and a brief readme. Include the ER diagram in comments or a markdown section if possible.  

## Timeline & Time Estimates  
1. **Project Setup (0.5h):** Initialize repo, virtual environment, install FastAPI, Streamlit, SQLite, Wikipedia-API. Sketch ER diagram and endpoints.  
2. **API Development (1.5h):** Implement `/generate` and `/fact_check` in FastAPI. Integrate LLM call (even if mocked). Integrate Wikipedia lookup. Test these endpoints.  
3. **Database & History (1.0h):** Define SQLite schema (SQLAlchemy models or raw SQL). Add history-saving in the above endpoints. Implement a simple `GET /history` that returns stored interactions.  
4. **Frontend (Streamlit) (2.0h):** Build the UI pages. Use `st.input` fields and buttons to call the FastAPI endpoints. Test the flow: user inputs → backend call → display output. Add “History” page showing past entries.  
5. **Wrap-Up (1.0h):** Test entire app from end to end. Fix bugs, refine prompts, ensure Docker/Deployment readiness if needed. Write README, ER diagram explanations, and finalize deliverables.  

_Total ≈ 6 hours._ This schedule prioritizes a working submission first, then quick refinements if time allows.

## Deliverables Checklist  
- **Source Code:** `main.py` (FastAPI app), `app.py` (Streamlit script), `requirements.txt`. All endpoints and UI logic implemented.  
- **ER Diagram & Description:** A simple diagram (can be a drawn link if possible) or detailed schema description in a comment/README explaining entities (e.g. tables for queries and outputs).  
- **README File:** Instructions to run the app (setup, how to start FastAPI and Streamlit), and placeholders for “Demo Link” and “GitHub Link” that mentors can use.  
- **Demo/Links:** The app should be linkable (if deployed) or at least instructions given. Populate the “Add Demo/GitHub” fields in the UI.  
- **Sample Queries:** Include example inputs and expected outputs in the README or comments (e.g. example event and generated starters, example topic and Wikipedia summary).  

## Sample Code Snippets  

**FastAPI Endpoint (Generate Starters):**  
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ConversationRequest(BaseModel):
    event: str
    interests: str

@app.post("/generate")
async def generate_starters(req: ConversationRequest):
    prompt = (
        f"Generate 3 conversation starters for an event: '{req.event}'. "
        f"Include context from interests: {req.interests}."
    )
    # Call to LLM API (e.g., OpenAI or Google Gemini):
    # response = call_llm_api(prompt)
    # For now, use a placeholder:
    starters = [
        "Have you explored how climate change impacts urban planning at this event?",
        "What innovative solutions in AI are you most excited to discuss today?",
        "How does sustainable city development influence your professional goals?"
    ]
    return {"starters": starters}
```

**FastAPI Endpoint (Fact Check via Wikipedia):**  
```python
import wikipediaapi
from fastapi import Query

@app.get("/fact_check")
def fact_check(query: str = Query(..., description="Topic to search in Wikipedia")):
    wiki = wikipediaapi.Wikipedia(language='en', user_agent='networking-assistant')
    page = wiki.page(query)
    if page.exists():
        summary = page.summary
    else:
        summary = "No information found for that query."
    return {"query": query, "summary": summary}
```

**Streamlit UI Example:**  
```python
import streamlit as st
import requests

st.title("Personalized Networking Assistant")

# --- Generate Starters Section ---
st.header("Generate Conversation Starters")
event = st.text_input("Event Description", "")
interests = st.text_input("Your Interests (optional)", "")
if st.button("Generate Starters"):
    if event:
        resp = requests.post("http://localhost:8000/generate", json={
            "event": event, "interests": interests
        })
        data = resp.json()
        for starter in data.get("starters", []):
            st.write(f"- {starter}")
    else:
        st.write("Please enter an event description.")

# --- Quick Fact Check Section ---
st.header("Quick Fact Verification")
topic = st.text_input("Topic / Fact to Verify", "")
if st.button("Check Wikipedia"):
    if topic:
        resp = requests.get(f"http://localhost:8000/fact_check?query={topic}")
        data = resp.json()
        st.write(data.get("summary", ""))
    else:
        st.write("Please enter a topic to search.")

# --- History Section ---
st.header("History of Interactions")
resp = requests.get("http://localhost:8000/history")
if resp.status_code == 200:
    history_items = resp.json()
    for item in history_items:
        st.write(f"**{item['timestamp']}** – *{item['type']}*: {item['input']} → {item['output']}")
```

**Notes:** These snippets illustrate the core idea. In production, you’d replace placeholders (e.g. the `starters` list) with actual LLM API calls. The code assumes the FastAPI server runs on `localhost:8000`. Remember to install all libraries (`fastapi`, `uvicorn`, `streamlit`, `wikipedia-api`, etc.) and run each part (FastAPI and Streamlit) separately.

**Key References:** For help with the Wikipedia integration, see the [Wikipedia-API documentation](https://pypi.org/project/Wikipedia-API/). FastAPI’s capabilities are described on Wikipedia, and Streamlit’s purpose is outlined in its docs, confirming their suitability for this project. These tools, combined with a pre-built LLM API, allow quick delivery of the required features within the time limit.  

