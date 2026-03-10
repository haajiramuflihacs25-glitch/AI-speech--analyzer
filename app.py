from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import whisper
from textblob import TextBlob
import pandas as pd
import tempfile
import json
from werkzeug.utils import secure_filename
import traceback
import librosa
import numpy as np
import warnings
from scipy import signal
import requests
from dotenv import load_dotenv
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()

app = Flask(__name__, 
           static_folder='static',
           template_folder='.')

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB max file size for video
app.config['UPLOAD_FOLDER'] = 'uploads'

# OpenRouter AI Configuration
OPENROUTER_API_KEY = os.getenv('OPEN_ROUTER_API_KEY')
OPENROUTER_MODEL = os.getenv('OPEN_ROUTER_AI_MODEL', 'openai/gpt-3.5-turbo')
OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1/chat/completions'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load Whisper model (using tiny for better compatibility)
print("Loading AI speech model...")
try:
    model = whisper.load_model("tiny")
    print("Whisper 'tiny' model loaded successfully!")
except Exception as e:
    print(f"Failed to load tiny model: {e}")
    try:
        model = whisper.load_model("base")
        print("Whisper 'base' model loaded successfully!")
    except Exception as e2:
        print(f"Failed to load base model: {e2}")
        model = None

# Allowed file extensions (now includes video)
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a', 'mp4', 'mov', 'avi', 'mkv', 'wmv', 'flv', 'webm', 'ogg', '3gp', 'aac', 'flac'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_audio_from_video(video_path, output_audio_path):
    """Extract audio from video file using ffmpeg-python or moviepy"""
    try:
        import moviepy.editor as mp
        video = mp.VideoFileClip(video_path)
        audio = video.audio
        audio.write_audiofile(output_audio_path, logger=None, verbose=False)
        audio.close()
        video.close()
        return True, "Audio extracted successfully"
    except ImportError:
        # Fallback to ffmpeg if moviepy is not available
        try:
            import subprocess
            command = [
                'ffmpeg', '-i', video_path,
                '-ab', '160k', '-ac', '2', '-ar', '16000',
                '-vn', output_audio_path, '-y'
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                return True, "Audio extracted successfully"
            else:
                return False, f"FFmpeg error: {result.stderr}"
        except Exception as e:
            return False, f"Audio extraction failed: {str(e)}"
    except Exception as e:
        return False, f"Error extracting audio: {str(e)}"

def is_video_file(filename):
    """Check if file is a video file"""
    video_extensions = {'mp4', 'mov', 'avi', 'mkv', 'wmv', 'flv', 'webm', '3gp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in video_extensions

def generate_ai_insights(transcription, sentiment_data, word_freq):
    """Generate AI-powered insights using OpenRouter API"""
    if not OPENROUTER_API_KEY:
        return [{"title": "AI Integration", "content": "OpenRouter API key not configured. Please add your API key to the .env file."}]
    
    try:
        # Prepare context for AI analysis
        top_words = ', '.join(list(word_freq.keys())[:5])
        
        prompt = f"""Analyze the following speech transcription and provide insights:

Transcription: "{transcription[:500]}..."
Sentiment: {sentiment_data['sentiment']} (Polarity: {sentiment_data['polarity']:.3f})
Top words: {top_words}

Provide 3-4 brief insights about:
1. Communication style and tone
2. Key themes or topics discussed  
3. Emotional indicators and engagement level
4. Potential areas for improvement or notable strengths

Format as JSON with 'title' and 'content' fields for each insight."""

        headers = {
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'http://localhost:5000',
            'X-Title': 'AI Speech Analyzer'
        }

        data = {
            'model': OPENROUTER_MODEL,
            'messages': [{
                'role': 'user',
                'content': prompt
            }],
            'max_tokens': 500,
            'temperature': 0.7
        }

        response = requests.post(OPENROUTER_BASE_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            # Try to parse as JSON, fallback to plain text
            try:
                insights = json.loads(ai_response)
                return insights if isinstance(insights, list) else [insights]
            except json.JSONDecodeError:
                # Parse plain text response
                lines = ai_response.strip().split('\n')
                insights = []
                current_insight = {"title": "AI Analysis", "content": ""}
                
                for line in lines:
                    if line.strip():
                        if any(num in line for num in ['1.', '2.', '3.', '4.']):
                            if current_insight["content"]:
                                insights.append(current_insight)
                            current_insight = {"title": line.split('.', 1)[1].strip() if '.' in line else "Insight", "content": ""}
                        else:
                            current_insight["content"] += line.strip() + " "
                
                if current_insight["content"]:
                    insights.append(current_insight)
                    
                return insights if insights else [{"title": "AI Analysis", "content": ai_response}]
        else:
            return [{"title": "AI Error", "content": f"API request failed: {response.status_code}"}]
            
    except requests.Timeout:
        return [{"title": "AI Timeout", "content": "AI analysis request timed out. Please try again."}]
    except Exception as e:
        return [{"title": "AI Error", "content": f"AI analysis failed: {str(e)}"}]

def extract_audio_from_video(video_path, output_audio_path):
    """Extract audio from video file using ffmpeg-python or moviepy"""
    try:
        import moviepy.editor as mp
        video = mp.VideoFileClip(video_path)
        audio = video.audio
        audio.write_audiofile(output_audio_path, logger=None, verbose=False)
        audio.close()
        video.close()
        return True, "Audio extracted successfully"
    except ImportError:
        # Fallback to ffmpeg if moviepy is not available
        try:
            import subprocess
            command = [
                'ffmpeg', '-i', video_path,
                '-ab', '160k', '-ac', '2', '-ar', '16000',
                '-vn', output_audio_path, '-y'
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                return True, "Audio extracted successfully"
            else:
                return False, f"FFmpeg error: {result.stderr}"
        except Exception as e:
            return False, f"Audio extraction failed: {str(e)}"
    except Exception as e:
        return False, f"Error extracting audio: {str(e)}"

def is_video_file(filename):
    """Check if file is a video file"""
    video_extensions = {'mp4', 'mov', 'avi', 'mkv', 'wmv', 'flv', 'webm', '3gp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in video_extensions

def generate_ai_insights(transcription, sentiment_data, word_freq):
    """Generate AI-powered insights using OpenRouter API"""
    if not OPENROUTER_API_KEY:
        return [{"title": "AI Integration", "content": "OpenRouter API key not configured. Please add your API key to the .env file."}]
    
    try:
        # Prepare context for AI analysis
        top_words = ', '.join(list(word_freq.keys())[:5])
        
        prompt = f"""Analyze the following speech transcription and provide insights:

Transcription: "{transcription[:500]}..."
Sentiment: {sentiment_data['sentiment']} (Polarity: {sentiment_data['polarity']:.3f})
Top words: {top_words}

Provide 3-4 brief insights about:
1. Communication style and tone
2. Key themes or topics discussed  
3. Emotional indicators and engagement level
4. Potential areas for improvement or notable strengths

Format as JSON with 'title' and 'content' fields for each insight."""

        headers = {
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'http://localhost:5000',
            'X-Title': 'AI Speech Analyzer'
        }

        data = {
            'model': OPENROUTER_MODEL,
            'messages': [{
                'role': 'user',
                'content': prompt
            }],
            'max_tokens': 500,
            'temperature': 0.7
        }

        response = requests.post(OPENROUTER_BASE_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            # Try to parse as JSON, fallback to plain text
            try:
                insights = json.loads(ai_response)
                return insights if isinstance(insights, list) else [insights]
            except json.JSONDecodeError:
                # Parse plain text response
                lines = ai_response.strip().split('\n')
                insights = []
                current_insight = {"title": "AI Analysis", "content": ""}
                
                for line in lines:
                    if line.strip():
                        if any(num in line for num in ['1.', '2.', '3.', '4.']):
                            if current_insight["content"]:
                                insights.append(current_insight)
                            current_insight = {"title": line.split('.', 1)[1].strip() if '.' in line else "Insight", "content": ""}
                        else:
                            current_insight["content"] += line.strip() + " "
                
                if current_insight["content"]:
                    insights.append(current_insight)
                    
                return insights if insights else [{"title": "AI Analysis", "content": ai_response}]
        else:
            return [{"title": "AI Error", "content": f"API request failed: {response.status_code}"}]
            
    except requests.Timeout:
        return [{"title": "AI Timeout", "content": "AI analysis request timed out. Please try again."}]
    except Exception as e:
        return [{"title": "AI Error", "content": f"AI analysis failed: {str(e)}"}]
    """Validate and preprocess audio file with multiple fallback strategies"""
    try:
        # Strategy 1: Load with librosa (most robust)
        audio, sr = librosa.load(filepath, sr=16000)  # Whisper expects 16kHz
        
        # Check if audio is not empty
        if len(audio) == 0:
            return False, "Audio file is empty or corrupted", None
            
        # Check if audio is too short
        if len(audio) < sr * 0.5:  # Minimum 0.5 seconds
            return False, "Audio file is too short (minimum 0.5 seconds required)", None
            
        # Check if audio is too long
        if len(audio) > sr * 10 * 60:  # Maximum 10 minutes for stability
            return False, "Audio file is too long (maximum 10 minutes allowed)", None
        
        # Normalize audio to prevent clipping
        audio = audio / (np.abs(audio).max() + 1e-8)
        
        # Apply basic noise reduction (simple high-pass filter)
        from scipy import signal
        sos = signal.butter(1, 80, 'hp', fs=sr, output='sos')
        audio = signal.sosfilt(sos, audio)
        
        # Ensure audio is not all zeros after processing
        if np.abs(audio).max() < 1e-6:
            return False, "Audio contains no detectable signal", None
            
        return True, f"Audio validated: {len(audio)/sr:.1f}s duration", audio
        
    except Exception as e:
        return False, f"Error processing audio file: {str(e)}", None

@app.route('/')
def index():
    """Serve the main webpage"""
    return send_from_directory('.', 'index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_audio():
    """Analyze uploaded audio file"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload an audio file.'}), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        # If it's a video file, extract audio first
        audio_path = temp_path
        if is_video_file(filename):
            print(f"Video file detected: {filename}. Extracting audio...")
            audio_filename = f"extracted_{filename.rsplit('.', 1)[0]}.wav"
            audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
            
            success, message = extract_audio_from_video(temp_path, audio_path)
            if not success:
                return jsonify({'error': f'Failed to extract audio from video: {message}'}), 400
            print(f"Audio extraction successful: {message}")
        
        try:
            # Check if model is loaded
            if model is None:
                return jsonify({'error': 'AI model failed to load. Please restart the server.'}), 500
            
            # Validate audio file
            print(f"Processing audio file: {filename}")
            is_valid, message, audio_data = validate_audio(audio_path)
            
            if not is_valid:
                return jsonify({'error': message}), 400
            
            print(f"Audio validated: {message}")
            
            # Try multiple transcription strategies
            result = None
            transcription_strategies = [
                ("file_path_simple", lambda: model.transcribe(audio_path, fp16=False, verbose=False)),
                ("file_path_detailed", lambda: model.transcribe(audio_path, fp16=False, language="en", task="transcribe", verbose=False)),
                ("audio_array", lambda: model.transcribe(audio_data, fp16=False, verbose=False)),
                ("audio_array_english", lambda: model.transcribe(audio_data, fp16=False, language="en", verbose=False))
            ]
            
            for strategy_name, strategy_func in transcription_strategies:
                try:
                    print(f"Trying transcription strategy: {strategy_name}...")
                    result = strategy_func()
                    print(f"Strategy {strategy_name} succeeded!")
                    break
                except Exception as e:
                    print(f"Strategy {strategy_name} failed: {str(e)}")
                    continue
            
            if result is None:
                return jsonify({'error': 'All transcription methods failed. The audio file may be corrupted or in an unsupported format.'}), 500
            
            text = result.get("text", "").strip()
            print(f"Transcription completed: '{text[:100]}...' ({len(text)} characters)")
            
            # Check if transcription is empty
            if not text:
                text = "No speech detected in the audio file. Please try with a clearer audio recording."
            
            # Sentiment Analysis using TextBlob
            analysis = TextBlob(text)
            polarity = analysis.sentiment.polarity
            
            if polarity > 0:
                sentiment = "Positive"
            elif polarity < 0:
                sentiment = "Negative"
            else:
                sentiment = "Neutral"
            
            # Word Frequency Analysis
            words = text.lower().split()
            df = pd.DataFrame(words, columns=["word"])
            word_count = df["word"].value_counts().head(10)
            
            # Convert to dictionary for JSON response
            word_frequency = word_count.to_dict()
            
            # Calculate statistics
            total_words = len(words)
            unique_words = len(set(words))
            avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
            
            # Get duration from Whisper result if available
            duration = result.get("duration", 0)
            duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}" if duration else "Unknown"
            
            # Prepare response
            response_data = {
                'transcription': text,
                'sentiment': {
                    'polarity': polarity,
                    'sentiment': sentiment
                },
                'wordFrequency': word_frequency,
                'statistics': {
                    'totalWords': total_words,
                    'uniqueWords': unique_words,
                    'averageWordLength': round(avg_word_length, 1),
                    'duration': duration_str
                }
            }
            
            return jsonify(response_data)
            
        except Exception as e:
            print(f"Analysis error: {str(e)}")
            traceback.print_exc()
            return jsonify({'error': f'Error analyzing audio: {str(e)}'}), 500
            
        finally:
            # Clean up temporary files
            if os.path.exists(temp_path):
                os.remove(temp_path)
            # Clean up extracted audio file if it's different from temp_path
            if 'audio_path' in locals() and audio_path != temp_path and os.path.exists(audio_path):
                os.remove(audio_path)
    
    except Exception as e:
        print(f"Request error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Request error: {str(e)}'}), 500

@app.route('/api/ai-insights', methods=['POST'])
def get_ai_insights():
    """Generate AI insights for transcription"""
    try:
        data = request.get_json()
        if not data or 'transcription' not in data:
            return jsonify({'error': 'Transcription data required'}), 400
            
        transcription = data['transcription']
        sentiment_data = data.get('sentiment', {'sentiment': 'Unknown', 'polarity': 0})
        word_frequency = data.get('wordFrequency', {})
        
        insights = generate_ai_insights(transcription, sentiment_data, word_frequency)
        
        return jsonify({'insights': insights})
        
    except Exception as e:
        print(f"AI insights error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to generate AI insights: {str(e)}'}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None,
        'version': '1.0.0'
    })

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum file size is 100MB.'}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("Starting AI Speech Analyzer Web Server...")
    print("Server will be available at: http://localhost:5000")
    print("Upload folder:", app.config['UPLOAD_FOLDER'])
    
    # Run the Flask development server
    app.run(debug=True, host='0.0.0.0', port=5000)