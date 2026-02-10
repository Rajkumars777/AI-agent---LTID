/**
 * Voice Demo Page
 * Demonstrates voice interface components and functionality
 */

import React from 'react';
import { VoiceMicIndicator } from '../components/VoiceMicIndicator';
import { WakeWordAnimation } from '../components/WakeWordAnimation';
import { VoiceWaveform } from '../components/VoiceWaveform';
import { VoiceControlPanel } from '../components/VoiceControlPanel';
import { useVoiceInterface } from '../hooks/useVoiceInterface';
import '../styles/voice.css';

export default function VoiceDemo() {
    const { status, config, toggleVoiceMode, updateConfig } = useVoiceInterface();

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <div className="text-center mb-12">
                    <h1 className="text-4xl font-bold mb-4">Voice Interface Demo</h1>
                    <p className="text-gray-600 dark:text-gray-400">
                        Test the S-Tier voice capabilities with Kokoro-82M TTS and Whisper STT
                    </p>
                </div>

                {/* Main Voice Control */}
                <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 mb-8">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-2xl font-semibold">Voice Control</h2>
                        <VoiceControlPanel config={config} onConfigChange={updateConfig} />
                    </div>

                    {/* Microphone Indicator - Large */}
                    <div className="flex justify-center py-12">
                        <VoiceMicIndicator
                            status={status}
                            onToggle={toggleVoiceMode}
                            size="lg"
                        />
                    </div>

                    {/* Speaking Waveform */}
                    {status.isSpeaking && (
                        <div className="flex justify-center mt-8">
                            <VoiceWaveform isActive={status.isSpeaking} />
                        </div>
                    )}
                </div>

                {/* Status Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                    <StatusCard
                        label="Listening"
                        active={status.isListening}
                        color="blue"
                    />
                    <StatusCard
                        label="Recording"
                        active={status.isRecording}
                        color="red"
                    />
                    <StatusCard
                        label="Processing"
                        active={status.isProcessing}
                        color="yellow"
                    />
                    <StatusCard
                        label="Speaking"
                        active={status.isSpeaking}
                        color="green"
                    />
                </div>

                {/* Configuration Display */}
                <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6">
                    <h3 className="text-lg font-semibold mb-4">Current Configuration</h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                        <ConfigItem label="Wake Word" value={config.wakeWord} />
                        <ConfigItem label="Voice" value={config.voice} />
                        <ConfigItem
                            label="TTS Engine"
                            value={config.useLocalTTS ? 'Local (Kokoro)' : 'Cloud (ElevenLabs)'}
                        />
                        <ConfigItem label="Sensitivity" value={config.sensitivity.toFixed(1)} />
                    </div>
                </div>

                {/* Instructions */}
                <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6">
                    <h3 className="text-lg font-semibold mb-3 text-blue-900 dark:text-blue-100">
                        How to Use
                    </h3>
                    <ol className="list-decimal list-inside space-y-2 text-blue-800 dark:text-blue-200">
                        <li>Click the microphone button to enable voice mode</li>
                        <li>Say "{config.wakeWord}" to activate</li>
                        <li>Speak your command clearly</li>
                        <li>Wait for the response</li>
                        <li>Adjust settings using the gear icon</li>
                    </ol>
                </div>
            </div>

            {/* Wake Word Animation Overlay */}
            <WakeWordAnimation
                isDetected={status.wakeWordDetected}
                wakeWord={config.wakeWord}
            />
        </div>
    );
}

// Helper Components
function StatusCard({
    label,
    active,
    color
}: {
    label: string;
    active: boolean;
    color: 'blue' | 'red' | 'yellow' | 'green';
}) {
    const colors = {
        blue: 'bg-blue-500',
        red: 'bg-red-500',
        yellow: 'bg-yellow-500',
        green: 'bg-green-500',
    };

    return (
        <div className={`bg-white dark:bg-gray-800 rounded-lg p-4 ${active ? 'ring-2 ring-offset-2 ring-' + color + '-500' : ''}`}>
            <div className={`w-3 h-3 rounded-full mb-2 ${active ? colors[color] : 'bg-gray-300'}`} />
            <div className="text-sm font-medium">{label}</div>
            <div className="text-xs text-gray-500">{active ? 'Active' : 'Inactive'}</div>
        </div>
    );
}

function ConfigItem({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <div className="text-gray-500 dark:text-gray-400">{label}</div>
            <div className="font-medium">{value}</div>
        </div>
    );
}
