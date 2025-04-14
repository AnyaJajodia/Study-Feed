import os
import time
import uuid
import requests
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DID_API_KEY = os.getenv("DID_API_KEY")
if not DID_API_KEY:
    print("DID_API_KEY not found in environment")
    exit(1)
print("Using DID_API_KEY:", DID_API_KEY)

# Build the Basic Authentication header
# NOTE: We're encoding the DID_API_KEY as-is, without appending an extra colon.
auth = base64.b64encode(DID_API_KEY.encode()).decode()
headers = {
    "Authorization": f"Basic {auth}",
    "Content-Type": "application/json"
}

# Use a publicly accessible image for the face.
# Here we are using a Wikimedia placeholder image.
face_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Portrait_placeholder.png/200px-Portrait_placeholder.png"

# Define the text input
text_input = "Hello, this is a test for D-ID API talking head video."

# Build the payload.
# If you continue getting errors, try removing the "provider" block
payload = {
    "script": {
        "type": "text",
        "input": text_input
    }, "source_url": face_url,
}

# The endpoint for creating a talk.
endpoint = "https://api.d-id.com/talks"

print("Sending POST request to D-ID API...")
response = requests.post(endpoint, json=payload, headers=headers)
if response.status_code != 200:
    print("D-ID API error:", response.text)
    exit(1)

data = response.json()
talk_id = data.get("id")
if not talk_id:
    print("No talk ID returned. Response:", data)
    exit(1)
print("Talk ID received:", talk_id)

# Poll for the talk's status until it's done.
status_endpoint = f"{endpoint}/{talk_id}"
video_url = None
for i in range(30):  # Poll for up to 60 seconds (30 * 2 seconds)
    print(f"Polling status... iteration {i+1}")
    status_response = requests.get(status_endpoint, headers=headers)
    status_data = status_response.json()
    if status_data.get("status") == "done":
        video_url = status_data.get("result_url")
        print("Video is ready!")
        break
    time.sleep(2)

if not video_url:
    print("Video did not become ready in time.")
    exit(1)

print("Video URL:", video_url)

# Download the video locally.
video_file = f"output_{uuid.uuid4()}.mp4"
print("Downloading video as:", video_file)
with requests.get(video_url, stream=True) as vid_resp:
    if vid_resp.status_code == 200:
        with open(video_file, "wb") as f:
            for chunk in vid_resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Video downloaded successfully.")
    else:
        print("Error downloading video:", vid_resp.text)
