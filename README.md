# KisanSetu (किसान सेतु) 🌾🇮🇳
### *Sovereign Vernacular AI Voice Desk for Bharat's Farmers*

Built for **[The Great Indian AI Internship Challenge](https://www.gnani.ai/great-indian-ai-internship-registration-form#terms)** by **Gnani.ai**.

[![Gnani AI](https://img.shields.io/badge/Powered%20By-Gnani%20Artha%20Stack-emerald?style=for-the-badge)](https://gnani.ai)
[![Prisma STT](https://img.shields.io/badge/STT-Gnani%20Prisma%20v2.5-blue?style=for-the-badge)](https://docs.gnani.ai/api/STT/speech-to-text)
[![Timbre TTS](https://img.shields.io/badge/TTS-Gnani%20Timbre%20v2.5-amber?style=for-the-badge)](https://docs.gnani.ai/api/TTS/tts-inference)

---

## 🌟 Overview
**KisanSetu** brings the power of **Gnani Artha (India's Sovereign AI Stack)** directly to India's agricultural heartland. Farmers can simply speak into their phones in **Hindi, Marathi, Telugu, Kannada, or code-mixed dialects**—even while surrounded by loud diesel tractors or bustling APMC mandi chatter.

### Key Capabilities:
* 🎙️ **Acoustic Noise Resilience**: Powered by **Gnani Prisma v2.5**, transcribing spoken queries in ~150ms despite background tractor or market noise.
* 🔊 **Natural Indic Voice Synthesis**: Powered by **Gnani Timbre v2.5**, delivering voice advice in warm Indic cadences.
* 🌾 **Live APMC Mandi Bhav**: Real-time modal, minimum, and maximum rates across Indian mandis (Nashik, Indore, Warangal, Khanna) with price trends.
* 🍅 **Crop Rog Nidan (Crop Doctor)**: Rapid pest and leaf disease diagnosis with organic remedies and chemical dosages.
* 💰 **Sarkari Yojna**: Instant eligibility checks and toll-free contacts for PM-Kisan, PM Fasal Bima, and KCC.
* 🎛️ **The Acoustic Stress-Test Toggle**: Switch live between *Clean Audio*, *Field Tractor Rumble*, *Rural Mandi Chatter*, and *8kHz Narrowband Telephony*.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
* Python 3.10 or higher
* A valid Gnani AI API key (`GNANI_API_KEY`)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/your-username/kisansetu.git
cd kisansetu

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and set your Gnani API key:
```env
GNANI_API_KEY=vach_your_gnani_key_here
HOST=127.0.0.1
PORT=8000
```

### 4. Run the Application
```bash
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser and navigate to: **`http://127.0.0.1:8000`**

---

## 📁 Repository Structure
```
├── README.md                 # Project documentation
├── .env.example              # Template for API credentials
├── backend/
│   ├── app.py                # FastAPI backend & static server
│   ├── gnani_client.py       # Gnani Prisma v2.5 STT & Timbre v2.5 TTS wrapper
│   ├── indic_reasoner.py     # Indic agronomic reasoning engine
│   ├── audio_processor.py    # 8kHz telephony filter & noise utilities
│   ├── test_pipeline.py      # Automated pipeline verification tests
│   └── data/                 # Datasets for Mandi rates, crop diseases, & schemes
└── frontend/
    ├── index.html            # Modern glassmorphic interface
    ├── style.css             # Emerald & earth theme design system
    ├── app.js                # Web Audio API visualizer & API controller
    └── assets/               # Soundscapes & icons
```

---

## 🏆 Project Context
* **Built for**: [The Great Indian AI Internship Challenge](https://www.gnani.ai/great-indian-ai-internship-registration-form#terms) by **Gnani.ai**.
* **Categories**: Regional Languages, Noisy Telephonic Audio, Real-World Impact, Best Solo Project.
