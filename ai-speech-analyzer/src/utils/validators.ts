export function validateAudioFile(file: File): boolean {
    const validFormats = ['audio/mpeg', 'audio/wav', 'audio/ogg'];
    return validFormats.includes(file.type);
}

export function validateSpeechInput(input: string): boolean {
    return input.trim().length > 0 && input.length <= 500; // Example validation: non-empty and max length of 500 characters
}