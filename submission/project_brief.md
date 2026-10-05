# KisanSetu (किसान सेतु) — Project Brief & Submission Details

**Project Title**: KisanSetu (किसान सेतु) — Sovereign Vernacular AI Voice Desk for Bharat's Farmers  
**Participation Mode**: Solo Participant  
**Challenge**: [The Great Indian AI Internship Challenge](https://www.gnani.ai/great-indian-ai-internship-registration-form#terms) by Gnani.ai  

---

### 1. Problem Statement
Over 60% of India's 150+ million farmers are excluded from digital agricultural services because existing portals rely on written English or complex form navigation. When working out in agricultural fields or crowded APMC mandis, connectivity is often limited to noisy 2G/cellular channels with loud background noise (diesel tractor engines, wind, market chatter). Mainstream speech models trained on Western datasets fail on low-bandwidth Indian accents, regional dialects, and noisy acoustic conditions.

---

### 2. Solution Overview
**KisanSetu** is an ambient voice desk engineered on **Gnani Artha (India's Sovereign AI Stack)**. A farmer speaks into their phone in their native language (**Hindi, Marathi, Telugu, Kannada**). KisanSetu delivers:
1. **Live APMC Mandi Price Intelligence**: Real-time modal, minimum, and maximum rates across key regional markets (Nashik, Indore, Warangal, Khanna) with price trends.
2. **Crop Doctor (Rog Nidan)**: Instant diagnosis for crop diseases (e.g. Tomato Leaf Curl, Cotton Pink Bollworm, Wheat Yellow Rust) providing organic remedies and precise chemical spray dosages.
3. **Sarkari Yojna (Scheme & Subsidy Advisory)**: Clear eligibility checklists and toll-free helpline contacts for PM-Kisan Samman Nidhi, PM Fasal Bima Yojana, and Kisan Credit Card (KCC).

---

### 3. Gnani AI Models & Technologies Used
* **Gnani Prisma v2.5 (Speech-to-Text)**:
  - Transcribes spoken vernacular queries via HTTP REST / streaming.
  - Successfully handles code-mixed speech, regional phonetic variations, and noisy audio with verified sub-150ms processing latency.
* **Gnani Timbre v2.5 (Text-to-Speech)**:
  - Generates natural, expressive Indic voice responses using the `Nalini` voice profile.
  - Converted into instant audio streams for zero-latency browser playback.
* **Acoustic Noise & Telephony Simulator**:
  - In-memory 8kHz narrowband filter and ambient soundscape generator to test and demonstrate Prisma's noise resistance.

---

### 4. Target Users
* **Primary Users**: Smallholder farmers, rural agricultural workers, and tenant farmers across Tier 2, Tier 3, and rural India.
* **Secondary Users**: Village Level Entrepreneurs (VLEs) at Common Service Centres (CSCs), Krishi Vigyan Kendra (KVK) field extension officers, and APMC commission agents.

---

### 5. Solo Member Contribution
As a solo developer, I designed, built, and tested the full stack end-to-end:
* Integrated **Gnani Prisma v2.5** and **Gnani Timbre v2.5** APIs.
* Built the **FastAPI** backend with audio processing, telephony simulation, and the Indic agricultural reasoning engine.
* Created the curated emerald/earth **glassmorphic web dashboard** with real-time Web Audio API waveform visualizer and acoustic noise toggles.
* Prepared the comprehensive agronomic dataset (APMC Mandi rates, crop pest database, government subsidies).
* Scripted and produced the 60-second video demo and social media campaign.
