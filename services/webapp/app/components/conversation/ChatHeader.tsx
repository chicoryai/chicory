import { PlusIcon } from "@heroicons/react/24/outline";
import { ConversationDropdown } from "./ConversationDropdown";
import type { Conversation } from "~/services/chicory-conversation.server";

interface ChatHeaderProps {
    conversations: Conversation[];
    activeConversation: Conversation | null;
    projectId: string;
    onNewConversation: () => void;
    onArchiveConversation?: (id: string) => void;
    isSubmitting?: boolean;
}

export function ChatHeader({
    conversations,
    activeConversation,
    projectId,
    onNewConversation,
    onArchiveConversation,
    isSubmitting = false
}: ChatHeaderProps) {
    return (
        <div className="flex items-center justify-between px-4 py-3 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md transition-colors">
            {/* Left: Conversation Selector */}
            <div className="flex items-center gap-3 min-w-0 flex-1">
                <ConversationDropdown
                    conversations={conversations}
                    activeConversation={activeConversation}
                    projectId={projectId}
                    onArchive={onArchiveConversation}
                />
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-2">
                <button
                    onClick={onNewConversation}
                    disabled={isSubmitting}
                    className="flex items-center gap-2 px-3 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-600/50 text-white rounded-lg transition-all text-sm font-medium shadow-sm active:scale-95"
                    title="New Conversation"
                >
                    <PlusIcon className="h-4 w-4" />
                    <span className="hidden sm:inline">New Chat</span>
                </button>
            </div>
        </div>
    );
}
