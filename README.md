# Adaptive Learning LLM (VR-Based)

## Overview
This project builds an adaptive learning system using:
- VR inputs (eye, face, voice)
- Emotion detection
- RAG-based knowledge system

## Pipeline
PDF → Ingestion → Chunking → Embedding → Retrieval → LLM → Adaptive Response

## Setup
pip install -r requirements.txt

## Run
python -m src.ingestion.ingestion_step1