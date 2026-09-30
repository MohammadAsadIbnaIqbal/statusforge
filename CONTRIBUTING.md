# Contributing to StatusForge

Thank you for your interest in contributing to StatusForge! This document outlines the local setup, prerequisites, and basic contribution workflow.

## Prerequisites
- Node.js 20+
- Python 3.10+
- Docker & Docker Compose

## Local Setup

### 1. Environment Configuration
Copy the environment files for both the backend and frontend:
\\\ash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
\\\

### 2. Backend & Infrastructure
To run the full backend stack (FastAPI, PostgreSQL, Redis, and ARQ background worker), use Docker Compose:
\\\ash
docker-compose up --build
\\\

### 3. Frontend
Navigate to the \rontend\ directory, install dependencies, and start the development server:
\\\ash
cd frontend
npm install
npm run dev
\\\

## Running Tests

### Backend
Navigate to the \ackend\ directory and run pytest:
\\\ash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest tests
\\\

### Frontend
Navigate to the \rontend\ directory and run vitest:
\\\ash
cd frontend
npm run test
npm run lint
npm run build
\\\

## Basic Contribution Workflow
1. Fork the repository and create your feature branch: \git checkout -b feature/my-new-feature\
2. Write clean, readable code and include tests where appropriate.
3. Ensure both backend and frontend test suites pass.
4. Push to the branch and submit a pull request against the main branch.
