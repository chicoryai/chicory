import { useState, useCallback, useRef, useEffect } from "react";
import type { Message, ContentBlock } from "~/services/chicory-conversation.server";
import { useConversationStream, type StreamCompleteResult, type StreamingContentBlock } from "./useConversationStream";
import { useFetcher } from "@remix-run/react";
import type { FetcherWithComponents } from "@remix-run/react";

/* -------------------------------------------------------------------------------------------------
 * Types
 * -----------------------------------------------------------------------------------------------*/

export type ChatStatus = 'idle' | 'sending' | 'streaming' | 'error';

export interface ChatEngineState {
    messages: Message[];
    status: ChatStatus;
    error: string | null;
    typing: boolean;
}

export interface ChatEngineActions {
    sendMessage: (content: string) => Promise<void>;
    stopGeneration: () => void;
    setMessages: (messages: Message[]) => void;
}

export interface UseChatEngineOptions {
    projectId: string;
    conversationId: string | null;
    initialMessages?: Message[];
}

/* -------------------------------------------------------------------------------------------------
 * Helper: Content Block Conversion
 * -----------------------------------------------------------------------------------------------*/

function toPersistedContentBlocks(blocks: StreamingContentBlock[]): ContentBlock[] {
    return blocks.map((block): ContentBlock => {
        if (block.type === 'thinking') {
            return {
                type: 'thinking',
                thinking: block.thinking,
                signature: block.signature || '',
            };
        }
        if (block.type === 'text') {
            return {
                type: 'text',
                text: block.text,
            };
        }
        return {
            type: 'tool_use',
            id: block.id,
            name: block.name,
            input: block.input,
            output: block.output,
            is_error: block.is_error,
        };
    });
}

/* -------------------------------------------------------------------------------------------------
 * Hook: useChatEngine
 * -----------------------------------------------------------------------------------------------*/

export function useChatEngine({
    projectId,
    conversationId,
    initialMessages = []
}: UseChatEngineOptions) {
    // -- State --
    const [messages, setMessages] = useState<Message[]>(initialMessages);
    const [error, setError] = useState<string | null>(null);

    // Track active assistant message ID for streaming updates
    const currentAssistantMessageIdRef = useRef<string | null>(null);
    const fetcher = useFetcher() as FetcherWithComponents<any>;

    // Track processed fetcher data to avoid infinite loops
    const lastProcessedFetcherData = useRef<unknown>(null);

    // -- Sync with props --
    useEffect(() => {
        setMessages(initialMessages);
    }, [initialMessages]);

    // -- Streaming Hook --
    const {
        isStreaming,
        contentBlocks,
        startStreaming,
        resetStream,
        stopStreaming: stopStreamInternal
    } = useConversationStream({
        projectId,
        conversationId: conversationId || "",
        onComplete: (result: StreamCompleteResult) => {
            const assistantMessageId = currentAssistantMessageIdRef.current;
            if (assistantMessageId && result.finalContentBlocks.length > 0) {
                setMessages((prev) => {
                    const idx = prev.findIndex(
                        (msg) => msg.id === assistantMessageId || msg.id === `temp-assistant-${assistantMessageId}`
                    );
                    if (idx >= 0) {
                        const updated = [...prev];
                        updated[idx] = {
                            ...updated[idx],
                            status: result.isError ? "failed" : "completed",
                            content_blocks: toPersistedContentBlocks(result.finalContentBlocks),
                            completed_at: new Date().toISOString(),
                        };
                        return updated;
                    }
                    return prev;
                });
            }
            currentAssistantMessageIdRef.current = null;
            resetStream();
        },
        onError: (err) => {
            console.error("Stream error in engine:", err);
            setError(err);
            const assistantMessageId = currentAssistantMessageIdRef.current;
            if (assistantMessageId) {
                setMessages((prev) =>
                    prev.map((msg) =>
                        msg.id === assistantMessageId || msg.id === `temp-assistant-${assistantMessageId}`
                            ? { ...msg, status: "failed" as const }
                            : msg
                    )
                );
            }
            currentAssistantMessageIdRef.current = null;
        },
    });

    // -- Action: Send Message --
    const sendMessage = useCallback(async (content: string) => {
        if (!conversationId) return;

        setError(null);
        const now = new Date().toISOString();
        const tempTimestamp = Date.now();
        const tempUserMessageId = `temp-user-${tempTimestamp}`;
        const tempAssistantMessageId = `temp-assistant-${tempTimestamp}`;

        // 1. Optimistic Update
        const tempUserMessage: Message = {
            id: tempUserMessageId,
            conversation_id: conversationId,
            project_id: projectId,
            role: "user",
            content_blocks: [{ type: "text", text: content }],
            status: "completed",
            parent_message_id: null,
            turn_number: messages.length + 1,
            metadata: null,
            created_at: now,
            updated_at: now,
            completed_at: now,
        };

        const tempAssistantMessage: Message = {
            id: tempAssistantMessageId,
            conversation_id: conversationId,
            project_id: projectId,
            role: "assistant",
            content_blocks: [],
            status: "processing", // shows '...' typing state
            parent_message_id: tempUserMessageId,
            turn_number: messages.length + 2,
            metadata: null,
            created_at: now,
            updated_at: now,
            completed_at: null,
        };

        setMessages((prev) => [...prev, tempUserMessage, tempAssistantMessage]);
        resetStream();

        // 2. Submit to Backend
        fetcher.submit(
            {
                intent: "sendMessage",
                conversationId,
                content,
            },
            { method: "post", action: `/projects/${projectId}/chicory-agent?index` } // Standardize action target
        );

    }, [conversationId, projectId, messages.length, fetcher, resetStream]);

    // -- Effect: Handle Fetcher Response (Real IDs + Start Stream) --
    useEffect(() => {
        if (!fetcher.data || fetcher.state !== "idle" || fetcher.data === lastProcessedFetcherData.current) {
            return;
        }

        lastProcessedFetcherData.current = fetcher.data;
        const data = fetcher.data;

        if (data.success && data.intent === "sendMessage" && data.assistantMessageId) {
            // Updated IDs
            currentAssistantMessageIdRef.current = data.assistantMessageId;

            setMessages((prev) =>
                prev.map((msg) => {
                    // Update user message ID if returned (optional, but good practice if backend returns it)
                    if (msg.role === "user" && msg.id.startsWith("temp-user-")) {
                        return data.userMessageId ? { ...msg, id: data.userMessageId } : msg;
                    }
                    // Update assistant message ID
                    if (msg.role === "assistant" && msg.id.startsWith("temp-assistant-")) {
                        return { ...msg, id: data.assistantMessageId };
                    }
                    return msg;
                })
            );

            // Start Streaming
            startStreaming(data.assistantMessageId);
        } else if (data.error) {
            setError(data.error);
            // Revert optimistic updates or mark as error?
            // For now, let's mark the optimistic assistant message as failed
            setMessages((prev) =>
                prev.map((msg) =>
                    msg.id.startsWith("temp-assistant-")
                        ? { ...msg, status: "failed" }
                        : msg
                )
            );
        }
    }, [fetcher.data, fetcher.state, startStreaming]);

    // -- Action: Stop --
    const stopGeneration = useCallback(() => {
        stopStreamInternal();
        // Send cancel request to backend?
        // (Optional: fetcher.submit({ intent: 'cancel' ... }))
    }, [stopStreamInternal]);

    // -- Derived Status --
    const isSending = fetcher.state === 'submitting';
    const status: ChatStatus = error
        ? 'error'
        : isStreaming
            ? 'streaming'
            : isSending
                ? 'sending'
                : 'idle';

    return {
        state: {
            messages,
            status,
            error,
            typing: status === 'sending' || (status === 'streaming' && contentBlocks.length === 0),
            streamingContent: contentBlocks, // Expose raw blocks for the View to render
        },
        actions: {
            sendMessage,
            stopGeneration,
            setMessages
        }
    };
}
