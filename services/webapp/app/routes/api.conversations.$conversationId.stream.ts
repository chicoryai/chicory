/**
 * SSE Stream Proxy Endpoint
 * Proxies SSE events from backend-api to the frontend
 */

import type { LoaderFunctionArgs } from "@remix-run/node";

const BACKEND_URL = process.env.CHICORY_API_URL || "http://localhost:8000";

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { conversationId } = params;
  const url = new URL(request.url);
  const messageId = url.searchParams.get('messageId');
  const projectId = url.searchParams.get('projectId');

  console.log(`[ConversationStream] Starting stream request for conversation: ${conversationId}, message: ${messageId}`);

  if (!conversationId || !messageId || !projectId) {
    return new Response("Missing required parameters", { status: 400 });
  }

  // Build backend SSE URL
  const backendUrl = `${BACKEND_URL}/projects/${projectId}/conversations/${conversationId}/messages/${messageId}/stream`;
  console.log(`[ConversationStream] Connecting to: ${backendUrl}`);

  // Create a new ReadableStream that will connect to the backend API
  const stream = new ReadableStream({
    async start(controller) {
      try {
        console.log(`[ConversationStream] Fetching from backend API...`);
        const response = await fetch(backendUrl, {
          method: "GET",
          headers: {
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
          },
        });

        console.log(`[ConversationStream] Backend response status: ${response.status}, ok: ${response.ok}`);

        if (!response.ok) {
          const errorText = await response.text();
          console.error(`[ConversationStream] Backend error: ${errorText}`);
          // Send error as SSE event
          const errorEvent = `event: error\ndata: ${JSON.stringify({ error: errorText })}\n\n`;
          controller.enqueue(new TextEncoder().encode(errorEvent));
          controller.close();
          return;
        }

        if (!response.body) {
          console.error(`[ConversationStream] No response body received`);
          const errorEvent = `event: error\ndata: ${JSON.stringify({ error: "No response body" })}\n\n`;
          controller.enqueue(new TextEncoder().encode(errorEvent));
          controller.close();
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let chunkCount = 0;

        console.log(`[ConversationStream] Starting to read chunks...`);

        // Process the stream chunks
        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            console.log(`[ConversationStream] Stream done after ${chunkCount} chunks`);
            break;
          }

          chunkCount++;
          const decodedText = decoder.decode(value, { stream: true });
          console.log(`[ConversationStream] Chunk #${chunkCount}, Size: ${value.length} bytes`);
          console.log(`[ConversationStream] Content: ${decodedText.substring(0, 200)}...`);

          // Pass through the SSE events as-is
          controller.enqueue(value);
        }
      } catch (error) {
        console.error("[ConversationStream] Error in streaming:", error);
        const errorEvent = `event: error\ndata: ${JSON.stringify({ error: error instanceof Error ? error.message : String(error) })}\n\n`;
        controller.enqueue(new TextEncoder().encode(errorEvent));
      } finally {
        console.log(`[ConversationStream] Stream processing complete`);
        controller.close();
      }
    }
  });

  console.log(`[ConversationStream] Returning stream response`);
  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
