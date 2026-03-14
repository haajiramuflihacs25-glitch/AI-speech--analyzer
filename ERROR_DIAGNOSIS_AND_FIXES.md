# AI Speech Analyzer - Error Diagnosis & Fixes

## 🔴 ERRORS FOUND:

### **Error 1: ffmpeg Not Installed (ROOT CAUSE)**
```
Error: [Errno 2] No such file or directory: 'ffmpeg'
```
**Location:** `app.py` - `extract_audio_from_video()` function tries to call ffmpeg
**Why it fails:** Your system doesn't have ffmpeg installed
**Impact:** All video files (MP4, MOV, AVI, etc.) cannot be processed

**FIX FOR WINDOWS:**
```powershell
# Option 1 - Using Chocolatey (Recommended)
choco install ffmpeg

# Option 2 - Using Windows Package Manager  
winget install ffmpeg

# Option 3 - Manual Installation
# Download from: https://ffmpeg.org/download.html
# Extract and add ffmpeg.exe to System PATH
```

After installing, **RESTART your Flask server** for the system to recognize ffmpeg.

---

### **Error 2: 404 Error - API Endpoint Not Found**
```
Failed to load resource: the server responded with a status of 404 ()
/api/analyze
```
**Possible Causes:**
1. Flask server not running
2. Wrong URL being called from frontend
3. Temporary network error

**VERIFICATION:**
- Check that Flask server is running: `python app.py` 
- Verify `/api/analyze` route exists at line 230+ in `app.py` ✓ (IT DOES)
- Check browser console network tab for exact URL

---

### **Error 3: 400 Bad Request**
```
Failed to load resource: the server responded with a status of 400 ()
/api/analyze
```
**Root Causes:**
1. **Video file upload with missing ffmpeg** - Can't extract audio
2. **Empty audio file** - `validate_audio()` rejects files < 1KB
3. **Unsupported file format** - File type not in ALLOWED_EXTENSIONS
4. **Groq API key missing** - `GROQ_API_KEY` environment variable not set

**VERIFICATION CHECKLIST:**
- [ ] `ffmpeg` is installed? Run: `ffmpeg -version`
- [ ] `.env` file exists with `GROQ_API_KEY`?
- [ ] Audio file is > 1KB?
- [ ] File extension is in ALLOWED_EXTENSIONS?

---

## 🟢 QUICK FIXES:

### **Step 1: Install ffmpeg (CRITICAL)**
```powershell
# Windows - PowerShell as Admin
choco install ffmpeg
# OR
winget install ffmpeg
```

### **Step 2: Verify dependencles**
```powershell
cd "c:\Users\ELCOT\Desktop\AI speech  analyzer"
pip install -r requirements.txt
```

**Key packages needed:**
- `flask` - Web framework
- `groq` OR use requests (API calls)
- `python-dotenv` - Environment variables
- `textblob` - Sentiment analysis
- `moviepy` - Video audio extraction (fallback)
- `librosa` - Audio duration calculation

### **Step 3: Create .env file**
```
GROQ_API_KEY=your_actual_key_here
GROQ_CHAT_MODEL=llama-3.3-70b-versatile
```

### **Step 4: Test the API**
```powershell
# Start Flask server
python app.py

# In another terminal, test endpoint
$file = Get-Item "test_audio.mp3"
$form = @{
    file = [System.IO.FileStream]::new($file.FullName, 'Open', 'Read')
}
Invoke-WebRequest -Uri "http://localhost:5000/api/analyze" -Method POST -Form $form
```

---

## 📋 SYSTEM CHECK COMMANDS:

```powershell
# Check if ffmpeg is installed
ffmpeg -version

# Check Python packages
pip list | findstr flask

# Check if .env file exists
ls .env

# Test Groq API connectivity
python -c "import requests; print(requests.get('https://api.groq.com'))"

# Check Flask routes
python -c "from app import app; print(app.url_map)"
```

---

## 🎯 PRIORITY ORDER:

1. **FIRST:** Install ffmpeg (this fixes video processing)
2. **SECOND:** Verify/create .env with GROQ_API_KEY
3. **THIRD:** Restart Flask server
4. **FOURTH:** Test with audio file (not video) first
5. **FIFTH:** Test with video file to verify ffmpeg works

---

## ⚠️ COMMON MISTAKES:

| Issue | Fix |
|-------|-----|
| ffmpeg installed but still not found | Restart PowerShell/CMD after installation |
| 404 error persists | Make sure Flask is running on localhost:5000 |
| 400 error on audio upload | Check file size > 1KB and format is supported |
| "API key not configured" | Add `GROQ_API_KEY` to `.env` file |
| "Audio extraction failed" | ffmpeg not installed (Error #1) |

---
