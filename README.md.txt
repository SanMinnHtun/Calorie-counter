# Calorie-Counter AI AgentA streamlined, intelligent nutrition tracking application that leverages Gemini 2.5 to provide instant caloric and macronutrient analysis of meals. Built with a robust FastAPI backend and a clean, responsive frontend.

## 🚀 Overview

The Calorie-Counter AI Agent is designed to remove the friction from nutrition tracking. Instead of manually searching through food databases, users simply describe their meal, and the integrated AI agent returns a detailed breakdown of calories, protein, fats, and carbohydrates.

## 🏗️ Architecture

The system utilizes a modern, decoupled architecture ensuring low latency and high scalability.

Frontend: A lightweight, responsive interface built with vanilla HTML5, CSS3, and JavaScript. It handles user input and dynamically renders AI-generated insights via asynchronous fetch calls.Backend: A high-performance FastAPI (Python) server.

It acts as the orchestration layer—validating requests, handling prompt engineering, and managing secure communication with the AI model.

Intelligence Layer: Powered by Gemini 2.5, which acts as the core "agent." It performs semantic analysis on meal descriptions to generate structured JSON data, ensuring consistency in nutrient estimation.

Data FlowRequest: Client sends meal data to the FastAPI /analyze endpoint.Orchestration: Backend wraps the request into a system prompt tuned for nutritional accuracy.

Inference: Gemini 2.5 parses the data and returns a structured health profile.Response: API returns the structured data to the frontend for immediate display.
