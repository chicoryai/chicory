import { ActionFunctionArgs } from "@remix-run/node";
import { getUserOrgDetails } from "~/auth/auth.server";

const CLAUDE_SERVICE_URL = process.env.CLAUDE_SERVICE_URL || "http://localhost:8000";

export async function action({ request }: ActionFunctionArgs) {
  // Verify authentication
  const userDetails = await getUserOrgDetails(request);
  const userId = userDetails && 'userId' in userDetails ? userDetails.userId : null;
  
  if (!userId) {
    throw new Response("Unauthorized", { status: 401 });
  }

  // Parse request body
  const body = await request.json();
  const { prompt, session_id, options } = body;

  if (!prompt) {
    throw new Response("Prompt is required", { status: 400 });
  }

  // Create a new ReadableStream that will connect to the Claude service
  const stream = new ReadableStream({
    async start(controller) {
      try {
        // Connect to the Claude service streaming endpoint
        const response = await fetch(`${CLAUDE_SERVICE_URL}/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
          },
          body: JSON.stringify({
            prompt,
            session_id,
            options,
          }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          controller.error(`Failed to connect to Claude service: ${errorText}`);
          return;
        }

        if (!response.body) {
          controller.error("No response body");
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        // Process the stream chunks
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            // Send a final "done" event
            controller.enqueue(new TextEncoder().encode("event: done\ndata: {}\n\n"));
            break;
          }
          
          // Decode the chunk and add to buffer
          buffer += decoder.decode(value, { stream: true });
          
          // Process complete SSE messages from buffer
          const lines = buffer.split("\n");
          buffer = lines.pop() || ""; // Keep incomplete line in buffer
          
          for (const line of lines) {
            if (line.trim()) {
              // Forward the SSE line as-is
              controller.enqueue(new TextEncoder().encode(line + "\n"));
            } else {
              // Empty line marks end of SSE message
              controller.enqueue(new TextEncoder().encode("\n"));
            }
          }
        }
      } catch (error) {
        console.error("[CLAUDE STREAM] Error:", error);
        const errorMessage = error instanceof Error ? error.message : "Unknown error";
        controller.enqueue(
          new TextEncoder().encode(
            `event: error\ndata: ${JSON.stringify({ error: errorMessage })}\n\n`
          )
        );
      } finally {
        controller.close();
      }
    },
  });

  // Return the stream as a Server-Sent Events response
  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
    },
  });
}