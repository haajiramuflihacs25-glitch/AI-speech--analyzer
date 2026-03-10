import { AudioService } from '../src/services/audioService';
import { AIService } from '../src/services/aiService';
import { AnalysisResult } from '../src/models/analysisResult';

describe('AudioService', () => {
    let audioService: AudioService;

    beforeEach(() => {
        audioService = new AudioService();
    });

    test('should upload audio file', async () => {
        const mockFile = new File(['audio content'], 'test.mp3', { type: 'audio/mp3' });
        const result = await audioService.uploadAudio(mockFile);
        expect(result).toBeDefined();
        expect(result).toMatch(/test\.mp3/);
    });

    test('should fetch audio by id', async () => {
        const mockId = '123';
        const result = await audioService.fetchAudio(mockId);
        expect(result).toBeInstanceOf(File);
    });
});

describe('AIService', () => {
    let aiService: AIService;

    beforeEach(() => {
        aiService = new AIService();
    });

    test('should analyze audio data', async () => {
        const mockAudioData = 'mockAudioData';
        const result: AnalysisResult = await aiService.analyzeAudio(mockAudioData);
        expect(result).toHaveProperty('model');
        expect(result).toHaveProperty('confidence');
        expect(result).toHaveProperty('analysisDetails');
    });

    test('should get analysis history', async () => {
        const result: AnalysisResult[] = await aiService.getAnalysisHistory();
        expect(Array.isArray(result)).toBe(true);
    });
});