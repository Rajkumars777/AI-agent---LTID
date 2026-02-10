const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Store active abort controllers for cancellation
let currentAbortController: AbortController | null = null;
let currentTaskId: string | null = null;

export function generateTaskId(): string {
    return `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export function getCurrentTaskId(): string | null {
    return currentTaskId;
}

export async function fetchHealth() {
    const res = await fetch(`${API_BASE_URL}/`);
    return res.json();
}

export async function chatWithAgent(message: string, taskId?: string) {
    // Cancel any previous request
    if (currentAbortController) {
        currentAbortController.abort();
    }

    currentAbortController = new AbortController();
    currentTaskId = taskId || generateTaskId();

    try {
        const res = await fetch(`${API_BASE_URL}/agent/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ input: message, task_id: currentTaskId }),
            signal: currentAbortController.signal
        });
        if (!res.ok) throw new Error("Agent failed to respond");
        return res.json();
    } catch (error: unknown) {
        if (error instanceof Error && error.name === 'AbortError') {
            return { cancelled: true, task_id: currentTaskId, steps: [] };
        }
        throw error;
    } finally {
        currentAbortController = null;
    }
}

export async function cancelOperation(): Promise<boolean> {
    // First, abort the fetch request
    if (currentAbortController) {
        currentAbortController.abort();
        currentAbortController = null;
    }

    // Then notify the backend
    if (currentTaskId) {
        try {
            const res = await fetch(`${API_BASE_URL}/agent/cancel`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ task_id: currentTaskId })
            });
            currentTaskId = null;
            return res.ok;
        } catch {
            return false;
        }
    }
    return true;
}

export async function listFiles(directory: string = ".") {
    const res = await fetch(`${API_BASE_URL}/tools/files?directory=${directory}`);
    return res.json();
}

export async function browseUrl(url: string) {
    const res = await fetch(`${API_BASE_URL}/tools/browser/browse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
    });
    return res.json();
}
