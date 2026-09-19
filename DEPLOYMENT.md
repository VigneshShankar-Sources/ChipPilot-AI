# ChipPilot AI — Deployment Guide

This guide details multiple deployment options for **ChipPilot AI**, from 1-click zero-cost cloud hosting to Dockerized production deployment.

---

## 🌟 Option 1: Streamlit Community Cloud (Recommended — 100% Free & 1-Click)

Streamlit Community Cloud is the easiest and fastest way to deploy the interactive engineering dashboard for free directly from GitHub.

### Step-by-Step Instructions:
1. Ensure your repository is pushed to GitHub: `https://github.com/VigneshShankar-Sources/ChipPilot-AI`.
2. Go to [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.
3. Click **"New app"**.
4. Select your repository: `VigneshShankar-Sources/ChipPilot-AI`.
5. Set the **Main file path** to: `frontend/dashboard.py`.
6. Click **Deploy!**
7. Your app will build and go live with a public URL (e.g. `https://chippilot-ai.streamlit.app`).

---

## 🤗 Option 2: Hugging Face Spaces (Free CPU / GPU Hosting)

Hugging Face Spaces is another popular platform for hosting AI engineering tools:

1. Go to [Hugging Face Spaces](https://huggingface.co/spaces) and click **"Create new Space"**.
2. Select **Streamlit** as the Space SDK.
3. Choose Public or Private.
4. Clone or connect your GitHub repository.
5. Set the entrypoint to `frontend/dashboard.py` and requirements from `requirements.txt`.

---

## 🐳 Option 3: Docker & Docker Compose (Self-Hosted / Cloud VPS)

You can run both the **Streamlit Dashboard** and the **FastAPI REST API** locally or on any cloud server (AWS EC2, DigitalOcean, Hetzner, GCP, Linode).

### Run with Docker Compose:
```bash
# Clone the repository
git clone https://github.com/VigneshShankar-Sources/ChipPilot-AI.git
cd ChipPilot-AI

# Start both Dashboard & REST API
docker compose up --build -d
```
- **Streamlit UI**: `http://localhost:8501`
- **FastAPI Docs**: `http://localhost:8000/docs`

### Run Streamlit Single Container:
```bash
docker build -t chippilot-ai .
docker run -p 8501:8501 chippilot-ai
```

---

## ☁️ Option 4: Render / Railway / Koyeb (Web Service)

### On Render:
1. Sign in to [render.com](https://render.com) and click **"New Web Service"**.
2. Connect your GitHub repository `ChipPilot-AI`.
3. Set **Runtime** to `Python` (or `Docker`).
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**:
   - For Dashboard: `streamlit run frontend/dashboard.py --server.port=$PORT --server.address=0.0.0.0`
   - Or for API: `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
6. Click **Create Web Service**.

---

## 🔒 Environment & Configuration

ChipPilot AI comes with pre-configured defaults in `.streamlit/config.toml` and `configs/`. No mandatory paid API keys are required as the core diagnostic engine, EKG graph builder, and RCA scoring run deterministically and locally.
