# AI Speech Analyzer - Usage Examples

## How to Use the Enhanced Audio File Functionality

### Method 1: Command Line Argument
You can provide the audio file path directly when running the script:

```bash
python analysis.py "path/to/your/audio/file.wav"
```

Example:
```bash
python analysis.py "C:\Users\ELCOT\Desktop\speech_sample.mp3"
```

### Method 2: Interactive Input
Simply run the script and it will ask you for the audio file path:

```bash
python analysis.py
```

Then enter the path when prompted:
```
Please enter the path to your audio file:
C:\Users\ELCOT\Desktop\my_recording.wav
```

### Supported Audio Formats
- WAV (.wav)
- MP3 (.mp3)
- M4A (.m4a)
- MP4 (.mp4)
- MOV (.mov)
- AVI (.avi)
- MKV (.mkv)
- WMV (.wmv)
- FLV (.flv)

### Sample Output
```
=== AI Speech Analyzer ===
Please enter the path to your audio file:
sample_audio.wav
Loading AI speech model...
Analyzing speech from: sample_audio.wav
==================================================
TRANSCRIPTION RESULT:
==================================================
Hello, this is a sample audio file for testing the AI speech analyzer.

==================================================
ADDITIONAL INFORMATION:
==================================================
Language detected: en
Number of segments: 1

First few segments with timestamps:
  [00:00 - 00:03] Hello, this is a sample audio file for testing the AI speech analyzer.
```

### Tips
1. Use quotes around file paths that contain spaces
2. The analyzer will automatically detect the language
3. For long audio files, you'll see segments with timestamps
4. The TED dataset loading is optional and can be skipped if not needed