/**
 * Chicory Agent Main Page
 * Displays conversation dropdown and chat interface
 */

import { json } from "@remix-run/node";
import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import {
  useLoaderData,
  useSearchParams,
  useFetcher,
  useRevalidator,
} from "@remix-run/react";
import { useCallback, useEffect } from "react";
import { ChatHeader } from "~/components/conversation/ChatHeader";
import { MessageList } from "~/components/conversation/MessageList";
import { Composer } from "~/components/conversation/Composer";
import { FocusLayout } from "~/components/layouts/FocusLayout";
import { useChatEngine } from "~/hooks/useChatEngine";
import {
  getConversations,
  createConversation,
  getMessages,
  sendMessage,
  archiveConversation,
  type Conversation,
  type Message,
} from "~/services/chicory-conversation.server";
import { getUserOrgDetails } from "~/auth/auth.server";

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { projectId } = params;

  if (!projectId) {
    throw new Response("Project ID is required", { status: 400 });
  }

  // Get user details for validation
  const userDetails = await getUserOrgDetails(request);
  if (userDetails instanceof Response) {
    return userDetails;
  }

  // Get query params
  const url = new URL(request.url);
  const activeConversationId = url.searchParams.get("conversationId");

  try {
    // Fetch all active conversations
    const conversations = await getConversations(projectId, "active");

    // Fetch messages for active conversation
    let messages: Message[] = [];
    let activeConversation: Conversation | null = null;

    if (activeConversationId) {
      const convo = conversations.find((c) => c.id === activeConversationId);
      // Valid conversation found
      if (convo) {
        activeConversation = convo;
        messages = await getMessages(projectId, activeConversationId);
      }
    }

    return json({
      conversations,
      messages,
      activeConversation,
      projectId,
      error: null,
    });
  } catch (error) {
    console.error("Error loading Chicory Agent page:", error);
    return json({
      conversations: [],
      messages: [],
      activeConversation: null,
      projectId,
      error: "Failed to load conversations",
    });
  }
}

export async function action({ request, params }: ActionFunctionArgs) {
  const { projectId } = params;

  if (!projectId) {
    return json(
      { success: false, error: "Project ID is required" },
      { status: 400 }
    );
  }

  const userDetails = await getUserOrgDetails(request);
  if (userDetails instanceof Response) {
    return userDetails;
  }

  const formData = await request.formData();
  const intent = formData.get("intent") as string;

  try {
    if (intent === "createConversation") {
      const name = formData.get("name") as string | null;
      const conversation = await createConversation(projectId, name || undefined);
      return json({ success: true, conversation, intent: "createConversation" });
    }

    if (intent === "sendMessage") {
      const conversationId = formData.get("conversationId") as string;
      const content = formData.get("content") as string;

      if (!conversationId || !content) {
        return json(
          { success: false, error: "Conversation ID and content are required" },
          { status: 400 }
        );
      }

      const response = await sendMessage(projectId, conversationId, content);
      return json({
        success: true,
        userMessageId: response.user_message_id,
        assistantMessageId: response.assistant_message_id,
        intent: "sendMessage",
      });
    }

    if (intent === "archiveConversation") {
      const conversationId = formData.get("conversationId") as string;

      if (!conversationId) {
        return json(
          { success: false, error: "Conversation ID is required" },
          { status: 400 }
        );
      }

      await archiveConversation(projectId, conversationId);
      return json({ success: true, intent: "archiveConversation" });
    }

    return json({ success: false, error: "Unknown action" }, { status: 400 });
  } catch (error) {
    console.error("Error in Chicory Agent action:", error);
    return json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Action failed",
      },
      { status: 500 }
    );
  }
}

export default function ChicoryAgentPage() {
  const {
    conversations,
    messages: initialMessages,
    activeConversation,
    projectId,
    error,
  } = useLoaderData<typeof loader>();

  const [searchParams, setSearchParams] = useSearchParams();
  const managementFetcher = useFetcher(); // Separate fetcher for create/archive
  const revalidator = useRevalidator();

  const activeConversationId = searchParams.get("conversationId");

  // -- Chat Engine --
  const { state, actions } = useChatEngine({
    projectId,
    conversationId: activeConversationId,
    initialMessages,
  });

  // -- Event Handlers --

  const handleCreateConversation = useCallback(() => {
    managementFetcher.submit(
      { intent: "createConversation" },
      { method: "post" }
    );
  }, [managementFetcher]);

  const handleArchiveConversation = useCallback((conversationId: string) => {
    if (confirm("Are you sure you want to archive this conversation?")) {
      managementFetcher.submit(
        { intent: "archiveConversation", conversationId },
        { method: "post" }
      );
    }
  }, [managementFetcher]);

  const handleSend = useCallback((content: string) => {
    actions.sendMessage(content);
  }, [actions]);

  // -- Side Effects for Management Actions --
  useEffect(() => {
    const data = managementFetcher.data as any;
    if (!data) return;

    if (data.success && data.intent === "createConversation" && data.conversation) {
      // Switch to new conversation
      setSearchParams({ conversationId: data.conversation.id });
    } else if (data.success && data.intent === "archiveConversation") {
      // Clear selection if we just archived the active one
      if (activeConversationId) {
        setSearchParams({});
      }
      // Refresh list
      revalidator.revalidate();
    }
  }, [managementFetcher.data, setSearchParams, activeConversationId, revalidator]);

  // -- Error State --
  if (error) {
    return (
      <div className="h-full flex items-center justify-center bg-white dark:bg-gray-900">
        <div className="text-center p-8">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            Error Loading Page
          </h2>
          <p className="text-gray-500 dark:text-gray-400">{error}</p>
        </div>
      </div>
    );
  }

  // -- Render --
  return (
    <FocusLayout
      header={
        <ChatHeader
          conversations={conversations}
          activeConversation={activeConversation}
          projectId={projectId}
          onNewConversation={handleCreateConversation}
          onArchiveConversation={handleArchiveConversation}
          isSubmitting={managementFetcher.state === "submitting"}
        />
      }
      footer={
        <Composer
          onSend={handleSend}
          onStop={actions.stopGeneration}
          isStreaming={state.status === 'streaming'}
          isSending={state.status === 'sending'}
          disabled={!activeConversationId}
          placeholder={activeConversationId ? "Type a message..." : "Select a conversation to start chatting"}
        />
      }
    >
      {/* Message List - scrollable content area */}
      <div className="h-full overflow-y-auto">
        <MessageList
          messages={state.messages}
          streamingContentBlocks={state.streamingContent}
          isStreaming={state.status === 'streaming'}
          className="pb-4"
        />
      </div>
    </FocusLayout>
  );
}
