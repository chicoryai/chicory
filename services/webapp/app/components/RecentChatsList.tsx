interface ChatThread {
  id: string;
  title?: string;
  lastMessageTime: string;
}

interface RecentChatsListProps {
  chatThreads: ChatThread[];
}

export function RecentChatsList({ chatThreads }: RecentChatsListProps) {
  // Format relative time (e.g., "1 minute ago", "1 hour ago", "11 days ago")
  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) {
      return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
    } else if (diffHours > 0) {
      return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
    } else if (diffMins > 0) {
      return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`;
    } else {
      return 'Just now';
    }
  };

  if (chatThreads.length === 0) {
    return (
      <div className="flex items-center justify-center py-10">
        <div className="text-center">
          <p className="text-sm text-gray-400 mb-1">
            No chat threads yet
          </p>
          <p className="text-sm text-gray-400">
            Start a conversation to see it here
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {chatThreads.map((thread) => (
        <div key={thread.id} className="bg-gray-800 rounded-lg p-4">
          <h3 className="text-white font-medium mb-1">{thread.title || "Untitled"}</h3>
          <p className="text-gray-400 text-sm">Last message {formatRelativeTime(thread.lastMessageTime)}</p>
        </div>
      ))}
    </div>
  );
}
