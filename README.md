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

This application can be deployed on Heroku. Follow these steps to deploy your own instance:

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Copy your Supabase URL and anon key
3. Create a new Heroku app:
   - Go to [heroku.com](https://heroku.com)
   - Click "New" -> "Create new app"
   - Choose a unique app name
4. In Heroku dashboard, add environment variables:
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase anon key
5. Deploy the application:
   - Connect your GitHub repository
   - Enable automatic deploys from your main branch
   - Click "Deploy"

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
