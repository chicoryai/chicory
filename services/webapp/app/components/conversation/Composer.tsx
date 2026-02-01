import { useRef, useEffect, useState, type FormEvent, type KeyboardEvent } from "react";
import { PaperAirplaneIcon, StopIcon } from "@heroicons/react/24/outline";

interface ComposerProps {
    onSend: (content: string) => void;
    onStop?: () => void;
    isStreaming?: boolean;
    isSending?: boolean;
    disabled?: boolean;
    placeholder?: string;
}

export function Composer({
    onSend,
    onStop,
    isStreaming = false,
    isSending = false,
    disabled = false,
    placeholder = "Type a message..."
}: ComposerProps) {
    const [value, setValue] = useState("");
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // DEBUG: Always show beam for testing
    const DEBUG_BEAM = false;

    // Auto-resize
    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = "auto";
            textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
        }
    }, [value]);

    const handleSubmit = (e?: FormEvent) => {
        e?.preventDefault();
        if (!value.trim() || isStreaming || isSending || disabled) return;

        onSend(value.trim());
        setValue("");

        // Reset height
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
        }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const isBusy = isStreaming || isSending;

    return (
        <div className="w-full max-w-3xl mx-auto px-4 py-4 sm:px-6">
            <form onSubmit={handleSubmit} className="relative">
                <div className={`relative rounded-2xl transition-all shadow-sm ${(isStreaming || DEBUG_BEAM)
                    ? "border-beam bg-white dark:bg-gray-800"
                    : "bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 focus-within:ring-2 focus-within:ring-purple-500/20 focus-within:border-purple-500"
                    }`}>
                    <div className="relative flex flex-col">
                        <textarea
                            ref={textareaRef}
                            value={value}
                            onChange={(e) => setValue(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={isBusy ? "Agent is thinking..." : placeholder}
                            disabled={disabled || isBusy}
                            rows={1}
                            className="w-full resize-none bg-transparent px-4 py-3 text-base sm:text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500 focus:outline-none disabled:opacity-50 min-h-[96px] max-h-[200px]"
                        />

                        <div className="flex items-center justify-between px-2 pb-2">
                            {/* Left: Attachments / Tools (Placeholder for future) */}
                            <div className="flex items-center gap-1 text-gray-400">
                                {/* Future: <PaperClipIcon ... /> */}
                            </div>

                            {/* Right: Send / Stop Action */}
                            <div className="flex items-center">
                                {isStreaming ? (
                                    <button
                                        type="button"
                                        onClick={onStop}
                                        className="p-2 rounded-lg bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
                                        title="Stop responding"
                                    >
                                        <StopIcon className="h-5 w-5" />
                                    </button>
                                ) : (
                                    <button
                                        type="submit"
                                        disabled={!value.trim() || isSending || disabled}
                                        className="p-2 rounded-lg bg-purple-600 text-white hover:bg-purple-700 disabled:bg-gray-200 dark:disabled:bg-gray-700 disabled:text-gray-400 dark:disabled:text-gray-500 transition-all active:scale-95"
                                        title="Send message"
                                    >
                                        <PaperAirplaneIcon className="h-5 w-5" />
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Hint Text */}
                <div className="mt-2 text-center">
                    <p className="text-xs text-gray-400 dark:text-gray-500">
                        Press <kbd className="font-sans px-1 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 border border-gray-200 dark:border-gray-700">Enter</kbd> to send, <kbd className="font-sans px-1 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 border border-gray-200 dark:border-gray-700">Shift + Enter</kbd> for new line
                    </p>
                </div>
            </form>
        </div>
    );
}
