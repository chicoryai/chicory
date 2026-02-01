import { Link } from "@remix-run/react";
import { useState, useRef, useEffect } from "react";
import {
  TrashIcon,
  ChatBubbleLeftRightIcon,
  EllipsisVerticalIcon,
  PencilIcon,
  ExclamationTriangleIcon
} from "@heroicons/react/24/outline";
import type { Conversation } from "~/services/chicory-conversation.server";

interface ConversationListProps {
  conversations: Conversation[];
  activeConversationId?: string | null;
  projectId: string;
  onArchive?: (conversationId: string) => void;
  onRename?: (conversationId: string, newName: string) => void;
}

function DeleteConfirmModal({
  isOpen,
  conversationName,
  onConfirm,
  onCancel
}: {
  isOpen: boolean;
  conversationName: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const cancelButtonRef = useRef<HTMLButtonElement>(null);

  // Focus cancel button when modal opens
  useEffect(() => {
    if (isOpen) {
      cancelButtonRef.current?.focus();
    }
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onCancel();
      }
    }

    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
      return () => document.removeEventListener("keydown", handleKeyDown);
    }
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onCancel}
      />

      {/* Modal */}
      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-600 dark:text-red-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Delete conversation
            </h3>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              Are you sure you want to delete "<span className="font-medium">{conversationName}</span>"?
              This action cannot be undone.
            </p>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            ref={cancelButtonRef}
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

function ConversationMenu({
  conversationId,
  onDelete,
  onRename
}: {
  conversationId: string;
  onDelete?: () => void;
  onRename?: () => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  return (
    <div ref={menuRef} className="relative">
      <button
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
        title="More options"
      >
        <EllipsisVerticalIcon className="h-4 w-4" />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-1 w-36 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-50">
          {onRename && (
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setIsOpen(false);
                onRename();
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <PencilIcon className="h-4 w-4" />
              Rename
            </button>
          )}
          {onDelete && (
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setIsOpen(false);
                onDelete();
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
            >
              <TrashIcon className="h-4 w-4" />
              Delete
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export function ConversationList({
  conversations,
  activeConversationId,
  projectId,
  onArchive,
  onRename
}: ConversationListProps) {
  const [deleteModal, setDeleteModal] = useState<{
    isOpen: boolean;
    conversationId: string;
    conversationName: string;
  }>({ isOpen: false, conversationId: "", conversationName: "" });

  if (conversations.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-gray-400">
        <ChatBubbleLeftRightIcon className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No conversations yet</p>
        <p className="text-xs mt-1">Start a new conversation to begin</p>
      </div>
    );
  }

  const handleRename = (conversationId: string) => {
    const newName = prompt("Enter a new name for this conversation:");
    if (newName && newName.trim()) {
      onRename?.(conversationId, newName.trim());
    }
  };

  const openDeleteModal = (conversationId: string, conversationName: string) => {
    setDeleteModal({ isOpen: true, conversationId, conversationName });
  };

  const closeDeleteModal = () => {
    setDeleteModal({ isOpen: false, conversationId: "", conversationName: "" });
  };

  const confirmDelete = () => {
    if (deleteModal.conversationId && onArchive) {
      onArchive(deleteModal.conversationId);
    }
    closeDeleteModal();
  };

  return (
    <>
      <div className="flex flex-col gap-1">
        {conversations.map((conversation) => {
          const isActive = conversation.id === activeConversationId;
          const displayName = conversation.name || `Conversation ${conversation.id.slice(0, 8)}`;
          const dateStr = new Date(conversation.updated_at).toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric'
          });

          return (
            <div
              key={conversation.id}
              className={`group flex items-center gap-2 px-3 py-2 rounded-lg transition-colors cursor-pointer ${
                isActive
                  ? "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-200"
                  : "hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
              }`}
            >
              <Link
                to={`?conversationId=${conversation.id}`}
                className="flex-1 min-w-0"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium truncate">{displayName}</span>
                  <span className="text-xs text-gray-500 dark:text-gray-400 ml-2 flex-shrink-0">
                    {dateStr}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {conversation.message_count} messages
                  </span>
                </div>
              </Link>
              <ConversationMenu
                conversationId={conversation.id}
                onDelete={onArchive ? () => openDeleteModal(conversation.id, displayName) : undefined}
                onRename={onRename ? () => handleRename(conversation.id) : undefined}
              />
            </div>
          );
        })}
      </div>

      <DeleteConfirmModal
        isOpen={deleteModal.isOpen}
        conversationName={deleteModal.conversationName}
        onConfirm={confirmDelete}
        onCancel={closeDeleteModal}
      />
    </>
  );
}
