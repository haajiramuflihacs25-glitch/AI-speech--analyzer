export const config = {
    apiKey: process.env.API_KEY || 'your-default-api-key',
    environment: process.env.NODE_ENV || 'development',
    port: process.env.PORT || 3000,
    audioFilePath: process.env.AUDIO_FILE_PATH || './uploads/audio',
};