import express from 'express';
import { json } from 'body-parser';
import { AudioService } from './services/audioService';
import { AIService } from './services/aiService';

const app = express();
const port = process.env.PORT || 3000;

app.use(json());

const audioService = new AudioService();
const aiService = new AIService();

app.post('/upload', async (req, res) => {
    try {
        const file = req.body.file; // Assuming file is sent in the request body
        const filePath = await audioService.uploadAudio(file);
        res.status(200).json({ filePath });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/analyze', async (req, res) => {
    try {
        const audioData = req.body.audioData; // Assuming audio data is sent in the request body
        const analysisResult = await aiService.analyzeAudio(audioData);
        res.status(200).json(analysisResult);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
});