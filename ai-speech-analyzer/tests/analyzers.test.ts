import { SpeechAnalyzer } from '../src/analyzers/speechAnalyzer';
import { AudioProcessor } from '../src/analyzers/audioProcessor';
import { AnalysisResult } from '../src/models/analysisResult';
import { SpeechModel } from '../src/models/speechModel';

describe('SpeechAnalyzer', () => {
    let speechAnalyzer: SpeechAnalyzer;

    beforeEach(() => {
        speechAnalyzer = new SpeechAnalyzer();
    });

    it('should analyze speech and return an analysis result', () => {
        const input = "Hello, this is a test speech.";
        const result: AnalysisResult = speechAnalyzer.analyzeSpeech(input);
        
        expect(result).toBeDefined();
        expect(result.model.text).toBe(input);
        expect(result.confidence).toBeGreaterThan(0);
    });

    it('should return an array of analysis results', () => {
        speechAnalyzer.analyzeSpeech("First speech.");
        speechAnalyzer.analyzeSpeech("Second speech.");
        
        const results = speechAnalyzer.getAnalysisResults();
        
        expect(results.length).toBe(2);
    });
});

describe('AudioProcessor', () => {
    let audioProcessor: AudioProcessor;

    beforeEach(() => {
        audioProcessor = new AudioProcessor();
    });

    it('should process audio file', () => {
        const filePath = "path/to/audio/file.wav";
        audioProcessor.processAudio(filePath);
        
        const processedAudio = audioProcessor.getProcessedAudio();
        
        expect(processedAudio).toBeDefined();
        expect(processedAudio).toContain("processed");
    });
});