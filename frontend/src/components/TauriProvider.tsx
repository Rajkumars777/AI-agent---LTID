"use client";

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { setBackendPort } from "@/lib/api";

export default function TauriProvider({
    children,
}: {
    children: React.ReactNode;
}) {
    const [isReady, setIsReady] = useState(false);

    useEffect(() => {
        // Check if running in Tauri
        if (typeof window !== "undefined" && (window as any).__TAURI__) {
            const initTauri = async () => {
                try {
                    // Listen for backend-ready event (Port Discovery)
                    const unlisten = await listen<number>("backend-ready", (event) => {
                        console.log("Tauri: Backend ready on port", event.payload);
                        setBackendPort(event.payload);
                        setIsReady(true);
                    });

                    // Also try to invoke a command to get port if already running
                    // (Robustness for race conditions)
                    // const port = await invoke<number>("get_backend_port");
                    // if (port) setBackendPort(port);

                    return () => {
                        unlisten();
                    };
                } catch (e) {
                    console.error("Tauri init failed", e);
                }
            };

            initTauri();
        } else {
            // Dev/Web mode
            setIsReady(true);
        }
    }, []);

    if (!isReady) {
        return (
            <div className="flex h-screen items-center justify-center bg-black text-white">
                <div className="text-center">
                    <h2 className="text-xl font-bold">Initializing AI Engine...</h2>
                    <p className="text-gray-400">Please wait while the local backend starts.</p>
                </div>
            </div>
        );
    }

    return <>{children}</>;
}
