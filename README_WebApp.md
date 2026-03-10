# AI Speech Analyzer Web Application

This is a modern web interface for the AI Speech Analyzer project that provides:

## Features

- **Modern Web Interface**: Clean, responsive design with drag-and-drop file upload
- **Real-time Audio Analysis**: Upload audio files and get instant analysis results
- **Speech Transcription**: Powered by OpenAI's Whisper model
- **Sentiment Analysis**: Using TextBlob for sentiment scoring
- **Word Frequency Analysis**: Visual charts showing most common words
- **Analysis History**: Track previous analyses with local storage
- **Multiple Format Support**: WAV, MP3, M4A, MP4, MOV, AVI, MKV, WMV, FLV

## How to Run

1. **Install Dependencies**:
   ```bash
   pip install flask whisper textblob pandas werkzeug
   ```

2. **Start the Web Server**:
   ```bash
   python app.py
   ```

3. **Open in Browser**:
   Navigate to `http://localhost:5000` in your web browser

## File Structure

```
AI speech analyzer/
├── index.html          # Main webpage
├── app.py             # Flask web server
├── analysis.py        # Original CLI analysis script
├── static/
│   ├── style.css      # Webpage styling
│   └── script.js      # Frontend JavaScript
├── templates/         # (Future template storage)
├── uploads/          # Temporary file uploads
└── ai-speech-analyzer/ # TypeScript API project
```

## API Endpoints

- `GET /` - Main webpage
- `POST /api/analyze` - Analyze uploaded audio file
- `GET /api/health` - Health check

## Usage

1. **Upload Audio File**: Drag and drop or click to select an audio file
2. **Analyze**: Click the "Analyze Speech" button
3. **View Results**: See transcription, sentiment analysis, and word frequency
4. **History**: Previous analyses are saved locally in your browser

## Technical Details

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **AI Models**: 
  - Whisper (OpenAI) for speech transcription
  - TextBlob for sentiment analysis
- **Visualization**: Chart.js for word frequency charts
- **File Upload**: Supports files up to 100MB

## Integration

The web interface integrates seamlessly with your existing Python analysis script, providing a user-friendly way to access all the AI speech analysis features through a modern web browser.