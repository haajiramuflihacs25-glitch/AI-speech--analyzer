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