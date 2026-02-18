// Backend port discovery for Tauri sidecar architecture
let resolvedApiBase: string | null = null;
let portResolve: ((url: string) => void) | null = null;
const portPromise = new Promise<string>((resolve) => { portResolve = resolve; });

// Called by TauriProvider once the backend is confirmed ready
export function setBackendPort(port: number) {
    resolvedApiBase = `http://127.0.0.1:${port}`;
    if (portResolve) portResolve(resolvedApiBase);
}

export async function getApiBase(): Promise<string> {
    if (resolvedApiBase) return resolvedApiBase;

    // Fallback for web-only development
    if (typeof window !== "undefined" && !resolvedApiBase) {
        resolvedApiBase = "http://127.0.0.1:8000";
        return resolvedApiBase;
    }

    return portPromise;
}

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
    const base = await getApiBase();
    const res = await fetch(`${base}/`);
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
        const base = await getApiBase();
        const res = await fetch(`${base}/agent/chat`, {
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
            const base = await getApiBase();
            const res = await fetch(`${base}/agent/cancel`, {
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
    const base = await getApiBase();
    const res = await fetch(`${base}/tools/files?directory=${directory}`);
    return res.json();
}

export async function browseUrl(url: string) {
    const base = await getApiBase();
    const res = await fetch(`${base}/tools/browser/browse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
    });
    return res.json();
}

export async function orchestrateWebTask(url: string, action: string, selector?: string) {
    const base = await getApiBase();
    try {
        const res = await fetch(`${base}/api/web-orchestrator`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url, action, selector }),
        });
        if (!res.ok) throw new Error(`API Error: ${res.status}`);
        return res.json();
    } catch (e: any) {
        return { status: "Failed", error: e.toString() };
    }
}
