// Global variables
let selectedFile = null;
let analysisHistory = [];
let mediaRecorder = null;
let recordedChunks = [];
let recordingStartTime = null;
let recordingTimer = null;
let recordedBlob = null;

// DOM elements
const uploadArea = document.getElementById('uploadArea');
const audioFile = document.getElementById('audioFile');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const analyzeBtn = document.getElementById('analyzeBtn');
const loadingSection = document.getElementById('loadingSection');
const resultsSection = document.getElementById('resultsSection');
const progressBar = document.getElementById('progressBar');

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    loadHistory();
    checkMicrophoneSupport();
});

// Setup event listeners
function setupEventListeners() {
    // File input change event
    audioFile.addEventListener('change', handleFileSelect);
    
    // Drag and drop events
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    
    // Click to select file
    uploadArea.addEventListener('click', () => audioFile.click());
}

// Handle file selection
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        selectedFile = file;
        displayFileInfo(file);
        enableAnalyzeButton();
    }
}

// Handle drag over
function handleDragOver(event) {
    event.preventDefault();
    uploadArea.classList.add('drag-over');
}

// Handle drag leave
function handleDragLeave(event) {
    event.preventDefault();
    uploadArea.classList.remove('drag-over');
}

// Handle drop
function handleDrop(event) {
    event.preventDefault();
    uploadArea.classList.remove('drag-over');
    
    const file = event.dataTransfer.files[0];
    if (file && isValidAudioFile(file)) {
        selectedFile = file;
        displayFileInfo(file);
        enableAnalyzeButton();
    } else {
        showNotification('Please select a valid audio file', 'error');
    }
}

// Check if file is valid audio/video file
function isValidAudioFile(file) {
    const validTypes = ['audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/m4a', 'audio/aac', 'audio/ogg', 'audio/flac', 'audio/webm',
                       'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska', 'video/x-ms-wmv', 'video/webm', 'video/3gpp'];
    const validExtensions = ['.wav', '.mp3', '.m4a', '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.ogg', '.3gp', '.aac', '.flac'];
    
    return validTypes.includes(file.type) || validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
}

// Display file information
function displayFileInfo(file) {
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    fileInfo.style.display = 'flex';
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Enable analyze button
function enableAnalyzeButton() {
    analyzeBtn.disabled = false;
    analyzeBtn.style.opacity = '1';
}

// Main analyze function
async function analyzeAudio() {
    if (!selectedFile) {
        showNotification('Please select an audio file first', 'error');
        return;
    }

    // Show loading section
    showLoading();
    
    try {
        // Simulate progress
        simulateProgress();
        
        // Upload file and get analysis results
        const analysisResult = await processAudioFile(selectedFile);
        
        // Display results
        displayResults(analysisResult);
        
        // Add to history
        addToHistory(selectedFile.name, analysisResult);
        
        // Hide loading and show results
        hideLoading();
        showResults();
        
    } catch (error) {
        console.error('Analysis error:', error);
        hideLoading();
        showNotification('Error analyzing audio file: ' + error.message, 'error');
    }
}

// Process audio file (real backend integration)
async function processAudioFile(file) {
    try {
        // Create FormData to send file to backend
        const formData = new FormData();
        formData.append('file', file);
        
        // Send file to Flask backend for analysis
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Analysis failed');
        }
        
        const results = await response.json();
        return results;
        
    } catch (error) {
        console.error('Error processing audio file:', error);
        throw error;
    }
}

// Show loading section
function showLoading() {
    loadingSection.style.display = 'block';
    resultsSection.style.display = 'none';
    progressBar.style.width = '0%';
}

// Hide loading section
function hideLoading() {
    loadingSection.style.display = 'none';
}

// Show results section
function showResults() {
    resultsSection.style.display = 'block';
}

// Simulate progress bar
function simulateProgress() {
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress >= 100) {
            progress = 100;
            clearInterval(interval);
        }
        progressBar.style.width = progress + '%';
    }, 200);
}

// Display analysis results
function displayResults(results) {
    // Display plain transcription (no highlighting)
    document.getElementById('transcriptionText').textContent = results.transcription;
    
    // Display highlighted transcription in filler analysis section
    const fillerHighlightEl = document.getElementById('fillerHighlightedText');
    if (results.highlighted_transcription) {
        fillerHighlightEl.innerHTML = results.highlighted_transcription;
    } else {
        fillerHighlightEl.textContent = results.transcription;
    }
    
    // Display filler word analysis
    if (results.fillerAnalysis) {
        displayFillerAnalysis(results.fillerAnalysis);
    }
    
    // Display sentiment analysis
    const polarityScore = document.getElementById('polarityScore');
    const sentimentResult = document.getElementById('sentimentResult');
    const sentimentBar = document.getElementById('sentimentBar');
    
    polarityScore.textContent = results.sentiment.polarity.toFixed(3);
    sentimentResult.textContent = results.sentiment.sentiment;
    sentimentResult.className = 'sentiment ' + results.sentiment.sentiment.toLowerCase();
    
    // Update sentiment bar
    const barWidth = Math.abs(results.sentiment.polarity) * 100;
    const barColor = results.sentiment.polarity > 0 ? '#002147' : 
                     results.sentiment.polarity < 0 ? '#8b0000' : '#5a6577';
    
    sentimentBar.style.width = barWidth + '%';
    sentimentBar.style.backgroundColor = barColor;
    
    // Display word frequency chart
    createWordFrequencyChart(results.wordFrequency);
    
    // Display statistics
    document.getElementById('totalWords').textContent = results.statistics.totalWords;
    document.getElementById('uniqueWords').textContent = results.statistics.uniqueWords;
    document.getElementById('avgWordLength').textContent = results.statistics.averageWordLength;
    document.getElementById('speechDuration').textContent = results.statistics.duration;
    
    // Display word stats
    displayWordStats(results.wordFrequency);
    
    // Show floating AI icon and prepare initial insights
    showFloatingAIIcon(results);
}

// Display filler word analysis
function displayFillerAnalysis(fillerAnalysis) {
    // Update filler statistics
    document.getElementById('fillerCount').textContent = fillerAnalysis.count;
    document.getElementById('fillerPercentage').textContent = fillerAnalysis.percentage + '%';
    document.getElementById('fillerRate').textContent = fillerAnalysis.rate_per_minute;
    
    // Update progress bar and level
    updateFillerProgress(fillerAnalysis.percentage);
    
    // Display filler breakdown if there are fillers
    if (fillerAnalysis.count > 0) {
        displayFillerBreakdown(fillerAnalysis.stats);
    }
    
    // Generate and display recommendations
    displayFillerRecommendations(fillerAnalysis);
}

// Update filler progress bar and level
function updateFillerProgress(percentage) {
    const progressFill = document.getElementById('fillerProgressFill');
    const levelElement = document.getElementById('fillerLevel');
    
    let level, levelClass;
    
    if (percentage <= 5) {
        level = 'Excellent';
        levelClass = 'excellent';
    } else if (percentage <= 10) {
        level = 'Good';
        levelClass = 'good';
    } else if (percentage <= 15) {
        level = 'Needs Improvement';
        levelClass = 'needs-improvement';
    } else {
        level = 'Poor';
        levelClass = 'poor';
    }
    
    // Update progress bar
    progressFill.style.width = Math.min(percentage, 20) / 20 * 100 + '%';
    progressFill.className = `filler-progress-fill ${levelClass}`;
    
    // Update level text
    levelElement.textContent = level;
    levelElement.className = `filler-level ${levelClass}`;
}

// Display filler word breakdown
function displayFillerBreakdown(fillerStats) {
    const wordsList = document.getElementById('fillerWordsList');
    wordsList.innerHTML = '';
    
    // Convert stats to array and sort by count
    const fillerArray = Object.entries(fillerStats).sort((a, b) => b[1] - a[1]);
    
    fillerArray.forEach(([word, count]) => {
        const tag = document.createElement('div');
        tag.className = 'filler-word-tag';
        tag.innerHTML = `
            ${word}
            <span class="filler-word-count">${count}</span>
        `;
        wordsList.appendChild(tag);
    });
}

// Display filler recommendations
function displayFillerRecommendations(fillerAnalysis) {
    const tipsContainer = document.getElementById('fillerTips');
    const tips = [];
    
    if (fillerAnalysis.percentage <= 5) {
        tips.push('🎉 Excellent speaking! Your filler word usage is very low.');
        tips.push('💪 Keep up the great work with clear, confident speech.');
    } else if (fillerAnalysis.percentage <= 10) {
        tips.push('👍 Good job! Your filler word usage is reasonable.');
        tips.push('🎯 Try to be more aware of occasional fillers to improve further.');
    } else if (fillerAnalysis.percentage <= 15) {
        tips.push('⚠️ You have a moderate amount of filler words.');
        tips.push('🎯 Practice pausing instead of using fillers.');
        tips.push('📝 Record yourself regularly to build awareness.');
    } else {
        tips.push('🚨 High filler word usage detected.');
        tips.push('⏸️ Practice pausing for 1-2 seconds instead of using fillers.');
        tips.push('🎤 Try speaking slower to give yourself time to think.');
        tips.push('📖 Practice reading aloud to improve fluency.');
    }
    
    // Add rate-specific tips
    if (fillerAnalysis.rate_per_minute > 10) {
        tips.push('⚡ You\'re using fillers very frequently. Focus on breathing and pacing.');
    }
    
    tipsContainer.innerHTML = '';
    tips.forEach(tip => {
        const tipElement = document.createElement('div');
        tipElement.className = 'filler-tip';
        tipElement.textContent = tip;
        tipsContainer.appendChild(tipElement);
    });
}



// Method switching functions
function switchMethod(method) {
    const uploadMethod = document.getElementById('uploadMethod');
    const recordMethod = document.getElementById('recordMethod');
    const toggleBtns = document.querySelectorAll('.toggle-btn');
    
    // Reset active states
    uploadMethod.classList.remove('active');
    recordMethod.classList.remove('active');
    toggleBtns.forEach(btn => btn.classList.remove('active'));
    
    if (method === 'upload') {
        uploadMethod.classList.add('active');
        document.querySelector('.toggle-btn:first-child').classList.add('active');
    } else if (method === 'record') {
        recordMethod.classList.add('active');
        document.querySelector('.toggle-btn:last-child').classList.add('active');
    }
}

// Microphone functions
function checkMicrophoneSupport() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        const recordMethod = document.getElementById('recordMethod');
        recordMethod.innerHTML = `
            <div class="method-header">
                <i class="fas fa-microphone-slash"></i>
                <h3>Recording Not Available</h3>
            </div>
            <div class="recording-area">
                <p>Microphone recording is not supported in this browser or requires HTTPS.</p>
            </div>
        `;
    }
}

function toggleRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        stopRecording();
    } else {
        startRecording();
    }
}

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            recordedChunks = [];
            mediaRecorder = new MediaRecorder(stream);
            
            mediaRecorder.ondataavailable = function(event) {
                if (event.data.size > 0) {
                    recordedChunks.push(event.data);
                }
            };
            
            mediaRecorder.onstop = function() {
                recordedBlob = new Blob(recordedChunks, { type: 'audio/wav' });
                const audioUrl = URL.createObjectURL(recordedBlob);
                
                const recordedAudio = document.getElementById('recordedAudio');
                recordedAudio.src = audioUrl;
                
                document.getElementById('recordingStatus').style.display = 'none';
                document.getElementById('recordingPreview').style.display = 'block';
                
                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
            };
            
            mediaRecorder.start();
            recordingStartTime = Date.now();
            
            // Update UI
            const recordBtn = document.getElementById('recordBtn');
            recordBtn.innerHTML = '<i class="fas fa-stop"></i><span>Stop Recording</span>';
            recordBtn.classList.add('recording');
            
            document.getElementById('recordingStatus').style.display = 'flex';
            
            // Start timer
            recordingTimer = setInterval(updateRecordingTime, 1000);
        })
        .catch(error => {
            console.error('Error accessing microphone:', error);
            showNotification('Could not access microphone. Please check permissions.', 'error');
        });
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        
        // Reset UI
        const recordBtn = document.getElementById('recordBtn');
        recordBtn.innerHTML = '<i class="fas fa-microphone"></i><span>Start Recording</span>';
        recordBtn.classList.remove('recording');
        
        clearInterval(recordingTimer);
    }
}

function updateRecordingTime() {
    if (recordingStartTime) {
        const elapsed = Date.now() - recordingStartTime;
        const minutes = Math.floor(elapsed / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);
        document.getElementById('recordingTime').textContent = 
            `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
}

function useRecording() {
    if (recordedBlob) {
        // Create a File object from the blob
        selectedFile = new File([recordedBlob], 'recording.wav', { type: 'audio/wav' });
        
        // Hide recording preview
        document.getElementById('recordingPreview').style.display = 'none';
        
        // Show file info
        displayFileInfo(selectedFile);
        enableAnalyzeButton();
        
        // Switch to upload tab to show the file info
        switchMethod('upload');
        
        showNotification('Recording ready for analysis!', 'success');
    }
}

function discardRecording() {
    recordedBlob = null;
    document.getElementById('recordingPreview').style.display = 'none';
    document.getElementById('recordedAudio').src = '';
    showNotification('Recording discarded', 'info');
}

// Global variables for AI chat
let currentAnalysisResults = null;
let aiChatHistory = [];

// Initialize AI components when DOM loads
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    loadHistory();
    checkMicrophoneSupport();
    setupAIComponents(); // Add AI setup
});

// Setup AI-related event listeners
function setupAIComponents() {
    const aiIcon = document.getElementById('aiFloatingIcon');
    const aiPanel = document.getElementById('aiSidePanel');
    const closePanelBtn = document.getElementById('closePanelBtn');
    const sendBtn = document.getElementById('sendMessageBtn');
    const userInput = document.getElementById('userMessageInput');
    
    // Show AI icon by default (always available for chat)
    aiIcon.classList.remove('hidden');
    
    // AI icon click event
    aiIcon.addEventListener('click', toggleAIPanel);
    
    // Close panel event
    closePanelBtn.addEventListener('click', closeAIPanel);
    
    // Send message events
    sendBtn.addEventListener('click', sendAIMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendAIMessage();
        }
    });
    
    // Close panel when clicking outside
    document.addEventListener('click', function(e) {
        if (!aiPanel.contains(e.target) && !aiIcon.contains(e.target) && aiPanel.classList.contains('active')) {
            closeAIPanel();
        }
    });
}

// Show analysis notification on floating AI icon
function showFloatingAIIcon(analysisResults) {
    currentAnalysisResults = analysisResults;
    const aiIcon = document.getElementById('aiFloatingIcon');
    
    // Add blinking animation to indicate new analysis is ready
    aiIcon.classList.add('blinking');
    
    // Remove blinking after a few seconds
    setTimeout(() => {
        aiIcon.classList.remove('blinking');
    }, 10000); // Blink for 10 seconds to get user's attention
    
    // Generate initial AI insights
    generateInitialInsights(analysisResults);
}

// Generate initial AI insights
async function generateInitialInsights(results) {
    try {
        const response = await fetch('/api/ai-chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: 'analyze_speech',
                analysis_data: {
                    transcription: results.transcription,
                    sentiment: results.sentiment,
                    wordFrequency: results.wordFrequency,
                    statistics: results.statistics
                }
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            // Store initial insights for when panel opens
            aiChatHistory = [{
                type: 'ai',
                content: data.response,
                timestamp: new Date()
            }];
        }
    } catch (error) {
        console.error('Error generating initial insights:', error);
        // Fallback insights
        aiChatHistory = [{
            type: 'ai',
            content: generateFallbackInsights(results),
            timestamp: new Date()
        }];
    }
}

// Generate fallback insights when AI is not available
function generateFallbackInsights(results) {
    const sentiment = results.sentiment.sentiment.toLowerCase();
    const wordCount = results.statistics.totalWords;
    const uniqueWords = results.statistics.uniqueWords;
    const topWords = Object.keys(results.wordFrequency).slice(0, 3).join(', ');
    
    let insights = `I've analyzed your speech! Here's what I found:\n\n`;
    insights += `📊 **Speech Analysis Summary:**\n`;
    insights += `• Sentiment: ${results.sentiment.sentiment} (${results.sentiment.polarity > 0 ? 'optimistic tone' : results.sentiment.polarity < 0 ? 'critical tone' : 'balanced tone'})\n`;
    insights += `• Length: ${wordCount} words with ${uniqueWords} unique terms\n`;
    insights += `• Key topics: ${topWords}\n\n`;
    
    if (sentiment === 'positive') {
        insights += `✨ Your speech has a positive, engaging tone! This suggests confidence and enthusiasm in your delivery.`;
    } else if (sentiment === 'negative') {
        insights += `🤔 Your speech has a more critical or serious tone. This could indicate analytical thinking or addressing challenges.`;
    } else {
        insights += `⚖️ Your speech maintains a balanced, neutral tone, which shows objectivity and professionalism.`;
    }
    
    insights += `\n\nFeel free to ask me questions about your speech patterns, delivery tips, or anything else!`;
    
    return insights;
}

// Toggle AI panel
function toggleAIPanel() {
    const aiIcon = document.getElementById('aiFloatingIcon');
    const aiPanel = document.getElementById('aiSidePanel');
    
    if (aiPanel.classList.contains('active')) {
        closeAIPanel();
    } else {
        openAIPanel();
    }
}

// Open AI panel
function openAIPanel() {
    const aiIcon = document.getElementById('aiFloatingIcon');
    const aiPanel = document.getElementById('aiSidePanel');
    const chatMessages = document.getElementById('aiChatMessages');
    
    // Stop blinking and show panel
    aiIcon.classList.remove('blinking');
    aiPanel.classList.add('active');
    
    // Load existing chat history
    displayChatHistory();
    
    // Show welcome message if no chat history exists
    if (aiChatHistory.length === 0) {
        const welcomeMessage = currentAnalysisResults ? 
            "👋 Hi! I've analyzed your speech and I'm ready to discuss the results. You can also ask me anything else you'd like to know!" :
            "👋 Hello! I'm your AI assistant. I can help with speech analysis, communication tips, or answer any questions you have. Feel free to ask me anything!";
            
        addMessageToChat('ai', welcomeMessage, false);
        aiChatHistory.push({
            type: 'ai',
            content: welcomeMessage,
            timestamp: new Date()
        });
    }
    
    // Focus on input
    setTimeout(() => {
        document.getElementById('userMessageInput').focus();
    }, 300);
}

// Close AI panel
function closeAIPanel() {
    const aiPanel = document.getElementById('aiSidePanel');
    aiPanel.classList.remove('active');
}

// Display chat history
function displayChatHistory() {
    const chatMessages = document.getElementById('aiChatMessages');
    chatMessages.innerHTML = '';
    
    aiChatHistory.forEach(message => {
        addMessageToChat(message.type, message.content, false);
    });
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Send AI message
async function sendAIMessage() {
    const userInput = document.getElementById('userMessageInput');
    const message = userInput.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addMessageToChat('user', message);
    
    // Store user message
    aiChatHistory.push({
        type: 'user',
        content: message,
        timestamp: new Date()
    });
    
    // Clear input
    userInput.value = '';
    
    // Show loading
    showAILoading(true);
    
    try {
        const response = await fetch('/api/ai-chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                analysis_data: currentAnalysisResults,
                chat_history: aiChatHistory.slice(-10) // Send last 10 messages for context
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to get AI response');
        }
        
        const data = await response.json();
        
        // Hide loading
        showAILoading(false);
        
        // Add AI response
        addMessageToChat('ai', data.response);
        
        // Store AI response
        aiChatHistory.push({
            type: 'ai',
            content: data.response,
            timestamp: new Date()
        });
        
    } catch (error) {
        console.error('Error sending AI message:', error);
        showAILoading(false);
        
        // Fallback response
        const fallbackResponse = generateFallbackResponse(message);
        addMessageToChat('ai', fallbackResponse);
        
        aiChatHistory.push({
            type: 'ai',
            content: fallbackResponse,
            timestamp: new Date()
        });
    }
}

// Add message to chat display
function addMessageToChat(type, content, scrollToBottom = true) {
    const chatMessages = document.getElementById('aiChatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = type === 'ai' ? 'ai-message' : 'user-message';
    
    const avatar = type === 'ai' ? 
        '<div class="ai-avatar">🤖</div>' : 
        '<div class="user-avatar">👤</div>';
    
    const formattedContent = formatMessageContent(content);
    
    messageDiv.innerHTML = `
        ${avatar}
        <div class="message-content">
            ${formattedContent}
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    
    if (scrollToBottom) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Format message content (handle markdown-like formatting)
function formatMessageContent(content) {
    // Simple markdown-like formatting
    let formatted = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
    
    return `<p>${formatted}</p>`;
}

// Show/hide AI loading indicator
function showAILoading(show) {
    const loadingDiv = document.getElementById('aiLoading');
    const sendBtn = document.getElementById('sendMessageBtn');
    
    loadingDiv.style.display = show ? 'flex' : 'none';
    sendBtn.disabled = show;
    
    if (show) {
        const chatMessages = document.getElementById('aiChatMessages');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Generate fallback response when AI is not available
function generateFallbackResponse(message) {
    const lowerMessage = message.toLowerCase();
    
    if (lowerMessage.includes('sentiment') || lowerMessage.includes('emotion')) {
        const sentiment = currentAnalysisResults?.sentiment?.sentiment || 'neutral';
        return `Your speech shows a ${sentiment.toLowerCase()} sentiment with a polarity score of ${currentAnalysisResults?.sentiment?.polarity?.toFixed(3) || '0.000'}. This indicates ${sentiment === 'Positive' ? 'optimistic and engaging' : sentiment === 'Negative' ? 'critical or serious' : 'balanced and objective'} communication.`;
    }
    
    if (lowerMessage.includes('improve') || lowerMessage.includes('better')) {
        return `To improve your speech: 1) Work on varying your tone and pace, 2) Use more descriptive language, 3) Practice clear articulation, and 4) Engage your audience with questions or stories.`;
    }
    
    if (lowerMessage.includes('words') || lowerMessage.includes('vocabulary')) {
        const stats = currentAnalysisResults?.statistics;
        return `You used ${stats?.totalWords || 'N/A'} total words with ${stats?.uniqueWords || 'N/A'} unique terms. This gives you a vocabulary diversity ratio of ${stats ? (stats.uniqueWords / stats.totalWords * 100).toFixed(1) : 'N/A'}%.`;
    }
    
    if (lowerMessage.includes('time') || lowerMessage.includes('duration')) {
        return `Your speech duration was ${currentAnalysisResults?.statistics?.duration || 'unknown'}. Consider your speaking pace and whether it allows your audience to follow along comfortably.`;
    }
    
    return `I'd be happy to help analyze your speech! You can ask me about sentiment, word choice, speaking patterns, or tips for improvement. I have access to your complete speech analysis data.`;
}

// Old function - now replaced
// AI Insights function (kept for compatibility)
async function generateAIInsights() {
    // This function is now handled by the floating icon system
    console.warn('generateAIInsights is deprecated - using floating AI icon instead');
}

// Create word frequency chart
function createWordFrequencyChart(wordFreq) {
    const ctx = document.getElementById('wordChart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (window.wordChart && typeof window.wordChart.destroy === 'function') {
        window.wordChart.destroy();
    }
    
    const words = Object.keys(wordFreq).slice(0, 10);
    const frequencies = Object.values(wordFreq).slice(0, 10);
    
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js is not loaded. Falling back to simple display.');
        displaySimpleChart(words, frequencies);
        return;
    }
    
    try {
        window.wordChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: words,
                datasets: [{
                    label: 'Frequency',
                    data: frequencies,
                    backgroundColor: 'rgba(0, 33, 71, 0.8)',
                    borderColor: 'rgba(0, 33, 71, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Top 10 Most Frequent Words'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.warn('Error creating chart with Chart.js:', error);
        displaySimpleChart(words, frequencies);
    }
}

// Fallback function to display chart without Chart.js
function displaySimpleChart(words, frequencies) {
    const canvas = document.getElementById('wordChart');
    const ctx = canvas.getContext('2d');
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Set canvas size
    canvas.width = 400;
    canvas.height = 300;
    
    // Draw simple bars
    const maxFreq = Math.max(...frequencies);
    const barWidth = (canvas.width - 60) / words.length;
    const maxBarHeight = canvas.height - 60;
    
    ctx.fillStyle = '#002147';
    ctx.font = '12px Arial';
    
    words.forEach((word, index) => {
        const barHeight = (frequencies[index] / maxFreq) * maxBarHeight;
        const x = 30 + index * barWidth;
        const y = canvas.height - 30 - barHeight;
        
        // Draw bar
        ctx.fillRect(x, y, barWidth - 2, barHeight);
        
        // Draw word label
        ctx.fillStyle = '#333';
        ctx.save();
        ctx.translate(x + barWidth/2, canvas.height - 10);
        ctx.rotate(-Math.PI/4);
        ctx.textAlign = 'right';
        ctx.fillText(word, 0, 0);
        ctx.restore();
        
        // Draw frequency label
        ctx.textAlign = 'center';
        ctx.fillText(frequencies[index], x + barWidth/2, y - 5);
        
        ctx.fillStyle = '#002147';
    });
}

// Display word statistics
function displayWordStats(wordFreq) {
    const wordStats = document.getElementById('wordStats');
    wordStats.innerHTML = '';
    
    const topWords = Object.entries(wordFreq).slice(0, 5);
    
    topWords.forEach(([word, count]) => {
        const statDiv = document.createElement('div');
        statDiv.className = 'word-stat';
        statDiv.innerHTML = `
            <span><strong>${word}</strong></span>
            <span>${count} times</span>
        `;
        wordStats.appendChild(statDiv);
    });
}

// Copy transcription to clipboard
function copyTranscription() {
    const transcriptionElement = document.getElementById('transcriptionText');
    
    // Get the text content without HTML tags
    let textToCopy;
    if (transcriptionElement.innerHTML.includes('<span')) {
        // If there are highlighted spans, get clean text content
        textToCopy = transcriptionElement.textContent || transcriptionElement.innerText;
    } else {
        // If plain text, use it directly
        textToCopy = transcriptionElement.textContent;
    }
    
    navigator.clipboard.writeText(textToCopy).then(() => {
        showNotification('Transcription copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy text:', err);
        showNotification('Failed to copy text', 'error');
    });
}

// Add analysis to history
function addToHistory(filename, results) {
    const historyItem = {
        id: Date.now(),
        filename: filename,
        timestamp: new Date().toLocaleString(),
        sentiment: results.sentiment.sentiment,
        wordCount: results.statistics.totalWords
    };
    
    analysisHistory.unshift(historyItem);
    saveHistory();
    displayHistory();
}

// Save history to localStorage
function saveHistory() {
    localStorage.setItem('speechAnalysisHistory', JSON.stringify(analysisHistory));
}

// Load history from localStorage
function loadHistory() {
    const saved = localStorage.getItem('speechAnalysisHistory');
    if (saved) {
        analysisHistory = JSON.parse(saved);
        displayHistory();
    }
}

// Display history
function displayHistory() {
    const historyList = document.getElementById('historyList');
    
    if (analysisHistory.length === 0) {
        historyList.innerHTML = '<p class="no-history">No analysis history yet. Upload and analyze your first audio file!</p>';
        return;
    }
    
    historyList.innerHTML = analysisHistory.map(item => `
        <div class="history-item">
            <div>
                <strong>${item.filename}</strong>
                <br>
                <small>${item.timestamp}</small>
            </div>
            <div>
                <span class="sentiment ${item.sentiment.toLowerCase()}">${item.sentiment}</span>
                <br>
                <small>${item.wordCount} words</small>
            </div>
        </div>
    `).join('');
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // Style the notification
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#002147' : type === 'error' ? '#8b0000' : '#0d3a6e'};
        color: white;
        padding: 15px 20px;
        border-radius: 5px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Utility function for sleep
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Add CSS for notification animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);