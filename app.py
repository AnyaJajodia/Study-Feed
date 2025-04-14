from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, flash, url_for
from flask import jsonify
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import json
import os
import openai
import requests
from datetime import datetime
from google.cloud import texttospeech
import random

print("Current working directory:", os.getcwd())
load_dotenv()
print("Loaded OpenAI API Key:", os.getenv("OPENAI_API_KEY"))
print("Loaded Google API Key:", os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
print("DID API KEY:", os.getenv("DID_API_KEY"))

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py', silent=False)
app.config['AUDIOS_FOLDER'] = os.path.join(app.root_path, 'static', 'audios')
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///studyreels.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    level = db.Column(db.String(50))
    file_count = db.Column(db.Integer, default=0)
    progress = db.Column(db.Integer, default=0)
    reels = db.relationship('Reel', backref='feed', lazy=True, cascade="all, delete-orphan")

class Reel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)  # New column for the brief description
    content = db.Column(db.Text, nullable=False)  # This will now store the 'teaching' text
    audio = db.Column(db.String(300))
    video = db.Column(db.String(300))  # Path/URL to the generated video
    feed_id = db.Column(db.Integer, db.ForeignKey('feed.id'), nullable=False)
    comments = db.relationship('Comment', backref='reel', lazy=True, cascade="all, delete-orphan")


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reel_id = db.Column(db.Integer, db.ForeignKey('reel.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


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
@app.route('/for_you')
def for_you():
    query = request.args.get('search_query', '').strip().lower()
    if query:
        feeds = Feed.query.filter(Feed.name.ilike(f'%{query}%')).all()
    else:
        feeds = Feed.query.all()
    return render_template('for_you.html', feeds=feeds)


@app.route('/make_new')
def make_new():
    return render_template('make_new_feed.html')


@app.route('/delete_feed/<int:feed_id>')
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
def resume_feed(feed_id):
    feed = Feed.query.get_or_404(feed_id)
    return render_template('feed_reels.html', feed=feed)


@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/add_comment', methods=['POST'])
def add_comment():
    reel_id = request.form.get('reel_id')
    comment_text = request.form.get('comment')
    
    if not reel_id or not comment_text:
        return jsonify({'status': 'error', 'message': 'Missing reel id or comment'}), 400

    try:
        reel_id_int = int(reel_id)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid reel id'}), 400

    new_comment = Comment(reel_id=reel_id_int, content=comment_text)
    db.session.add(new_comment)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Comment added', 'comment': {
        'id': new_comment.id,
        'content': new_comment.content
    }})

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
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
    # file upload removed – we now only use topic.
    if not topic:
        flash('Topic is required to generate a feed.', 'danger')
        return redirect(url_for('make_new'))

    # Create Feed record.
    new_feed = Feed(name=topic, level=level, file_count=0)
    db.session.add(new_feed)
    db.session.commit()  # new_feed now has an id.

    # Generate reels using OpenAI (or your preferred generation function)
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
        
        # Randomly select one video from static/videos folder.
        videos_dir = os.path.join(app.root_path, 'static', 'videos')
        video_files = [f for f in os.listdir(videos_dir) if f.endswith('.mp4')]
        if video_files:
            chosen_video = random.choice(video_files)
            video_url = url_for('static', filename='videos/' + chosen_video)
        else:
            video_url = ""
        
        # Generate audio using Google TTS helper.
        audio_filename = f"{uuid.uuid4()}.mp3"
        audio_url = generate_voiceover(teaching_text, audio_filename)
        
        new_reel = Reel(
            title=title,
            description=description,
            content=teaching_text,
            video=video_url,
            audio=audio_url,
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



# def generate_image(prompt_text):
#     detailed_prompt = (
#         f"Create an educational illustration that visually represents the following concept: {prompt_text}. "
#         "The style should be clean and modern, with clear diagrams or icons suitable for an educational app. "
#         "Focus on clarity, simplicity, and visual appeal. Do not include too much text, if possible none."
#     )
#     try:
#         response = openai.Image.create(
#             prompt=detailed_prompt,
#             n=1,
#             size="512x512"  # You can adjust the size as needed
#         )
#         # Extract the URL from the response
#         image_url = response['data'][0]['url']
#         return image_url
#     except Exception as e:
#         print("Error generating image:", e)
#         # Return a fallback image if there’s an error
#         return "https://via.placeholder.com/350x150"


if __name__ == '__main__':
    app.run(debug=True)
