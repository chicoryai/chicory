import { useEffect, useRef } from "react";
import { ChatBubbleBottomCenterTextIcon } from "@heroicons/react/24/outline";
import type { Message } from "~/services/chicory-conversation.server";
import type { StreamingContentBlock } from "~/hooks/useConversationStream";
import { TurnBlock, groupMessagesIntoTurns } from "./TurnBlock";

interface MessageListProps {
    messages: Message[];
    streamingContentBlocks: StreamingContentBlock[];
    isStreaming?: boolean;
    className?: string;
}

export function MessageList({
    messages,
    streamingContentBlocks,
    isStreaming = false,
    className = ""
}: MessageListProps) {
    const bottomRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const isInitialMount = useRef(true);
    const prevMessageCount = useRef(messages.length);

    const turns = groupMessagesIntoTurns(messages);

    const activeTurnRef = useRef<HTMLDivElement>(null);

    // Auto-scroll logic - scroll on new messages or during streaming
    useEffect(() => {
        // Skip on initial mount if desired, but user wants "initial render already placed at last block"
        // so we actually WANT to run this on mount too.

        const hasNewMessages = messages.length > prevMessageCount.current;
        prevMessageCount.current = messages.length;

        // If new messages OR streaming OR initial mount (implied by effect running)
        if (activeTurnRef.current) {
            // Use 'auto' behavior for instant snap as requested ("placed", not scrolling)
            activeTurnRef.current.scrollIntoView({ behavior: "auto", block: "start" });
        }
    }, [messages.length, isStreaming]);

    // Empty State
    if (turns.length === 0 && !isStreaming) {
        return (
            <div className={`flex items-center justify-center h-full text-gray-500 dark:text-gray-400 ${className}`}>
                <div className="text-center max-w-sm px-6">
                    <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                        <ChatBubbleBottomCenterTextIcon className="h-8 w-8 text-purple-600 dark:text-purple-400" />
                    </div>
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Start a conversation</h3>
                    <p className="text-sm">
                        Say hello to Chicory Agent to get started with your tasks.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div ref={containerRef} className={`flex flex-col w-full max-w-3xl mx-auto px-4 sm:px-6 py-16 pb-4 ${className}`}>
            {turns.map((turn, index) => {
                const isLatest = index === turns.length - 1;
                return (
                    <TurnBlock
                        key={turn.id}
                        ref={isLatest ? activeTurnRef : null}
                        turn={turn}
                        streamingContentBlocks={streamingContentBlocks}
                        isStreaming={isStreaming}
                        isLatest={isLatest}
                    />
                );
            })}

            {/* Spacer for auto-scrolling buffer */}
            <div ref={bottomRef} className="h-px w-full mt-4" />
        </div>
    );
}
