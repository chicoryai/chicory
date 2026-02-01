import { LoaderFunctionArgs } from "@remix-run/node";
import { getUserOrgDetails } from "~/auth/auth.server";

const BASE_URL = process.env.CHICORY_API_URL || "http://localhost:8000";

/**
 * Resource route that streams chat message responses from the Chicory API
 */
export async function loader({ request, params }: LoaderFunctionArgs) {
  const { agentId, taskId, projectId } = params;
  
  console.log(`[STREAM] Starting stream request for agent: ${agentId}, task: ${taskId}`);
  
  if (!agentId || !taskId || !projectId) {
    throw new Response("Agent ID, Project ID, and Task ID are required", { status: 400 });
  }
  
  // Get user details to access project ID
  const userDetails = await getUserOrgDetails(request);
  if (userDetails instanceof Response) {
    return userDetails;
  }
  
  const orgId = 'orgId' in userDetails ? (userDetails as any).orgId : undefined;
  if (!orgId) {
    return new Response("Organization access required", { status: 403 });
  }

  console.log(`[STREAM] Connecting to Chicory API for project: ${projectId}`);
  const apiUrl = `${BASE_URL}/projects/${encodeURIComponent(projectId)}/agents/${encodeURIComponent(agentId)}/tasks/${encodeURIComponent(taskId)}/stream`;
  console.log(`[STREAM] API URL: ${apiUrl}`);

  // Create a new ReadableStream that will connect to the Chicory API
  const stream = new ReadableStream({
    async start(controller) {
      try {
        // Connect to the Chicory API streaming endpoint
        console.log(`[STREAM] Fetching from API...`);
        const response = await fetch(
          apiUrl,
          {
            method: "GET",
            headers: {
              "Accept": "text/event-stream",
            },
          }
        );

        console.log(`[STREAM] API response status: ${response.status}, ok: ${response.ok}`);
        console.log(`[STREAM] Response headers:`, Object.fromEntries([...response.headers.entries()]));

        if (!response.ok) {
          const errorText = await response.text();
          console.error(`[STREAM] API error: ${errorText}`);
          controller.error(`Failed to connect to streaming endpoint: ${errorText}`);
          return;
        }

        if (!response.body) {
          console.error(`[STREAM] No response body received`);
          controller.error("No response body");
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let chunkCount = 0;

        console.log(`[STREAM] Starting to read chunks...`);

        // Process the stream chunks
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            console.log(`[STREAM] Stream done, sending final event`);
            // Send a final "done" event
            controller.enqueue(new TextEncoder().encode("event: done\ndata: {}\n\n"));
            break;
          }
          
          chunkCount++;
          
          // Decode the binary chunk to text
          const decodedText = decoder.decode(value.slice(), { stream: true });
          
          console.log(`[STREAM] Chunk #${chunkCount}, Size: ${value.length} bytes`);
          console.log(`[STREAM] Decoded text: ${decodedText}`);
          
          // Simply pass through the SSE events - they're already in SSE format
          controller.enqueue(value);
        }
      } catch (error) {
        console.error("[STREAM] Error in streaming:", error);
        controller.error(error instanceof Error ? error.message : String(error));
      } finally {
        console.log(`[STREAM] Stream processing complete`);
        controller.close();
      }
    }
  });

  console.log(`[STREAM] Returning stream response`);
  // Return a streaming response
  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
    },
  });
}
