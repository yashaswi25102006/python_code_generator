# 🤖 Agentic Dev/Test Crew

A small two-agent workflow built with **LangGraph** + **Gemini**, wrapped in a **Streamlit** chat-style UI:

- **Developer agent** — writes Python code for whatever task you describe.
- **Tester agent** — generates test scenarios for the task *and* actually executes the generated code, then reports both.

## Run locally

```bash
git clone <your-repo-url>
cd <your-repo>
pip install -r requirements.txt
```

Set your Gemini API key (either works):

- Create `.streamlit/secrets.toml` (copy `.streamlit/secrets.toml.example`) with:
  ```toml
  GEMINI_API_KEY = "your-key-here"
  ```
- Or just paste it into the sidebar text box when the app is running.

Then launch:

```bash
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

## Deploy on Render

1. Push this folder to a GitHub repo (public or private, either works on Render).
2. Go to [render.com](https://render.com), sign in with GitHub.
3. Click **New → Web Service**, and pick your repo.
   - Render should auto-detect the included `render.yaml` and pre-fill the build/start commands. If it doesn't, set them manually:
     - **Build command:** `pip install -r requirements.txt`
     - **Start command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
4. Under **Environment**, add a variable:
   - Key: `GEMINI_API_KEY`, Value: your Gemini API key
5. Click **Create Web Service**. First deploy takes a couple of minutes. Your app will be live at `https://<your-app-name>.onrender.com`.

> Free-tier Render web services spin down after inactivity and take ~30–60s to wake back up on the next visit — normal, not a bug.

## Deploy on Streamlit Community Cloud (free, alternative)

1. Push this folder to a **public GitHub repo**.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app**, pick your repo/branch, and set the main file path to `app.py`.
4. In the app's **Settings → Secrets**, paste:
   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```
5. Deploy. Your app will be live at `https://<your-app-name>.streamlit.app`.

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit app (UI + LangGraph agent workflow) |
| `requirements.txt` | Python dependencies |
| `.streamlit/secrets.toml.example` | Template for your API key — copy, don't commit the real one |
| `.gitignore` | Keeps secrets/venvs out of git |

## Notes

- Get a free Gemini API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
- `run_python_code` executes model-generated code with Python's `exec`. That's fine for a personal/demo tool, but **don't expose this app publicly without adding sandboxing** if you plan to let untrusted users submit tasks.
