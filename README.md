# AdaptiveAI - Intelligent Adaptive Tutoring System

An AI-powered personalized learning platform for Data Science, Machine Learning, and Deep Learning education.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ADAPTIVE AGENT (Orchestrator)            │
│         Analyzes learner profile → Routes to agents         │
│         Adjusts level/style → Personalizes responses        │
└─────────────────────────┬───────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ Data Science  │ │    Machine    │ │     Deep      │
│    Agent      │ │   Learning    │ │   Learning    │
│  (Supervisor) │ │    Agent      │ │    Agent      │
└───────────────┘ └───────────────┘ └───────────────┘
```

## 📁 Project Structure

```
AdaptiveAI/
├── frontend/
│   ├── index.html      # Main UI
│   ├── script.js       # Frontend logic
│   └── styles.css      # Styling
│
├── backend/
│   ├── app.py          # Flask server
│   ├── config.py       # Configuration
│   ├── database.py     # MongoDB connection
│   ├── requirements.txt
│   ├── .env.example    # Environment template
│   │
│   ├── models/
│   │   └── user.py     # User model
│   │
│   ├── routes/
│   │   ├── auth.py     # Authentication endpoints
│   │   ├── profile.py  # Profile endpoints
│   │   ├── chat.py     # AI chat endpoints
│   │   └── analytics.py # Analytics endpoints
│   │
│   └── services/
│       └── ai_agents.py # AI agent logic
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- MongoDB (local or Atlas)
- OpenAI API key

### Backend Setup

1. **Navigate to backend folder:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create .env file:**
   ```bash
   copy .env.example .env
   ```

5. **Edit .env with your settings:**
   ```env
   FLASK_SECRET_KEY=your-secret-key
   MONGODB_URI=mongodb://localhost:27017/
   MONGODB_DB_NAME=adaptiveai
   OPENAI_API_KEY=sk-your-openai-key
   ```

6. **Start MongoDB** (if using local):
   ```bash
   mongod
   ```

7. **Run the server:**
   ```bash
   python app.py
   ```
   Server runs at: http://localhost:5000

### Frontend Setup

1. **Open frontend/index.html** in browser, or use Live Server:
   - VS Code: Right-click → "Open with Live Server"
   - This will run at: http://127.0.0.1:5500

## 📡 API Endpoints

### Authentication
- `POST /api/auth/signup` - Create new user
- `POST /api/auth/login` - Login user

### Chat (AI Agents)
- `POST /api/chat/message` - Send message to AI agent
- `GET /api/chat/history/<user_id>` - Get chat history
- `POST /api/chat/analyze-progression` - Check level updates

### Analytics
- `POST /api/analytics/save` - Save quiz analytics
- `GET /api/analytics/user/<email>` - Get user analytics
- `GET /api/analytics/progress/<email>` - Get progress report
- `POST /api/analytics/webhook/n8n` - n8n webhook endpoint

### Profile
- `GET /api/profile/<user_id>` - Get user profile
- `PUT /api/profile/<user_id>` - Update profile

## 🤖 AI Agents

### Adaptive Agent (Orchestrator)
- Analyzes learner profile
- Determines teaching style (Friendly/Concise/Socratic)
- Adjusts complexity based on skill level
- Routes queries to specialized agents

### Data Science Agent (Supervisor)
- EDA, data cleaning, visualization
- Pandas, NumPy, Matplotlib, Seaborn
- Statistical analysis

### Machine Learning Agent
- Supervised/Unsupervised learning
- Scikit-learn implementation
- Model evaluation, feature engineering

### Deep Learning Agent
- Neural networks, backpropagation
- CNNs, RNNs, Transformers
- TensorFlow, PyTorch

## 🔄 n8n Integration

The system includes a webhook endpoint for n8n automation:
- `POST /api/analytics/webhook/n8n`

Use this to:
- Automatically check for level progression
- Trigger notifications
- Schedule analytics reports

## 📊 Learning Personalization

The system adapts based on:
1. **Detected Level** (from quiz) - Beginner/Intermediate/Advanced
2. **Learning Style** - Friendly/Concise/Socratic
3. **Skill Levels** - Python and Math proficiency
4. **Strongest Domain** - DS/ML/DL preference
5. **Chat History** - Context-aware responses

## 🛠️ Development

### Running in Development
```bash
# Backend
cd backend
python app.py

# Frontend (with Live Server)
cd frontend
# Use VS Code Live Server extension
```

### MongoDB Collections
- `users` - User accounts and profiles
- `analytics` - Quiz and learning analytics
- `interactions` - Chat history

## 📝 License

MIT License - See LICENSE file for details.

---
Built for graduation project | AdaptiveAI © 2026
