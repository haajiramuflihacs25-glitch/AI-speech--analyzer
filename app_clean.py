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

def is_video_file(filename):
    """Check if file is a video file"""
    video_extensions = {'mp4', 'mov', 'avi', 'mkv', 'wmv', 'flv', 'webm', '3gp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in video_extensions

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

def validate_audio(filepath):
    """Simple audio validation"""
    try:
        audio, sr = librosa.load(filepath, sr=16000)
        
        if len(audio) == 0:
            return False, "Audio file is empty or corrupted", None
            
        if len(audio) < sr * 0.5:
            return False, "Audio file is too short (minimum 0.5 seconds required)", None
            
        if len(audio) > sr * 10 * 60:
            return False, "Audio file is too long (maximum 10 minutes allowed)", None
        
        return True, f"Audio validated: {len(audio)/sr:.1f}s duration", audio
        
    except Exception as e:
        return False, f"Error processing audio file: {str(e)}", None

@app.route('/')
def index():
    """Serve the main webpage"""
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

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
            return jsonify({'error': 'Invalid file type. Please upload an audio or video file.'}), 400
        
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
            
            # Transcribe using Whisper
            try:
                result = model.transcribe(audio_path, fp16=False, verbose=False)
            except Exception as e:
                print(f"File transcription failed, trying audio array: {str(e)}")
                result = model.transcribe(audio_data, fp16=False, verbose=False)
            
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

@app.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    """Handle AI chat requests"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
            
        user_message = data['message']
        analysis_data = data.get('analysis_data', {})
        chat_history = data.get('chat_history', [])
        
        # Handle special analysis request
        if user_message == 'analyze_speech':
            response = generate_speech_analysis(analysis_data)
        else:
            # Generate contextual response
            response = generate_AI_response(user_message, analysis_data, chat_history)
        
        return jsonify({'response': response})
        
    except Exception as e:
        print(f"AI chat error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to process AI chat: {str(e)}'}), 500

def generate_speech_analysis(analysis_data):
    """Generate initial speech analysis"""
    try:
        transcription = analysis_data.get('transcription', '')
        sentiment = analysis_data.get('sentiment', {})
        word_freq = analysis_data.get('wordFrequency', {})
        stats = analysis_data.get('statistics', {})
        
        if not transcription:
            return "I notice there's no transcription data available. Please analyze some audio first!"
        
        # Generate comprehensive analysis
        analysis = "**🎯 Speech Analysis Complete!**\n\n"
        
        # Sentiment analysis
        sentiment_label = sentiment.get('sentiment', 'Unknown')
        polarity = sentiment.get('polarity', 0)
        
        analysis += "**📊 Sentiment Analysis:**\n"
        if sentiment_label == 'Positive':
            analysis += f"✅ Your speech has a {sentiment_label.lower()} tone (polarity: {polarity:.3f})\n"
            analysis += "This suggests enthusiasm, confidence, and engaging communication.\n\n"
        elif sentiment_label == 'Negative':
            analysis += f"⚠️ Your speech has a {sentiment_label.lower()} tone (polarity: {polarity:.3f})\n"
            analysis += "This might indicate critical thinking, addressing challenges, or serious topics.\n\n"
        else:
            analysis += f"⚖️ Your speech maintains a balanced, {sentiment_label.lower()} tone (polarity: {polarity:.3f})\n"
            analysis += "This shows objectivity and professional communication.\n\n"
        
        # Speech statistics
        total_words = stats.get('totalWords', 0)
        unique_words = stats.get('uniqueWords', 0)
        avg_length = stats.get('averageWordLength', 0)
        duration = stats.get('duration', 'Unknown')
        
        analysis += "**📈 Speech Statistics:**\n"
        analysis += f"• Length: {total_words} words over {duration}\n"
        analysis += f"• Vocabulary: {unique_words} unique words\n"
        analysis += f"• Complexity: {avg_length:.1f} avg. letters per word\n"
        
        if unique_words and total_words:
            diversity = (unique_words / total_words) * 100
            analysis += f"• Diversity: {diversity:.1f}% vocabulary variation\n\n"
        
        # Top words analysis
        if word_freq:
            top_words = list(word_freq.keys())[:5]
            analysis += f"**🔤 Key Terms:** {', '.join(top_words)}\n\n"
        
        # Personalized insights
        analysis += "**💡 Quick Insights:**\n"
        
        if diversity > 70:
            analysis += "• Excellent vocabulary diversity! Your word choice keeps listeners engaged.\n"
        elif diversity > 50:
            analysis += "• Good vocabulary range. Consider adding more descriptive terms.\n"
        else:
            analysis += "• Try using more varied vocabulary to enhance engagement.\n"
        
        if avg_length > 5:
            analysis += "• You use sophisticated, longer words - great for formal contexts.\n"
        elif avg_length < 4:
            analysis += "• Your language is clear and accessible - perfect for broad audiences.\n"
        
        analysis += "\n**Ask me anything about your speech patterns, delivery tips, or specific improvements!**"
        
        return analysis
        
    except Exception as e:
        print(f"Error generating speech analysis: {e}")
        return "I've analyzed your speech! The data shows interesting patterns. Feel free to ask me specific questions about your speaking style, word choice, or areas for improvement."

def generate_AI_response(message, analysis_data, chat_history):
    """Generate AI response based on user message and context"""
    try:
        # If OpenRouter API is available, use it
        if OPENROUTER_API_KEY:
            return generate_openrouter_response(message, analysis_data, chat_history)
        else:
            return generate_fallback_response(message, analysis_data)
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return generate_fallback_response(message, analysis_data)

def generate_openrouter_response(message, analysis_data, chat_history):
    """Generate response using OpenRouter API"""
    try:
        # Prepare context
        context = f"""You are an AI speech analysis assistant. You have analyzed the user's speech with the following data:
        
Transcription: {analysis_data.get('transcription', 'N/A')[:500]}...
Sentiment: {analysis_data.get('sentiment', {}).get('sentiment', 'N/A')} (polarity: {analysis_data.get('sentiment', {}).get('polarity', 0):.3f})
Word Count: {analysis_data.get('statistics', {}).get('totalWords', 'N/A')}
Vocabulary: {analysis_data.get('statistics', {}).get('uniqueWords', 'N/A')} unique words
Duration: {analysis_data.get('statistics', {}).get('duration', 'N/A')}
Top Words: {', '.join(list(analysis_data.get('wordFrequency', {}).keys())[:5])}

Provide helpful, encouraging, and specific advice about speech improvement, communication skills, and speaking techniques. Keep responses conversational and under 200 words."""
        
        # Build conversation history
        messages = [
            {"role": "system", "content": context}
        ]
        
        # Add recent chat history
        for msg in chat_history[-6:]:  # Last 6 messages for context
            role = "assistant" if msg['type'] == 'ai' else "user"
            messages.append({"role": role, "content": msg['content']})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Make API request
        headers = {
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'http://localhost:5000',
            'X-Title': 'AI Speech Analyzer'
        }
        
        payload = {
            'model': OPENROUTER_MODEL,
            'messages': messages,
            'max_tokens': 300,
            'temperature': 0.7
        }
        
        response = requests.post(OPENROUTER_BASE_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            return ai_response
        else:
            print(f"OpenRouter API error: {response.status_code} - {response.text}")
            return generate_fallback_response(message, analysis_data)
            
    except Exception as e:
        print(f"OpenRouter API error: {e}")
        return generate_fallback_response(message, analysis_data)

def generate_fallback_response(message, analysis_data):
    """Generate local fallback response"""
    message_lower = message.lower()
    
    # Sentiment-related questions
    if any(word in message_lower for word in ['sentiment', 'emotion', 'tone', 'feeling']):
        sentiment = analysis_data.get('sentiment', {})
        sentiment_label = sentiment.get('sentiment', 'neutral')
        polarity = sentiment.get('polarity', 0)
        
        if sentiment_label == 'Positive':
            return f"Your speech shows a **positive sentiment** (score: {polarity:.3f})! This indicates enthusiasm and confidence. Your upbeat tone likely engages listeners well. To maintain this energy, consider varying your pace and using expressive gestures."
        elif sentiment_label == 'Negative':
            return f"Your speech has a **critical tone** (score: {polarity:.3f}), which can be effective for serious topics. To balance this, try incorporating solution-focused language and acknowledging positive aspects when appropriate."
        else:
            return f"Your speech maintains a **balanced, neutral tone** (score: {polarity:.3f}). This objectivity works well for informational content. Consider adding emotional emphasis in key moments to increase engagement."
    
    # Improvement questions
    elif any(word in message_lower for word in ['improve', 'better', 'tips', 'advice', 'help']):
        suggestions = "**Here are personalized improvement tips:**\n\n"
        suggestions += "• **Vary your pace**: Slow down for important points, speed up for transitions.\n"
        suggestions += "• **Use the 'Rule of 3'**: Group ideas in threes for better memorability.\n"
        suggestions += "• **Practice active voice**: Makes your speech more direct and engaging.\n"
        suggestions += "• **Add pauses**: Strategic silence gives your audience time to process important information."
        return suggestions
    
    # General/other questions
    else:
        return f"I'm here to help with your speech analysis! I can discuss:\n\n• **Sentiment & tone** - How your message comes across\n• **Vocabulary** - Word choice and diversity analysis  \n• **Delivery tips** - Pacing, structure, and engagement\n• **Improvement strategies** - Personalized suggestions\n\nWhat specific aspect of your speech would you like to explore?"

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
        
        # Simple insights if no API key
        if not OPENROUTER_API_KEY:
            insights = [{
                "title": "Basic Analysis",
                "content": f"Your speech was {sentiment_data['sentiment'].lower()} in tone with {len(transcription.split())} words. Consider the clarity and pacing of your delivery."
            }]
        else:
            insights = [{
                "title": "AI Analysis",
                "content": "AI insights feature is available. Add your OpenRouter API key to enable detailed analysis."
            }]
        
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
    return jsonify({'error': 'File too large. Maximum file size is 200MB.'}), 413

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