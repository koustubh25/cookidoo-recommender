# Recipe Recommendation System

## Why
Users need an intelligent way to discover Thermomix recipes from the Cookidoo database based on natural language queries. The current system lacks a recommendation engine that can understand user intent, combine semantic search with structured filtering, and provide personalized recipe suggestions compatible with their Thermomix TM6 device.

## What Changes
- Add a recipe recommendation engine that combines NL2SQL and vector embeddings for hybrid search
- Implement query understanding using Gemini AI to extract structured filters (dietary restrictions, cooking time, difficulty, etc.) from natural language
- Create vector similarity search using existing recipe embeddings for semantic matching
- Build result ranking and filtering logic that ensures TM6 compatibility
- Develop a chatbot interface for conversational recipe discovery
- Integrate Google Cloud AlloyDB for database operations and Vertex AI (Gemini) for AI capabilities

## Impact
- Affected specs: `recipe-recommendation` (new capability)
- Affected code: New Python modules for database connectivity, AI integration, query processing, recommendation engine, and chatbot interface
- Dependencies: Google Cloud SDK, AlloyDB connector, Vertex AI SDK, Gemini API
