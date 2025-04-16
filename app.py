from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, flash, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import json
import os
import openai
import requests
from datetime import datetime
# from google.cloud import texttospeech, speech
import random

print("Current working directory:", os.getcwd())
load_dotenv(override=True)
print("Loaded OpenAI API Key:", os.getenv("OPENAI_API_KEY"))
print("Loaded Google API Key:", os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py', silent=False)
app.config['AUDIOS_FOLDER'] = os.path.join(app.root_path, 'static', 'audios')
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///studyreels.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to use this feature.'
login_manager.login_message_category = 'warning'
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    feeds = db.relationship('Feed', backref='owner', lazy=True)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    level = db.Column(db.String(50))
    file_count = db.Column(db.Integer, default=0)
    progress = db.Column(db.Integer, default=0)
    reels = db.relationship('Reel', backref='feed', lazy=True, cascade="all, delete-orphan")
    user_id  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Reel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)  # New column for the brief description
    content = db.Column(db.Text, nullable=False)  # This will now store the 'teaching' text
    audio = db.Column(db.String(300))
    video = db.Column(db.String(300))  # Path/URL to the generated video
    subtitles = db.Column(db.Text)     # JSON string with subtitle timing
    feed_id = db.Column(db.Integer, db.ForeignKey('feed.id'), nullable=False)
    comments = db.relationship('Comment', backref='reel', lazy=True, cascade="all, delete-orphan")


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reel_id = db.Column(db.Integer, db.ForeignKey('reel.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# In-memory "database" for For You pages (feeds)
feeds = {}  # key: feed_id, value: { 'name': str, 'progress': int, 'reels': list }
next_feed_id = 1

# Dummy default reels to associate with each new feed
default_reels = [
    {'id': 1, 'title': 'Introduction', 'content': 'This is an introduction to the topic.', 'image': 'https://via.placeholder.com/350x150'},
    {'id': 2, 'title': 'Key Concept A', 'content': 'Explanation of key concept A.', 'image': 'https://via.placeholder.com/350x150'},
    {'id': 3, 'title': 'Key Concept B', 'content': 'Explanation of key concept B.', 'image': 'https://via.placeholder.com/350x150'}
]

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/')
@app.route('/for_you')
@login_required
def for_you():
    query = request.args.get('search_query', '').strip().lower()
    if query:
        feeds = Feed.query.filter(Feed.name.ilike(f'%{query}%')).all()
    else:
        feeds = Feed.query.all()
    return render_template('for_you.html', feeds=feeds)

@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('q', '').strip().lower()
    feeds = Feed.query.filter(Feed.name.ilike(f'%{query}%')).all() if query else []
    return render_template('search.html', query=query, feeds=feeds)



@app.route('/make_new')
@login_required
def make_new():
    return render_template('make_new_feed.html')


@app.route('/delete_feed/<int:feed_id>')
@login_required
def delete_feed(feed_id):
    feed = Feed.query.get(feed_id)
    if feed:
        db.session.delete(feed)
        db.session.commit()
        flash(f"Feed '{feed.name}' deleted.", "info")
    else:
        flash("Feed not found.", "warning")
    return redirect(url_for('for_you'))


@app.route('/resume_feed/<int:feed_id>')
@login_required
def resume_feed(feed_id):
    feed = Feed.query.get_or_404(feed_id)
    return render_template('feed_reels.html', feed=feed)


@app.route('/profile')
@login_required
def profile():
    # 1) Feeds created count + list
    user_feeds = Feed.query.filter_by(user_id=current_user.id).order_by(Feed.id.desc()).all()
    feed_count = len(user_feeds)

    # 2) Recent comments (requires Comment.user_id; see note below)
    recent_comments = Comment.query\
        .filter_by(user_id=current_user.id)\
        .order_by(Comment.created_at.desc())\
        .limit(5).all()

    return render_template(
        'profile.html',
        feed_count=feed_count,
        feeds=user_feeds,
        recent_comments=recent_comments
    )

@app.route('/activity')
@login_required
def user_activity():
    activities = []
    # Feed creation events (most recent 5)
    feeds = Feed.query.filter_by(user_id=current_user.id)\
             .order_by(Feed.id.desc())\
             .limit(5).all()
    for f in feeds:
        activities.append({
            'text': f"You created “{f.name}”",
            'time': None  # we don’t have a timestamp on Feed—could add one via migration
        })

    # Comment events (most recent 5)
    comments = Comment.query.filter_by(user_id=current_user.id)\
                .order_by(Comment.created_at.desc())\
                .limit(5).all()
    for c in comments:
        reel = Reel.query.get(c.reel_id)
        delta = datetime.utcnow() - c.created_at
        minutes = int(delta.total_seconds() // 60)
        when = f"{minutes}m ago" if minutes < 60 else f"{minutes//60}h ago"
        activities.append({
            'text': f"You commented on “{reel.title}”",
            'time': when
        })

    return jsonify(activities=activities)


@app.route('/add_comment', methods=['POST'])
@login_required
def add_comment():
    reel_id = request.form.get('reel_id')
    comment_text = request.form.get('comment')
    
    if not reel_id or not comment_text:
        return jsonify({'status': 'error', 'message': 'Missing reel id or comment'}), 400

    try:
        reel_id_int = int(reel_id)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid reel id'}), 400

    new_comment = Comment(
        reel_id=reel_id_int,
        user_id=current_user.id,
        content=comment_text
    )
    db.session.add(new_comment)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Comment added', 'comment': {
        'id': new_comment.id,
        'content': new_comment.content
    }})

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get(comment_id)
    if not comment:
        return jsonify({'status': 'error', 'message': 'Comment not found'}), 404

    try:
        db.session.delete(comment)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Comment deleted', 'comment_id': comment_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500



##########################################################################

import uuid  # Import at the top if not already imported

@app.route('/generate_feed', methods=['POST'])
def generate_feed():
    topic = request.form.get('topic')
    level = request.form.get('level')
    if not topic:
        flash('Topic is required to generate a feed.', 'danger')
        return redirect(url_for('make_new'))

    new_feed = Feed(
        name=topic,
        level=level,
        user_id=current_user.id
    )
    db.session.add(new_feed)
    db.session.commit()

    reels_data = generate_feed_content(topic)
    if not reels_data:
        reels_data = [{
            "title": "Introduction",
            "description": "Default introduction reel for the topic.",
            "teaching": "This is a default introduction reel teaching content."
        }]

    for reel_data in reels_data:
        title = reel_data.get("title", "Untitled")
        description = reel_data.get("description", "")
        teaching_text = reel_data.get("teaching", "")
        
        # Randomly select one video from static/videos
        videos_dir = os.path.join(app.root_path, 'static', 'videos')
        video_files = [f for f in os.listdir(videos_dir) if f.endswith('.mp4')]
        if video_files:
            chosen_video = random.choice(video_files)
            video_url = url_for('static', filename='videos/' + chosen_video)
        else:
            video_url = ""
        
        # Generate audio using Google TTS (your existing helper)
        audio_filename = f"{uuid.uuid4()}.mp3"
        audio_url = generate_voiceover(teaching_text, audio_filename)
        
        # Get the full path to the generated audio file
        audios_folder = os.path.join(app.root_path, 'static', 'audios')
        audio_filepath = os.path.join(audios_folder, audio_filename)
        
        # Generate subtitles from the audio file
        subtitles_list = generate_subtitles(audio_filepath)
        subtitles_json = json.dumps(subtitles_list)
        
        new_reel = Reel(
            title=title,
            description=description,
            content=teaching_text,
            video=video_url,
            audio=audio_url,
            subtitles=subtitles_json,
            feed_id=new_feed.id
        )
        db.session.add(new_reel)
    db.session.commit()

    flash(f"Feed '{topic}' created successfully!", "success")
    return redirect(url_for('for_you'))



def generate_feed_content(topic):
    prompt = (
        f"Generate 5 engaging subtopics for learning about '{topic}'. "
        "For each subtopic, return an object with the keys 'title', 'description', and 'teaching'. "
        "The 'description' should be a brief overview of the subtopic in one or two sentences."
        "The 'teaching' field should contain a detailed, step-by-step explanation that teaches the subtopic as if you were giving a math lecture. "
        "For algorithmic topics (e.g. Fleury's algorithm, Hierholzer's algorithm), include explicit steps such as: "
        "1. Conditions for the algorithm to work (e.g., degree properties). "
        "2. A detailed step-by-step procedure of how the algorithm is applied, including an example and explanation of each step. "
        "For other subtopics, include practical examples and clear instructions that help the learner understand and apply the concept. "
        "Return only a JSON array with these objects and nothing else. "
        "Example output: "
        '[{"title": "Fleury\'s Algorithm", "description": "Learn how to find an Eulerian path using Fleury\'s Algorithm.", '
        '"teaching": "Step 1: Identify all vertices and count their degrees. Step 2: Verify that the graph has either 0 or 2 vertices with an odd degree. '
        'Step 3: Start at a vertex with an odd degree (if one exists) or any vertex otherwise. Step 4: Traverse the graph by choosing the next edge that is not a bridge, '
        'unless no alternative exists. Step 5: Remove the traversed edge and repeat until all edges are visited. For example, consider a graph with vertices A, B, C, and D..."}, '
        '{"title": "Hierholzer\'s Algorithm", "description": "Learn the procedure to construct Eulerian circuits using Hierholzer\'s Algorithm.", '
        '"teaching": "Step 1: Start at any vertex and follow edges to form a circuit until returning to the starting vertex. Step 2: Identify any vertex in the circuit that has remaining edges. '
        'Step 3: Starting from that vertex, form another circuit and then merge this circuit with the original. Step 4: Continue this process until all edges are included. '
        'For example, for a given graph with vertices A, B, C... explain how the circuits are formed and merged step by step."}]'
    )


    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an educational content generator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800,
        )
    except Exception as e:
        print("Error calling OpenAI API:", e)
        return []
    
    generated_text = response.choices[0].message['content']
    print("Raw generated text:", generated_text)  # for debugging
    
    # Remove markdown code fences if they exist:
    if generated_text.startswith("```"):
        # Remove first and last three backticks
        generated_text = generated_text.strip().split("\n", 1)[-1]
        # If it ends with ```
        if generated_text.endswith("```"):
            generated_text = generated_text.rsplit("```", 1)[0]
    
    generated_text = generated_text.strip()
    if not generated_text:
        print("Generated text is empty after cleanup.")
        return []
    
    try:
        reels = json.loads(generated_text)
    except json.JSONDecodeError as e:
        print("JSON decode error:", e)
        # Optionally attempt further cleanup if necessary
        try:
            start = generated_text.find('[')
            end = generated_text.rfind(']') + 1
            reels = json.loads(generated_text[start:end])
        except Exception as ex:
            print("Failed to fix JSON format:", ex)
            reels = []
    return reels


def generate_voiceover(text, filename):
    """
    Uses Google Cloud TTS to synthesize speech from the given text,
    saves the audio as an MP3 file in static/audios, and returns the file URL.
    """
    from google.cloud import texttospeech

    client = texttospeech.TextToSpeechClient()
    
    # Set up the synthesis input
    synthesis_input = texttospeech.SynthesisInput(text=text)
    
    # Configure the voice parameters (adjust language & gender as needed)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    
    # Configure the audio output
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    
    # Perform the request to synthesize speech
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    
    # Define the destination folder (static/audios)
    audios_folder = os.path.join(app.root_path, 'static', 'audios')
    if not os.path.exists(audios_folder):
        os.makedirs(audios_folder)
    
    # Save the output to a file inside the audios folder
    audio_path = os.path.join(audios_folder, filename)
    with open(audio_path, 'wb') as out:
        out.write(response.audio_content)
        print(f"Audio content written to file '{audio_path}'")
    
    # Return the URL to access the file (e.g., /static/audios/filename.mp3)
    return url_for('static', filename='audios/' + filename)

def generate_subtitles(audio_filepath):
    """
    Process the given audio file using Google Speech-to-Text to obtain
    word-level timestamps. Returns a list of dictionaries, each with
    keys: 'start', 'end', and 'word'. 
    """
    from google.cloud import speech  # Use the standard client instead of speech_v1p1beta1

    client = speech.SpeechClient()

    # Read the audio file content
    with open(audio_filepath, "rb") as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.MP3,
        sample_rate_hertz=24000,  # Adjust as appropriate for your audio file
        language_code="en-US",
        enable_word_time_offsets=True
    )

    response = client.recognize(config=config, audio=audio)
    subtitles = []
    # Loop through the results and each word in the alternative
    for result in response.results:
        alternative = result.alternatives[0]
        for word_info in alternative.words:
            start_time = word_info.start_time.total_seconds()
            end_time = word_info.end_time.total_seconds()
            word = word_info.word
            subtitles.append({"start": start_time, "end": end_time, "word": word})
    return subtitles


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('for_you'))
    if request.method == 'POST':
        username = request.form['username']
        email    = request.form['email']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'warning')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'warning')
            return redirect(url_for('register'))
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash('Registration successful.', 'success')
        return redirect(url_for('for_you'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('for_you'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user     = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('for_you'))
        flash('Invalid credentials.', 'danger')
        return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('home'))



if __name__ == '__main__':
    app.run(debug=True)
