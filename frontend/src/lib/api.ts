const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchHealth() {
    const res = await fetch(`${API_BASE_URL}/`);
    return res.json();
}

export async function chatWithAgent(message: string) {
    const res = await fetch(`${API_BASE_URL}/agent/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input: message }),
    });
    if (!res.ok) throw new Error("Agent failed to respond");
    return res.json();
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
