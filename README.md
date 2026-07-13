# GenZ Cars Team

A modern car marketplace platform with AI-powered features — chatbot assistance, voice search, and comparative analysis.

## Architecture

```
genzcars-team/
├── Frontend/          # Next.js 14 (TypeScript, Tailwind, i18n)
├── Backend/           # FastAPI + Express hybrid API
├── Chatbot/           # AI chatbot for customer inquiries
├── voice assistant/   # Voice-powered search and commands
├── Comparison_Analysis/ # Vehicle comparison engine
├── infra/             # Docker and deployment configs
└── docs/              # Documentation
```

## Tech Stack

- **Frontend**: Next.js, TypeScript, Tailwind CSS, Zustand
- **Backend**: Python (FastAPI) / Node.js (Express), Supabase
- **AI**: Natural language chatbot, voice assistant
- **DevOps**: Docker, Docker Compose

## Quick Start

```bash
# Backend
cd Backend
pip install -r requirements.txt
python -m app

# Frontend
cd Frontend
npm install
npm run dev
```

## Features

- Car listing marketplace with advanced search
- AI chatbot for customer support
- Voice-activated commands
- Side-by-side vehicle comparison
- Multi-language support (i18n)
