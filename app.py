from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from groq import Groq
from textblob import TextBlob
import tempfile
import json
from werkzeug.utils import secure_filename
import traceback
import warnings
import requests
from dotenv import load_dotenv
import time
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()

app = Flask(__name__, 
           static_folder='static',
           template_folder='.')

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25MB max for Vercel
app.config['UPLOAD_FOLDER'] = '/tmp/uploads' if os.environ.get('VERCEL') else 'uploads'

# Groq API Configuration (free Whisper transcription + chat) 
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_CHAT_MODEL = os.getenv('GROQ_CHAT_MODEL', 'llama-3.3-70b-versatile')

# Deferred Groq client initialization to avoid import-time errors
_groq_client = None

def get_groq_client():
    """Lazily initialize and return the Groq client"""
    global _groq_client
    if _groq_client is None and GROQ_API_KEY:
        try:
            _groq_client = Groq(api_key=GROQ_API_KEY)
        except Exception as e:
            print(f"Failed to initialize Groq client: {e}")
            return None
    return _groq_client

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

print("AI Speech Analyzer ready (using Groq Whisper API for transcription)")

# Allowed file extensions (now includes video)
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a', 'mp4', 'mov', 'avi', 'mkv', 'wmv', 'flv', 'webm', 'ogg', '3gp', 'aac', 'flac'}

# Filler words list for detection
FILLER_WORDS = [
    "um", "uh", "like", "you know", "actually", "basically", "so", "well",
    "yeah", "okay", "right", "I mean", "sort of", "kind of", "you see", 
    "anyway", "obviously", "literally", "totally", "absolutely"
]

def detect_filler_words(text):
    """Detect filler words in text and return analysis"""
    import re
    
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    words = text.split()
    total_words = len(words)
    
    filler_instances = []
    filler_count = 0
    filler_stats = {}
    
    # Check for single word fillers
    for i, word in enumerate(words):
        clean_word = re.sub(r'[^\w\s]', '', word.lower())
        if clean_word in FILLER_WORDS:
            filler_instances.append({
                'word': word,
                'position': i,
                'type': 'single'
            })
            filler_count += 1
            filler_stats[clean_word] = filler_stats.get(clean_word, 0) + 1
    
    # Check for multi-word fillers
    multi_word_fillers = ["you know", "I mean", "sort of", "kind of", "you see"]
    for filler in multi_word_fillers:
        filler_lower = filler.lower()
        start = 0
        while True:
            pos = text_lower.find(filler_lower, start)
            if pos == -1:
                break
            filler_instances.append({
                'word': filler,
                'position': pos,
                'type': 'multi'
            })
            filler_count += 1
            filler_stats[filler_lower] = filler_stats.get(filler_lower, 0) + 1
            start = pos + len(filler)
    
    # Calculate statistics
    percentage = (filler_count / total_words * 100) if total_words > 0 else 0
    
    return {
        'instances': filler_instances,
        'count': filler_count,
        'percentage': round(percentage, 2),
        'stats': filler_stats,
        'total_words': total_words
    }

def highlight_filler_words(text):
    """Highlight filler words in text with HTML spans"""
    import re
    
    highlighted_text = text
    
    # Sort fillers by length (longest first) to avoid nested replacements
    sorted_fillers = sorted(FILLER_WORDS, key=len, reverse=True)
    
    for filler in sorted_fillers:
        # Create case-insensitive pattern with word boundaries
        if " " in filler:
            # Multi-word filler
            pattern = r'\b' + re.escape(filler) + r'\b'
        else:
            # Single word filler
            pattern = r'\b' + re.escape(filler) + r'\b'
        
        def replace_func(match):
            return f'<span class="filler-word" data-filler="{filler.lower()}">{match.group()}</span>'
        
        highlighted_text = re.sub(pattern, replace_func, highlighted_text, flags=re.IGNORECASE)
    
    return highlighted_text

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
    """Lightweight audio validation with estimated duration"""
    try:
        # Basic file size validation
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            return False, "Audio file is empty", 0
        if file_size < 1000:  # Less than 1KB
            return False, "Audio file is too small", 0
            
        # Estimate duration based on file size (~16KB per second for compressed audio)
        estimated_duration = max(1, file_size / 16000)  # Minimum 1 second
        return True, f"Audio validated (estimated {estimated_duration:.1f}s)", estimated_duration
    except Exception as e:
        return False, f"Error processing audio file: {str(e)}", 0

def format_duration_simple(total_seconds):
    """Simple duration formatting for MM:SS format"""
    if total_seconds <= 0:
        return "0:00"
    
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    return f"{minutes}:{seconds:02d}"

def calculate_speech_score(total_words, unique_words, filler_count, sentiment_polarity):
    """Calculate speech score based on analysis metrics"""
    score = 100
    # Reduce score for filler words
    score -= filler_count * 3
    # Vocabulary richness
    vocab_score = (unique_words / total_words) * 100 if total_words > 0 else 0
    # Sentiment bonus
    if sentiment_polarity > 0:
        score += 5
    # Clarity adjustment
    if filler_count > 5:
        score -= 5
    # Limit score
    score = max(0, min(100, score))
    return round(score), round(vocab_score)

def get_speech_level(score):
    """Determine speaker level based on score"""
    if score >= 90:
        return "Excellent Speaker"
    elif score >= 75:
        return "Confident Speaker"
    elif score >= 60:
        return "Developing Speaker"
    else:
        return "Needs Improvement"

def get_speech_feedback(score):
    """Generate feedback based on speech score"""
    if score >= 90:
        return "Outstanding speech with strong clarity and vocabulary."
    elif score >= 75:
        return "Good speech. Reducing filler words will improve it further."
    elif score >= 60:
        return "Speech is understandable but can improve clarity and confidence."
    else:
        return "Try practicing more and reduce filler words for better communication."

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
            # Check if Groq API is configured
            groq_client = get_groq_client()
            if groq_client is None:
                return jsonify({'error': 'Groq API key not configured. Add GROQ_API_KEY to environment variables.'}), 500
            
            # Validate audio file
            print(f"Processing audio file: {filename}")
            is_valid, message, estimated_duration = validate_audio(audio_path)
            
            if not is_valid:
                return jsonify({'error': message}), 400
            
            print(f"Audio validated: {message}")
            
            # Transcribe using Groq Whisper API
            with open(audio_path, 'rb') as audio_file:
                transcription_result = groq_client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), audio_file.read()),
                    model="whisper-large-v3-turbo",
                    response_format="verbose_json"
                )
            
            text = transcription_result.text.strip() if transcription_result.text else ""
            groq_duration = getattr(transcription_result, 'duration', 0) or 0
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
            
            # Word Frequency Analysis (without pandas)
            words = text.lower().split()
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            # Get top 10 words
            word_frequency = dict(sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            
            # Calculate statistics
            total_words = len(words)
            unique_words = len(set(words))
            avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
            
            # Use the best available duration
            final_duration = estimated_duration if estimated_duration > 0 else groq_duration
            duration_formatted = format_duration_simple(final_duration)
            
            # Filler word analysis
            filler_analysis = detect_filler_words(text)
            highlighted_text = highlight_filler_words(text)
            
            # Calculate speech score
            speech_score, vocab_score = calculate_speech_score(
                total_words, unique_words, filler_analysis['count'], polarity
            )
            clarity_score = max(0, 100 - (filler_analysis['count'] * 5))
            confidence_score = 80 if polarity > 0 else 60
            
            # Prepare response
            response_data = {
                'transcription': text,
                'highlighted_transcription': highlighted_text,
                'sentiment': {
                    'polarity': polarity,
                    'sentiment': sentiment
                },
                'wordFrequency': word_frequency,
                'fillerAnalysis': {
                    'count': filler_analysis['count'],
                    'percentage': filler_analysis['percentage'],
                    'stats': filler_analysis['stats'],
                    'instances': filler_analysis['instances'],
                    'rate_per_minute': round((filler_analysis['count'] / (final_duration / 60)) if final_duration > 0 else 0, 1)
                },
                'speechScore': {
                    'overall': speech_score,
                    'level': get_speech_level(speech_score),
                    'feedback': get_speech_feedback(speech_score),
                    'vocabScore': vocab_score,
                    'clarityScore': clarity_score,
                    'confidenceScore': confidence_score
                },
                'statistics': {
                    'totalWords': total_words,
                    'uniqueWords': unique_words,
                    'averageWordLength': round(avg_word_length, 1),
                    'duration': duration_formatted,
                    'wordsPerSecond': round(total_words / final_duration if final_duration > 0 else 0, 2)
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
        if analysis_data is None:
            analysis_data = {}
            
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
        print(f"DEBUG: Processing user message: '{message}'")
        print(f"DEBUG: Groq API key present: {bool(GROQ_API_KEY and GROQ_API_KEY.strip())}")
        # If Groq API is available, use it
        if GROQ_API_KEY and GROQ_API_KEY.strip():
            return generate_groq_response(message, analysis_data, chat_history)
        else:
            print("DEBUG: No valid Groq API key - using fallback response system")
            return generate_fallback_response(message, analysis_data)
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return generate_fallback_response(message, analysis_data)

def generate_groq_response(message, analysis_data, chat_history):
    """Generate response using Groq API"""
    try:
        # Handle None analysis_data
        if analysis_data is None:
            analysis_data = {}
        
        # Handle None chat_history
        if chat_history is None:
            chat_history = []
        
        # Prepare enhanced context that handles general questions
        transcription = analysis_data.get('transcription', '')
        has_speech_data = bool(transcription and transcription.strip())
        
        if has_speech_data:
            speech_context = f"""You have analyzed the user's speech with this data:
Transcription: {transcription[:300]}...
Sentiment: {analysis_data.get('sentiment', {}).get('sentiment', 'neutral')} (polarity: {analysis_data.get('sentiment', {}).get('polarity', 0):.3f})
Word Count: {analysis_data.get('statistics', {}).get('totalWords', 0)}
Vocabulary: {analysis_data.get('statistics', {}).get('uniqueWords', 0)} unique words
Duration: {analysis_data.get('statistics', {}).get('duration', 'Unknown')}"""
        else:
            speech_context = "No speech analysis data is currently available."
            
        context = f"""You are an intelligent AI assistant specializing in speech analysis and communication. You can discuss any topic the user asks about, while being especially helpful with speech, communication, language, and personal development topics.

{speech_context}

Guidelines:
- Answer any question the user asks, whether about speech analysis, general topics, or personal advice
- Be conversational, helpful, and encouraging
- When relevant, connect responses to communication or speaking skills
- Keep responses under 250 words
- Be knowledgeable across various subjects like technology, science, health, education, career advice, etc.
- Always provide practical, actionable advice when possible"""
        
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
        
        # Make API request to Groq
        try:
            groq_client = get_groq_client()
            if not groq_client:
                return jsonify({'error': 'Groq API not available'}), 500
            completion = groq_client.chat.completions.create(
                model=GROQ_CHAT_MODEL,
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )
            
            if completion.choices and len(completion.choices) > 0:
                ai_response = completion.choices[0].message.content
                return ai_response
            else:
                print("Groq API: No response choices available")
                return generate_fallback_response(message, analysis_data)
                
        except Exception as api_error:
            print(f"Groq API request error: {api_error}")
            return generate_fallback_response(message, analysis_data)
            
    except Exception as e:
        print(f"Groq API error: {e}")
        return generate_fallback_response(message, analysis_data)

def generate_fallback_response(message, analysis_data):
    """Generate comprehensive local fallback response for any type of question"""
    message_lower = message.lower().strip()
    print(f"DEBUG: Fallback processing message: '{message_lower}'")
    
    # Check if we're in fallback mode due to missing API key
    api_status = " (Note: Configure Groq API key for enhanced AI responses)" if not (GROQ_API_KEY and GROQ_API_KEY.strip()) else ""
    
    # Greeting responses
    if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']):
        return f"Hello! 👋 I'm your AI speech analysis assistant. I can help you with speech analysis, communication tips, or answer any questions you have. What would you like to discuss today?{api_status}"
    
    # PRIORITIZE: Speech improvement questions (must come before general speech analysis)
    elif any(combo in message_lower for combo in ['improve in my speech', 'improve my speech', 'speech improvement', 'suggestion which i want to improve', 'things i want to improve']):
        print("DEBUG: Routing to speech improvement (personal_development)")
        return handle_personal_development(message_lower)
    
    # Personal development & life advice (general improvement questions)
    elif any(word in message_lower for word in ['improve', 'better', 'tips', 'advice', 'help', 'motivation', 'confidence', 'goal', 'habit', 'success']) and not any(word in message_lower for word in ['sentiment', 'analysis']):
        print("DEBUG: Routing to handle_personal_development")
        return handle_personal_development(message_lower)
    
    # Speech analysis related questions (for actual analysis discussion)
    elif any(word in message_lower for word in ['sentiment', 'emotion', 'tone', 'feeling', 'analysis']) or (any(word in message_lower for word in ['speech', 'voice']) and not any(word in message_lower for word in ['improve', 'better', 'tips', 'suggestion'])):
        print("DEBUG: Routing to handle_speech_questions")
        return handle_speech_questions(message_lower, analysis_data)
    
    # Technology & AI questions
    elif any(word in message_lower for word in ['technology', 'ai', 'artificial intelligence', 'machine learning', 'python', 'programming', 'coding', 'software']):
        return handle_technology_questions(message_lower)
    
    # Health & wellness questions
    elif any(word in message_lower for word in ['health', 'exercise', 'fitness', 'diet', 'nutrition', 'mental health', 'stress', 'anxiety', 'wellness']):
        return handle_health_questions(message_lower)
    
    # Career & education questions
    elif any(word in message_lower for word in ['career', 'job', 'work', 'study', 'education', 'learning', 'skill', 'resume', 'interview', 'professional']):
        return handle_career_questions(message_lower)
    
    # Geography, countries & world knowledge
    elif any(word in message_lower for word in ['country', 'city', 'capital', 'geography', 'world', 'nation', 'continent', 'population', 'currency', 'language']):
        return handle_geography_questions(message_lower)
    
    # Current events & leaders
    elif any(word in message_lower for word in ['president', 'prime minister', 'leader', 'government', 'politics', 'election', 'governor']):
        return handle_politics_questions(message_lower)
    
    # Science & general knowledge
    elif any(word in message_lower for word in ['science', 'physics', 'chemistry', 'biology', 'math', 'history', 'geography', 'space', 'astronomy']):
        return handle_science_questions(message_lower)
    
    # Entertainment & hobbies
    elif any(word in message_lower for word in ['movie', 'music', 'book', 'game', 'hobby', 'travel', 'food', 'recipe', 'entertainment']):
        return handle_entertainment_questions(message_lower)
    
    # Questions (what, how, why, when, where)
    elif any(message_lower.startswith(word) for word in ['what', 'how', 'why', 'when', 'where', 'which', 'who']):
        return handle_question_words(message_lower)
    
    # Default conversational response
    else:
        return generate_contextual_response(message, analysis_data)

def handle_speech_questions(message_lower, analysis_data):
    """Handle speech-related questions"""
    sentiment = analysis_data.get('sentiment', {})
    sentiment_label = sentiment.get('sentiment', 'neutral')
    polarity = sentiment.get('polarity', 0)
    
    if 'sentiment' in message_lower or 'emotion' in message_lower or 'tone' in message_lower:
        if sentiment_label == 'Positive':
            return f"Your speech shows a **positive sentiment** (score: {polarity:.3f})! This indicates enthusiasm and confidence. Your upbeat tone likely engages listeners well. To maintain this energy, consider varying your pace and using expressive gestures."
        elif sentiment_label == 'Negative':
            return f"Your speech has a **critical tone** (score: {polarity:.3f}), which can be effective for serious topics. To balance this, try incorporating solution-focused language and acknowledging positive aspects when appropriate."
        else:
            return f"Your speech maintains a **balanced, neutral tone** (score: {polarity:.3f}). This objectivity works well for informational content. Consider adding emotional emphasis in key moments to increase engagement."
    else:
        return "I can help analyze various aspects of your speech including tone, sentiment, word choice, pacing, and delivery. What specific aspect of speech analysis interests you most?"

def handle_technology_questions(message_lower):
    """Handle technology-related questions"""
    if 'ai' in message_lower or 'artificial intelligence' in message_lower:
        return "AI is transforming many fields, including speech analysis! It helps us understand language patterns, sentiment, and communication effectiveness. AI can process vast amounts of speech data to provide insights that improve human communication. What specific aspect of AI interests you?"
    elif 'programming' in message_lower or 'coding' in message_lower:
        return "Programming is a valuable skill! Like public speaking, coding requires clear structure, logical flow, and attention to detail. Both involve breaking complex ideas into manageable parts. Are you interested in learning to code or improving your programming skills?"
    else:
        return "Technology continues to evolve rapidly, affecting how we communicate and interact. From speech recognition to real-time translation, tech is breaking down communication barriers. What technology topic would you like to explore?"

def handle_health_questions(message_lower):
    """Handle health and wellness questions"""
    if 'stress' in message_lower or 'anxiety' in message_lower:
        return "Stress and anxiety can significantly impact speech delivery. Deep breathing exercises, preparation, and practice can help. Try the 4-7-8 breathing technique: inhale for 4, hold for 7, exhale for 8. This can calm nerves before speaking. What specific situation causes you stress?"
    elif 'voice' in message_lower:
        return "Voice health is crucial for effective communication! Stay hydrated, avoid excessive throat clearing, warm up your voice with humming or gentle scales, and rest your voice when it feels strained. Good posture also supports better voice projection."
    else:
        return "Good health supports confident communication. Regular exercise, proper sleep, and stress management all contribute to clearer thinking and more effective speaking. What aspect of health and wellness interests you most?"

def handle_career_questions(message_lower):
    """Handle career and professional development questions"""
    if 'interview' in message_lower:
        return "Interview success often depends on clear communication! Practice common questions, prepare specific examples, maintain good eye contact, and speak at a measured pace. Remember: they already liked your resume, now they want to see your personality and communication skills."
    elif 'presentation' in message_lower or 'public speaking' in message_lower:
        return "Great presentations combine clear structure with engaging delivery. Start with a hook, organize in 3 main points, use stories and examples, and end with a strong call to action. Practice your transitions and timing. What type of presentation are you preparing?"
    else:
        return "Career advancement often relies on strong communication skills. Whether networking, presenting ideas, or leading teams, your ability to articulate thoughts clearly sets you apart. What aspect of professional development interests you most?"

def handle_science_questions(message_lower):
    """Handle science and knowledge questions"""
    if 'brain' in message_lower or 'neuroscience' in message_lower:
        return "The brain's language centers are fascinating! Broca's area handles speech production while Wernicke's area manages comprehension. Speech patterns can reveal cognitive processes and emotional states. This is why speech analysis provides such rich insights into human communication."
    elif 'psychology' in message_lower:
        return "Psychology plays a huge role in effective communication! Our word choice, tone, and pacing reflect our mental state and influence how others perceive us. Understanding psychology helps improve both speaking and listening skills."
    else:
        return "Science helps us understand the mechanics of communication - from acoustics and vocal anatomy to cognitive processing and social psychology. What scientific topic would you like to explore?"

def handle_personal_development(message_lower):
    """Handle personal development questions"""
    # Speech improvement questions
    if any(word in message_lower for word in ['speech', 'speaking', 'communication', 'presentation', 'voice', 'delivery']):
        if 'improve' in message_lower or 'better' in message_lower:
            return "**🎯 Great question! Here are key areas to improve your speech:**\n\n**📢 Delivery & Voice:**\n• **Pace**: Vary your speaking speed - slow down for important points\n• **Volume**: Project your voice clearly without shouting\n• **Tone**: Match your tone to your content (enthusiastic, serious, etc.)\n• **Pauses**: Use strategic silence to let key points sink in\n\n**💬 Content & Structure:**\n• **Clarity**: Use simple, direct language your audience understands\n• **Organization**: Start with main points, support with examples\n• **Transitions**: Connect ideas smoothly with linking phrases\n• **Engagement**: Ask questions, use stories, involve your audience\n\n**🧠 Confidence & Presence:**\n• **Body language**: Stand tall, make eye contact, use gestures\n• **Preparation**: Know your material inside and out\n• **Practice**: Rehearse out loud, record yourself\n• **Mindset**: Focus on your message, not your nerves\n\nWhat specific aspect would you like to work on most?"
        else:
            return "I can help you improve various aspects of your speech! Are you looking to work on delivery, content organization, confidence, voice projection, or something specific? Let me know what area interests you most!"
    # Confidence questions
    elif 'confidence' in message_lower:
        return "Building confidence in communication takes practice! Start with small conversations, prepare talking points for social situations, practice good posture, and remember that most people are focused on themselves, not judging you. Each successful interaction builds more confidence."
    # Motivation questions
    elif 'motivation' in message_lower:
        return "Staying motivated requires clear goals and celebrating small wins. Set specific, achievable targets for your communication skills - like speaking up once in each meeting, or giving one genuine compliment daily. Track your progress and acknowledge improvements!"
    # General improvement questions
    elif 'improve' in message_lower or 'better' in message_lower:
        return "**🌟 Here are proven ways to improve yourself:**\n\n**🎯 Set Clear Goals:**\n• Define specific, measurable objectives\n• Break big goals into smaller, actionable steps\n• Track your progress regularly\n\n**💪 Build Good Habits:**\n• Start with one small change at a time\n• Be consistent - even 10 minutes daily helps\n• Focus on progress, not perfection\n\n**📚 Keep Learning:**\n• Read books, take courses, watch tutorials\n• Learn from others who excel in areas you want to improve\n• Practice new skills regularly\n\n**🤝 Communication Skills:**\n• Listen actively to others\n• Practice speaking clearly and confidently\n• Work on body language and presence\n\nWhat specific area would you like to focus on improving?"
    else:
        return "Personal growth often comes through better communication. Whether building relationships, advancing careers, or gaining confidence, how we express ourselves shapes our experiences. What area of personal development interests you most?"

def handle_entertainment_questions(message_lower):
    """Handle entertainment and hobby questions"""
    if 'music' in message_lower:
        return "Music and speech share many similarities! Both use rhythm, tone, and pacing to convey emotion. Musicians often make excellent public speakers because they understand timing and audience engagement. Do you play any instruments or have musical interests?"
    elif 'book' in message_lower:
        return "Reading enhances vocabulary and communication skills! It exposes you to different writing styles, expands knowledge, and provides conversation topics. Great communicators are often well-read. What genres do you enjoy, or are you looking for book recommendations?"
    else:
        return "Hobbies and interests make great conversation starters! They reveal personality and can help connect with others who share similar passions. What hobbies or entertainment topics interest you?"

def handle_geography_questions(message_lower):
    """Handle geography and world knowledge questions"""
    if 'capital' in message_lower:
        if 'india' in message_lower:
            return "The capital of India is **New Delhi**. While Delhi is the National Capital Territory, New Delhi specifically serves as the seat of the Indian government and houses important buildings like the Parliament House and Rashtrapati Bhavan."
        elif 'france' in message_lower:
            return "The capital of France is **Paris**, known as the 'City of Light' and famous for landmarks like the Eiffel Tower, Louvre Museum, and Notre-Dame Cathedral."
        elif 'japan' in message_lower:
            return "The capital of Japan is **Tokyo**, one of the world's most populous metropolitan areas and a major economic center in Asia."
        elif 'usa' in message_lower or 'america' in message_lower:
            return "The capital of the United States is **Washington, D.C.** (District of Columbia), which houses the White House, Capitol Building, and Supreme Court."
    elif 'population' in message_lower:
        if 'india' in message_lower:
            return "India has a population of over **1.4 billion people**, making it the most populous country in the world as of 2023, having surpassed China."
        elif 'world' in message_lower:
            return "The world population is approximately **8 billion people** as of 2023, with India and China being the most populous countries."
    elif 'language' in message_lower:
        if 'india' in message_lower:
            return "India has **22 official languages** including Hindi and English. Hindi is the most widely spoken, but India recognizes hundreds of regional languages and dialects, reflecting its incredible linguistic diversity."
    else:
        return "I can help with geographical information about countries, capitals, populations, languages, and more! What specific place or geographical fact are you curious about?"

def handle_politics_questions(message_lower):
    """Handle political and leadership questions"""
    if 'president of india' in message_lower:
        return "The current President of India is **Droupadi Murmu**, who took office on July 25, 2022. She is India's 15th President and the first tribal woman to hold this office."
    elif 'prime minister of india' in message_lower:
        return "The current Prime Minister of India is **Narendra Modi**, who has been in office since May 2014. He represents the Bharatiya Janata Party (BJP)."
    elif 'chief minister of india' in message_lower:
        return "India doesn't have a single 'Chief Minister' for the entire country - India has a **Prime Minister** (Narendra Modi) who leads the central government, and each of the 28 states has its own Chief Minister. Did you mean the Prime Minister of India, or are you asking about a specific state's Chief Minister?"
    elif 'governor of india' in message_lower:
        return "India doesn't have a single 'Governor' - it has a **President** as head of state and state governors for each of its 28 states. Did you mean the President of India or a specific state's governor?"
    elif 'president of usa' in message_lower or 'president of america' in message_lower:
        return "The current President of the United States is **Joe Biden**, who took office on January 20, 2021. He is the 46th President of the United States."
    else:
        return "I can provide information about world leaders, government structures, and political systems. Which country's leadership or political system are you asking about?"

def handle_question_words(message_lower):
    """Handle questions starting with question words with specific knowledge"""
    
    # India-specific questions
    if 'governor of india' in message_lower or 'indian governor' in message_lower:
        return "India doesn't have a single 'Governor' - it has a **President** as the head of state. The current President of India is **Droupadi Murmu** (since July 2022). India also has state governors for each state - there are 28 states, each with their own governor. Did you mean the President of India or a specific state's governor?"
    
    if 'president of india' in message_lower:
        return "The current President of India is **Droupadi Murmu**, who took office on July 25, 2022. She is India's 15th President and the first tribal woman to hold this office. The President of India serves as the ceremonial head of state."
        
    if 'prime minister of india' in message_lower:
        return "The current Prime Minister of India is **Narendra Modi**, who has been in office since May 2014. He represents the Bharatiya Janata Party (BJP) and is currently serving his second term after winning the 2019 general elections."
    
    # World leaders and geography
    if 'president of' in message_lower:
        if 'usa' in message_lower or 'america' in message_lower or 'united states' in message_lower:
            return "The current President of the United States is **Joe Biden**, who took office on January 20, 2021. He is the 46th President of the United States."
        else:
            return "I'd be happy to help with information about world leaders! Which specific country's president are you asking about? I can provide current information about many countries."
    
    if 'capital of' in message_lower:
        if 'india' in message_lower:
            return "The capital of India is **New Delhi**. While Delhi is the National Capital Territory, New Delhi specifically serves as the seat of the Indian government and houses important buildings like the Parliament House and Rashtrapati Bhavan (President's residence)."
        elif 'france' in message_lower:
            return "The capital of France is **Paris**, known as the 'City of Light' and famous for landmarks like the Eiffel Tower, Louvre Museum, and Notre-Dame Cathedral."
        elif 'japan' in message_lower:
            return "The capital of Japan is **Tokyo**, one of the world's most populous metropolitan areas and a major economic center in Asia."
        else:
            return "I can help you with capital cities! Which country's capital are you asking about? I know the capitals of many countries around the world."
    
    # Time and date questions
    if 'time' in message_lower or 'date' in message_lower:
        if 'what time' in message_lower:
            return "I don't have access to real-time data, but the current date in our conversation is March 10, 2026. For accurate current time, please check your device's clock or search online."
        elif 'what date' in message_lower:
            return "Based on our conversation context, today is **March 10, 2026**. This is the date reference I'm working with in our session."
    
    # Science questions
    if any(word in message_lower for word in ['sun', 'moon', 'earth', 'solar system', 'planet']):
        if 'how far' in message_lower and 'sun' in message_lower:
            return "The Sun is approximately **93 million miles** (150 million kilometers) away from Earth. This distance is called an Astronomical Unit (AU) and is used as a standard measurement for distances in our solar system."
        elif 'planets' in message_lower:
            return "Our solar system has **8 planets**: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune. They orbit the Sun in that order from closest to farthest."
    
    # Technology questions
    if 'how does' in message_lower and any(word in message_lower for word in ['internet', 'computer', 'ai', 'phone']):
        if 'internet' in message_lower:
            return "The internet works through a global network of interconnected computers and servers. Data is broken into small packets, sent through various routes (cables, fiber optics, satellite), and reassembled at the destination. It's like a massive postal system for digital information!"
        elif 'ai' in message_lower:
            return "AI works by processing large amounts of data to find patterns and make predictions. Machine learning algorithms train on examples to learn tasks like speech recognition, image analysis, or language processing - similar to how this speech analyzer learns to understand your communication patterns!"
    
    # General question starters
    if message_lower.startswith('who'):
        if any(word in message_lower for word in ['invented', 'created', 'founded']):
            return "I'd be happy to help with historical information! Who specifically are you asking about? Whether it's inventors, founders, creators, or historical figures, I can provide information about many notable people."
        else:
            return "Great question about a person! Could you be more specific about who you're asking about? I can provide information about world leaders, historical figures, inventors, artists, and many other notable people."
    
    elif message_lower.startswith('what'):
        if 'is' in message_lower:
            return "I'd be happy to explain what something is! Could you be more specific about what concept, object, or idea you'd like me to define or explain?"
        else:
            return "I can help explain what various things are, how they work, or their significance. What specific topic would you like me to clarify? I'm knowledgeable about science, technology, history, geography, and many other subjects."
    
    elif message_lower.startswith('where'):
        if 'is' in message_lower:
            return "I can help with geographical information! Are you asking about the location of a city, country, landmark, or something else? Please be more specific and I'll provide the location details."
        else:
            return "I'd be happy to help with location-based questions! Where specifically are you asking about? Whether it's countries, cities, landmarks, or geographical features, I can provide information."
    
    elif message_lower.startswith('when'):
        return "I can help with dates and historical timelines! What specific event, invention, or historical moment are you asking about? I can provide information about when many important things happened."
    
    elif message_lower.startswith('how'):
        return "That's a great question! I'd be happy to explain how various things work. Could you be more specific about what process, concept, or system you'd like me to explain?"
    
    elif message_lower.startswith('why'):
        return "Understanding the 'why' behind things is fascinating! What specific phenomenon, decision, or concept would you like me to explain the reasons for?"
    
    # Default for unmatched questions
    else:
        return "I'm here to help answer your questions! I can discuss topics like world geography, current events, science, technology, history, and much more. Could you rephrase your question or be more specific? I'll do my best to provide a helpful answer."

def generate_contextual_response(message, analysis_data):
    """Generate a contextual response for general conversation"""
    has_speech_data = bool(analysis_data.get('transcription', '').strip())
    
    if has_speech_data:
        return f"I'm here to help with any questions you have! I can discuss your speech analysis, provide communication tips, or chat about any topic that interests you. Your recent speech analysis shows some interesting patterns - feel free to ask about those, or we can explore any other subject. What's on your mind?"
    else:
        return f"I'm your AI assistant and I'm here to help! Whether you want to discuss speech analysis, communication skills, technology, health, career advice, or any other topic, I'm ready to provide helpful insights and answer your questions. What would you like to talk about?"

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
        'groq_configured': get_groq_client() is not None,
        'version': '1.0.0'
    })

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum file size is 25MB.'}), 413

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