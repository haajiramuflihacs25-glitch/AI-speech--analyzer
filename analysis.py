import whisper
from textblob import TextBlob
import pandas as pd
import matplotlib.pyplot as plt

print("Loading AI speech model...")

model = whisper.load_model("base")

print("Analyzing speech...")

result = model.transcribe("speech.wav")

text = result["text"]

print("\nTranscription Result:")
print(text)

# Sentiment Analysis
analysis = TextBlob(text)

print("\nSentiment Analysis:")
print("Polarity:", analysis.sentiment.polarity)

if analysis.sentiment.polarity > 0:
    print("Sentiment: Positive")
elif analysis.sentiment.polarity < 0:
    print("Sentiment: Negative")
else:
    print("Sentiment: Neutral")

# Word Frequency
words = text.lower().split()

df = pd.DataFrame(words, columns=["word"])

word_count = df["word"].value_counts().head(10)

print("\nTop Words:")
print(word_count)

# Visualization
word_count.plot(kind="bar")

plt.title("Most Used Words in Speech")
plt.xlabel("Words")
plt.ylabel("Frequency")

plt.show()
from wordcloud import WordCloud
import matplotlib.pyplot as plt

wordcloud = WordCloud(width=800, height=400, background_color="white").generate(text)

plt.figure(figsize=(10,5))
plt.imshow(wordcloud)
plt.axis("off")
plt.title("Speech Word Cloud")
plt.show()
filler_words = [
    "um", "uh", "erm", "ah", "eh", "hmm", "mm",
    "like", "actually", "basically", "literally",
    "seriously", "honestly", "well", "so", "right",
    "okay", "ok", "yeah",
    "you know", "i mean", "kind of", "sort of",
    "you see", "to be honest", "believe me",
    "at the end of the day", "the thing is",
    "you know what i mean"
]
def detect_filler_words(text):
    words = text.lower().split()
    found_fillers = []

    for word in words:
        if word in filler_words:
            found_fillers.append(word)

    return found_fillers
def highlight_filler_words(text):
    highlighted_text = text

    for word in filler_words:
        highlighted_text = highlighted_text.replace(
            word,
            f"[{word}]"
        )

    return highlighted_text
result = model.transcribe("speech.wav")
speech_text = result["text"]
fillers = detect_filler_words(speech_text)

print("\nFiller Words Found:", fillers)
print("Total Filler Words:", len(fillers))
highlighted_text = highlight_filler_words(speech_text)

print("\nHighlighted Speech:")
print(highlighted_text)
import librosa
audio_file = "speech.wav"

audio, sr = librosa.load(audio_file)
duration = librosa.get_duration(y=audio, sr=sr)
minutes = int(duration // 60)
seconds = int(duration % 60)

speech_duration = f"{minutes} min {seconds} sec"
print("Speech Duration:", speech_duration)
result = model.transcribe("speech.wav")
speech_text = result["text"]
import librosa

audio_file = "speech.wav"

audio, sr = librosa.load(audio_file)
duration = librosa.get_duration(y=audio, sr=sr)

minutes = int(duration // 60)
seconds = int(duration % 60)

speech_duration = f"{minutes} min {seconds} sec"

print("Speech Duration:", speech_duration)

def calculate_speech_score(total_words, unique_words, filler_count, sentiment_polarity):
    
    score = 100

    # reduce score for filler words
    score -= filler_count * 3

    # vocabulary richness
    vocab_score = (unique_words / total_words) * 100

    # sentiment bonus
    if sentiment_polarity > 0:
        score += 5

    # clarity adjustment
    if filler_count > 5:
        score -= 5

    # limit score
    if score > 100:
        score = 100
    if score < 0:
        score = 0

    return round(score), round(vocab_score)
speech_score, vocab_score = calculate_speech_score(
    total_words,
    unique_words,
    filler_count,
    sentiment_polarity
)
def speech_level(score):

    if score >= 90:
        return "Excellent Speaker"
    elif score >= 75:
        return "Confident Speaker"
    elif score >= 60:
        return "Developing Speaker"
    else:
        return "Needs Improvement"
    def speech_feedback(score):

    if score >= 90:
        return "Outstanding speech with strong clarity and vocabulary."
    
    elif score >= 75:
        return "Good speech. Reducing filler words will improve it further."
    
    elif score >= 60:
        return "Speech is understandable but can improve clarity and confidence."
    
    else:
        return "Try practicing more and reduce filler words for better communication."
    
    clarity_score = 100 - (filler_count * 5)
confidence_score = 80 if sentiment_polarity > 0 else 60
vocabulary_score = (unique_words / total_words) * 100