import { LoaderFunctionArgs } from "@remix-run/node";

const BASE_URL = process.env.CHICORY_API_URL || "http://localhost:8000";

/**
 * SSE endpoint that polls for MCP gateway tool details every 5 seconds
 * Closes the connection when tool has description available
 */
export async function loader({ params }: LoaderFunctionArgs) {
  const { projectId, gatewayId, toolId } = params;
  
  console.log(`[TOOL-STREAM] Starting stream for tool: ${toolId}`);
  
  if (!projectId || !gatewayId || !toolId) {
    throw new Response("Project ID, Gateway ID, and Tool ID are required", { status: 400 });
  }

  const apiUrl = `${BASE_URL}/projects/${encodeURIComponent(projectId)}/mcp-gateway/${encodeURIComponent(gatewayId)}/tools/${encodeURIComponent(toolId)}`;
  console.log(`[TOOL-STREAM] API URL: ${apiUrl}`);

  // Create a new ReadableStream that will poll the API
  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();
      let intervalId: NodeJS.Timeout;
      let retryCount = 0;
      const maxRetries = 60; // 5 minutes total (60 * 5 seconds)

      const checkToolDetails = async () => {
        try {
          retryCount++;
          console.log(`[TOOL-STREAM] Polling attempt ${retryCount} for tool ${toolId}`);
          
          const response = await fetch(apiUrl, {
            method: "GET",
            headers: {
              "Accept": "application/json",
            },
          });

          if (!response.ok) {
            console.error(`[TOOL-STREAM] API error: ${response.status}`);
            // Send error event but continue polling
            const errorEvent = `event: error\ndata: ${JSON.stringify({ 
              error: `Failed to fetch tool details: ${response.status}` 
            })}\n\n`;
            controller.enqueue(encoder.encode(errorEvent));
            
            if (retryCount >= maxRetries) {
              const timeoutEvent = `event: timeout\ndata: ${JSON.stringify({ 
                message: "Deployment timed out after 5 minutes" 
              })}\n\n`;
              controller.enqueue(encoder.encode(timeoutEvent));
              clearInterval(intervalId);
              controller.close();
            }
            return;
          }

          const toolData = await response.json();
          console.log(`[TOOL-STREAM] Tool data received:`, toolData);

          // Send tool data event
          const dataEvent = `event: tool-update\ndata: ${JSON.stringify(toolData)}\n\n`;
          controller.enqueue(encoder.encode(dataEvent));

          // Check if tool has description (not "No description available")
          if (toolData.description && 
              toolData.description !== "No description available" &&
              toolData.description.trim() !== "") {
            console.log(`[TOOL-STREAM] Tool ${toolId} has description, closing stream`);
            
            // Send completion event
            const completeEvent = `event: complete\ndata: ${JSON.stringify({ 
              message: "Tool deployment complete",
              tool: toolData 
            })}\n\n`;
            controller.enqueue(encoder.encode(completeEvent));
            
            // Stop polling and close stream
            clearInterval(intervalId);
            controller.close();
          } else if (retryCount >= maxRetries) {
            console.log(`[TOOL-STREAM] Max retries reached for tool ${toolId}`);
            const timeoutEvent = `event: timeout\ndata: ${JSON.stringify({ 
              message: "Deployment timed out after 5 minutes" 
            })}\n\n`;
            controller.enqueue(encoder.encode(timeoutEvent));
            clearInterval(intervalId);
            controller.close();
          }
        } catch (error) {
          console.error("[TOOL-STREAM] Error polling tool details:", error);
          const errorEvent = `event: error\ndata: ${JSON.stringify({ 
            error: error instanceof Error ? error.message : String(error) 
          })}\n\n`;
          controller.enqueue(encoder.encode(errorEvent));
          
          if (retryCount >= maxRetries) {
            clearInterval(intervalId);
            controller.close();
          }
        }
      };

      // Send initial heartbeat
      const heartbeatEvent = `event: heartbeat\ndata: ${JSON.stringify({ 
        message: "Connection established, starting deployment monitoring" 
      })}\n\n`;
      controller.enqueue(encoder.encode(heartbeatEvent));

      // Start polling immediately
      checkToolDetails();
      
      // Then poll every 5 seconds
      intervalId = setInterval(checkToolDetails, 5000);

      // Note: request.signal may not be available in all environments
      // So we'll just rely on the interval cleanup
    }
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no", // Disable Nginx buffering
    },
  });
}