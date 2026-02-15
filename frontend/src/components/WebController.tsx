"use client";

import { useState } from 'react';
import { orchestrateWebTask } from '@/lib/api';

export default function WebController() {
    const [url, setUrl] = useState("https://datatables.net/examples/basic_init/zero_configuration.html");
    const [status, setStatus] = useState("");
    const [resultData, setResultData] = useState<any>(null);
    const [screenshotPath, setScreenshotPath] = useState<string | null>(null);

    const handleScrape = async () => {
        const cleanUrl = sanitizeUrl(url);
        if (cleanUrl !== url) setUrl(cleanUrl);

        setStatus(`🚀 Launching Browser for ${cleanUrl}...`);
        setResultData(null);
        setScreenshotPath(null);

        try {
            const result = await orchestrateWebTask(cleanUrl, "scrape_table");
            setStatus(`Status: ${result.status}`);
            if (result.data) {
                setResultData(result.data);
                console.log("Scraped Data:", result.data);
            }
            if (result.file && (result.file.endsWith('.png') || result.file.endsWith('.jpg'))) {
                setScreenshotPath(result.file);
            }
        } catch (e) {
            setStatus(`Error: ${e}`);
        }
    };

    const handleDownload = async () => {
        const cleanUrl = sanitizeUrl(url);
        if (cleanUrl !== url) setUrl(cleanUrl);

        setStatus(`⬇️ Launching Browser for Download...`);
        setScreenshotPath(null);

        try {
            const result = await orchestrateWebTask(cleanUrl, "download_file");
            setStatus(`Status: ${result.status}`);
            if (result.file) {
                if (result.file.endsWith(".png")) {
                    setScreenshotPath(result.file); // It's an error screenshot
                    setStatus("Download failed (see screenshot)");
                } else {
                    alert(`File downloaded to: ${result.file}`);
                }
            }
        } catch (e) {
            setStatus(`Error: ${e}`);
        }
    };

    const sanitizeUrl = (input: string) => {
        let sanitized = input.trim();
        // Fix common typos
        if (sanitized.startsWith("ttps://")) sanitized = "h" + sanitized;
        if (sanitized.startsWith("tp://")) sanitized = "ht" + sanitized;
        // Add schema if missing
        if (!/^https?:\/\//i.test(sanitized)) {
            sanitized = "https://" + sanitized;
        }
        return sanitized;
    };

    const handleRead = async () => {
        const cleanUrl = sanitizeUrl(url);
        if (cleanUrl !== url) setUrl(cleanUrl); // Update UI

        setStatus(`📖 Reading ${cleanUrl}...`);
        setResultData(null);
        setScreenshotPath(null);

        try {
            const result = await orchestrateWebTask(cleanUrl, "read_page");
            setStatus(`Status: ${result.status}`);
            if (result.data) {
                setResultData(result.data);
            }
            if (result.file && (result.file.endsWith('.png') || result.file.endsWith('.jpg'))) {
                setScreenshotPath(result.file);
            }
        } catch (e) {
            setStatus(`Error: ${e}`);
        }
    };

    return (
        <div className="p-6 bg-gray-900 rounded-xl border border-gray-800 shadow-xl my-4">
            <h2 className="text-xl font-bold mb-4 text-white flex items-center gap-2">
                <span className="text-2xl">🕸️</span> Web Orchestrator
            </h2>

            <div className="mb-4">
                <label className="block text-gray-400 text-sm mb-1">Target URL</label>
                <input
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    className="w-full p-3 bg-gray-800 text-white rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none transition-colors"
                    placeholder="https://example.com"
                />
            </div>

            <div className="flex gap-3 mb-6">
                <button
                    onClick={handleScrape}
                    className="flex-1 bg-blue-600 hover:bg-blue-500 text-white px-4 py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 title='Extracts tables'"
                >
                    <span>📊</span> Scrape Table
                </button>
                <button
                    onClick={handleRead}
                    className="flex-1 bg-purple-600 hover:bg-purple-500 text-white px-4 py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 title='Reads article text'"
                >
                    <span>📖</span> Read Page
                </button>
                <button
                    onClick={handleDownload}
                    className="flex-1 bg-green-600 hover:bg-green-500 text-white px-4 py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 title='Clicks download buttons'"
                >
                    <span>⬇️</span> Download File
                </button>
            </div>

            <div className="mb-6">
                <button
                    onClick={() => {
                        setUrl("https://indexes.nikkei.co.jp/en/nkave/");
                        setStatus("🇯🇵 Starting Nikkei Workflow...");
                        setScreenshotPath(null);
                        orchestrateWebTask("https://indexes.nikkei.co.jp/en/nkave/", "get_nikkei_closing")
                            .then(result => {
                                setStatus(`Status: ${result.status}`);
                                if (result.file) {
                                    if (result.file.endsWith(".png")) {
                                        setScreenshotPath(result.file);
                                    } else {
                                        alert(`Nikkei Data saved to: ${result.file}`);
                                    }
                                }
                            })
                            .catch(e => setStatus(`Error: ${e}`));
                    }}
                    className="w-full bg-red-800 hover:bg-red-700 text-white px-4 py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                >
                    <span>🇯🇵</span> Run Nikkei Strategy (Auto-Save Excel)
                </button>
            </div>

            <div className="bg-black/50 p-4 rounded-lg min-h-[60px]">
                <p className={`text-sm ${status.startsWith("Error") ? "text-red-400" : "text-gray-300"}`}>
                    {status || "Ready to run tasks..."}
                </p>

                {screenshotPath && (
                    <div className="mt-4 border border-gray-700 rounded overflow-hidden">
                        <p className="text-xs text-gray-400 p-2 bg-gray-800">Screenshot: {screenshotPath}</p>
                        {/* 
                           Note: Directly showing local files in browser is blocked by security policies.
                           In a real app, backend would serve this via a static file endpoint.
                           For now, we just show the path.
                        */}
                        <p className="text-xs text-yellow-500 p-2">
                            (Screenshot saved to backend folder. Viewing local files directly in browser is restricted.)
                        </p>
                    </div>
                )}

                {resultData && (
                    <div className="mt-3">
                        <p className="text-xs text-gray-500 mb-1">Preview:</p>
                        <pre className="text-xs text-green-400 overflow-x-auto p-2 bg-black rounded">
                            {Array.isArray(resultData)
                                ? (
                                    <>
                                        {JSON.stringify(resultData.slice(0, 3), null, 2)}
                                        {resultData.length > 3 && `\n...and ${resultData.length - 3} more items`}
                                    </>
                                )
                                : JSON.stringify(resultData, null, 2)
                            }
                        </pre>
                    </div>
                )}
            </div>
        </div >
    );
}
