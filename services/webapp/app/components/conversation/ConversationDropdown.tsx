/**
 * ConversationDropdown Component
 * Dropdown selector for conversations with the active conversation always shown
 */

import { useState, useRef, useEffect } from "react";
import { Link } from "@remix-run/react";
import {
  ChevronDownIcon,
  ChatBubbleLeftRightIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import type { Conversation } from "~/services/chicory-conversation.server";

interface ConversationDropdownProps {
  conversations: Conversation[];
  activeConversation: Conversation | null;
  projectId: string;
  onArchive?: (conversationId: string) => void;
}

export function ConversationDropdown({
  conversations,
  activeConversation,
  projectId,
  onArchive,
}: ConversationDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  const displayName = activeConversation
    ? activeConversation.name || `Conversation ${activeConversation.id.slice(0, 8)}`
    : "Select conversation";

  return (
    <div ref={dropdownRef} className="relative">
      {/* Dropdown trigger */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors min-w-[200px] max-w-[300px]"
      >
        <ChatBubbleLeftRightIcon className="h-4 w-4 text-gray-500 flex-shrink-0" />
        <span className="text-sm font-medium text-gray-900 dark:text-white truncate flex-1 text-left">
          {displayName}
        </span>
        <ChevronDownIcon
          className={`h-4 w-4 text-gray-500 flex-shrink-0 transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div className="absolute left-0 top-full mt-1 w-72 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-50 max-h-80 overflow-y-auto">
          {conversations.length === 0 ? (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400">
              <ChatBubbleLeftRightIcon className="h-6 w-6 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No conversations yet</p>
            </div>
          ) : (
            conversations.map((conversation) => {
              const isActive = conversation.id === activeConversation?.id;
              const name =
                conversation.name ||
                `Conversation ${conversation.id.slice(0, 8)}`;
              const dateStr = new Date(conversation.updated_at).toLocaleDateString(
                undefined,
                { month: "short", day: "numeric" }
              );

              return (
                <div
                  key={conversation.id}
                  className={`group flex items-center gap-2 px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${
                    isActive ? "bg-purple-50 dark:bg-purple-900/20" : ""
                  }`}
                >
                  <Link
                    to={`?conversationId=${conversation.id}`}
                    onClick={() => setIsOpen(false)}
                    className="flex-1 min-w-0"
                  >
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-sm font-medium truncate ${
                          isActive
                            ? "text-purple-700 dark:text-purple-300"
                            : "text-gray-900 dark:text-white"
                        }`}
                      >
                        {name}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400 ml-2 flex-shrink-0">
                        {dateStr}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {conversation.message_count} messages
                    </div>
                  </Link>
                  {onArchive && (
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setIsOpen(false);
                        onArchive(conversation.id);
                      }}
                      className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-red-100 dark:hover:bg-red-900/30 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-all"
                      title="Delete conversation"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
