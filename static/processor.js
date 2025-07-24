// Testklasse, damit es auch in Firefox funktioniert. Hat aber andere Probleme gemacht.

class AudioProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.port.onmessage = (event) => {
            // You can receive config here if needed
        };
    }

    process(inputs) {
        const input = inputs[0];
        if (input.length > 0) {
            const channelData = input[0];
            const int16Buffer = new Int16Array(channelData.length);
            for (let i = 0; i < channelData.length; i++) {
                int16Buffer[i] = Math.max(-32768, Math.min(32767, channelData[i] * 32768));
            }

            this.port.postMessage(int16Buffer);
        }
        return true;
    }
}

registerProcessor('audio-processor', AudioProcessor);