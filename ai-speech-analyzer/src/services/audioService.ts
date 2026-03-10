export class AudioService {
    async uploadAudio(file: File): Promise<string> {
        // Logic to upload audio file
        return "Audio uploaded successfully";
    }

    async fetchAudio(id: string): Promise<File> {
        // Logic to fetch audio file by id
        return new File([], "audioFile.mp3");
    }
}