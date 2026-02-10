# Voice Interface - Component Reference

## React Components

### VoiceMicIndicator
**File**: `frontend/src/components/VoiceMicIndicator.tsx`

Microphone status indicator with color-coded states.

```tsx
<VoiceMicIndicator 
  status={voiceStatus}
  onToggle={toggleVoiceMode}
  size="lg" // 'sm' | 'md' | 'lg'
/>
```

**States**:
- 🔵 Blue (Listening) - Pulsing animation
- 🔴 Red (Recording) - Solid with pulse
- 🟡 Yellow (Processing) - Loading spinner
- 🟢 Green (Speaking) - Solid
- ⚪ Gray (Inactive) - Muted

---

### WakeWordAnimation
**File**: `frontend/src/components/WakeWordAnimation.tsx`

Full-screen overlay when wake word detected.

```tsx
<WakeWordAnimation 
  isDetected={status.wakeWordDetected}
  wakeWord="jarvis"
/>
```

Auto-dismisses after 2 seconds.

---

### VoiceWaveform
**File**: `frontend/src/components/VoiceWaveform.tsx`

Animated waveform for speaking state.

```tsx
<VoiceWaveform 
  isActive={status.isSpeaking}
  color="#10B981"
/>
```

---

### VoiceControlPanel
**File**: `frontend/src/components/VoiceControlPanel.tsx`

Settings panel for voice configuration.

```tsx
<VoiceControlPanel 
  config={voiceConfig}
  onConfigChange={updateConfig}
/>
```

**Features**:
- Wake word selection
- Voice selection (4 Kokoro voices)
- TTS mode toggle (Local/Cloud)
- Sensitivity slider (0.0-1.0)

---

## Hooks

### useVoiceInterface
**File**: `frontend/src/hooks/useVoiceInterface.ts`

State management for voice interface.

```tsx
const { status, config, toggleVoiceMode, updateConfig } = useVoiceInterface();
```

**Returns**:
- `status`: Current voice status
- `config`: Voice configuration
- `toggleVoiceMode()`: Enable/disable voice
- `updateConfig(config)`: Update settings

---

## Types

### VoiceStatus
```typescript
interface VoiceStatus {
  isListening: boolean;
  isRecording: boolean;
  isProcessing: boolean;
  isSpeaking: boolean;
  wakeWordDetected: boolean;
  isEnabled: boolean;
  currentCommand?: string;
  error?: string;
}
```

### VoiceConfig
```typescript
interface VoiceConfig {
  wakeWord: string;
  voice: string;
  useLocalTTS: boolean;
  sensitivity: number;
}
```

---

## Utility Functions

```typescript
// Get current state from status
getVoiceState(status: VoiceStatus): VoiceState

// Get color for state
getVoiceStateColor(state: VoiceState): string

// Get label for state
getVoiceStateLabel(state: VoiceState): string
```

---

## CSS Animations

**File**: `frontend/src/styles/voice.css`

- `.animate-wave` - Waveform bars
- `.animate-pulse-ring` - Recording pulse
- `.animate-ripple` - Listening ripple

---

## Demo Page

**File**: `frontend/src/pages/VoiceDemo.tsx`

Complete showcase of all voice components.

Navigate to: `/voice-demo`

---

## Integration Example

```tsx
import { VoiceMicIndicator } from './components/VoiceMicIndicator';
import { WakeWordAnimation } from './components/WakeWordAnimation';
import { VoiceControlPanel } from './components/VoiceControlPanel';
import { useVoiceInterface } from './hooks/useVoiceInterface';
import './styles/voice.css';

function App() {
  const { status, config, toggleVoiceMode, updateConfig } = useVoiceInterface();

  return (
    <>
      {/* Header Controls */}
      <div className="header">
        <VoiceMicIndicator status={status} onToggle={toggleVoiceMode} />
        <VoiceControlPanel config={config} onConfigChange={updateConfig} />
      </div>

      {/* Wake Word Overlay */}
      <WakeWordAnimation 
        isDetected={status.wakeWordDetected} 
        wakeWord={config.wakeWord}
      />
    </>
  );
}
```

---

## WebSocket Integration (TODO)

Add real-time backend communication:

```typescript
// In useVoiceInterface hook
useEffect(() => {
  const ws = new WebSocket('ws://localhost:8000/ws/voice');
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'voice_status') {
      setStatus(data.status);
    }
  };

  return () => ws.close();
}, []);
```
