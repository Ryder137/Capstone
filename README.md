# UniCare - Mental Health Support Platform

A Flask-based mental health support platform that provides users with various tools and resources for managing their mental well-being.

## Features

- User authentication (login/signup)
- Mental health assessment
- Journaling feature
- Mental health games
- Chatbot support
- Breathing exercises
- Doctor directory
- Progress tracking

## Deployment

This application is deployed on Vercel. Follow these steps to deploy your own instance:

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Copy your Supabase URL and anon key
3. Create a new project on Vercel:
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Connect your GitHub repository
4. In Vercel dashboard, add environment variables:
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase anon key
5. Deploy the project

## Local Development

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your Supabase credentials
5. Run the application:
   ```bash
   python app.py
   ```

The application will be available at `http://localhost:5000`

## Tech Stack

- Backend: Flask
- Database: Supabase (PostgreSQL)
- AI: Google's Gemini API
- Hosting: Vercel
