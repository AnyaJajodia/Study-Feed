# 📚 StudyReels

**StudyReels** is an AI-powered web application that transforms academic topics into engaging, Instagram-style reels. Designed to make studying visual, interactive, and addictive, it blends synced subtitles, AI-generated voiceovers, and dynamic attention-grabbing backgrounds to deliver bite-sized learning—perfect for today’s fast-paced attention spans.

---

## 🎥 Live Demo

🔗 [Check out the beta version](https://studyfeed1.pythonanywhere.com/for_you)

---

## ✨ Features

- 📽️ **Instagram-like Reels Interface**  
  Short, scrollable reels styled like Instagram’s feed layout.

- 🧠 **AI-Generated Reels**  
  Enter a topic → AI generates subtopics and explanatory scripts.

- 🔊 **Voiceover Generation**  
  Each reel includes automatically generated and synced voiceovers.

- 📄 **Subtitles Sync**  
  Captions appear in sync with audio, centered on the reel.

- 🧩 **Visual Backgrounds**  
  Attention-holding visuals (e.g., Minecraft parkour) to improve focus.

- 💬 **Comment Panel**  
  - Real-time comments  
  - Visible custom scrollbar  
  - Full reel script shown below the comment input  
  - Shadowed UI and wider layout for readability

- 🔍 **For You / Search Page**  
  - Clean search results with persistent top-right search bar  
  - Results displayed in a scrollable, reel-style layout
 
- 💻 **Login/SignUp**  
  - Users can login to see their generated reels and statistics

- 🎨 **Polished UI**  
  - Subtle shadows, margins, and padding  
  - Responsive headers across all pages  
  - Reels nudge left when comments open for better spatial balance

---

## 🧰 Tech Stack

| Layer         | Technology                        |
|---------------|-----------------------------------|
| **Frontend**  | HTML, CSS, JavaScript             |
| **Backend**   | Flask                             |
| **Database**  | SQLAlchemy                        |
| **Voiceover** | Google Text-to-Speech (TTS)       |
| **Realtime**  | Flask-SocketIO                    |
| **Hosting**   | PythonAnywhere (Beta)             |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Virtualenv or Anaconda
- Flask, Flask-SocketIO, SQLAlchemy, OpenAI, Google Cloud TTS SDK

### Clone the repository

```bash
git clone https://github.com/yourusername/studyreels.git
cd studyreels
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Set up environment variables
Create a `.env` file and set your API keys:

```bash
OPENAI_API_KEY=your_openai_key
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/credentials.json
```

### Run the app locally

```bash
python app.py
```
---

## 🧪 Testing Tips

- Scroll through reels and confirm subtitle sync.
- Open the comment panel—check reel positioning and custom scrollbar.
- Generate a new topic feed and watch the loading progress bar.
- Try different topics and verify AI output + voice alignment.

---

## 📁 Folder Structure

/static <br>
/templates <br>
&nbsp;&nbsp;&nbsp;&nbsp;feed_reels.html <br>
&nbsp;&nbsp;&nbsp;&nbsp;make_new_feed.html <br>
&nbsp;&nbsp;&nbsp;&nbsp;search.html <br>
app.py <br>
models.py <br>
utils/ <br>
&nbsp;&nbsp;&nbsp;&nbsp;generate_feed.py <br>
&nbsp;&nbsp;&nbsp;&nbsp;voiceover.py <br>
&nbsp;&nbsp;&nbsp;&nbsp;subtitles.py <br>

---

## 📌 Known Limitations

- No playlist or collection features yet
- Currently deployed on PythonAnywhere with limited scaling

---

## 🧠 Future Plans

- 🧪 Quiz mode and study gamification
- 📈 Reel analytics dashboard
- 📚 Collaborative study playlists












