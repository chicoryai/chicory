import type { LoaderFunctionArgs } from "@remix-run/node";

const BASE_URL = process.env.CHICORY_API_URL || 'https://api.chicory.ai';

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { evalId, agentId, projectId } = params;
  const url = new URL(request.url);
  const runId = url.searchParams.get('runId');
  
  if (!runId || !agentId || !projectId) {
    return new Response("Missing required parameters", { status: 400 });
  }
  
  console.log(`[SSE] Starting SSE for project: ${projectId}, agent: ${agentId}, evaluation: ${evalId}, run: ${runId}`);
  
  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();
      let isActive = true;
      let pollCount = 0;
      const maxPolls = 40; // Max 10 minutes (40 * 15 seconds)
      
      const pollRun = async () => {
        try {
          console.log(`[SSE] Polling run: ${runId}`);
          
          // Poll backend for run details
          const response = await fetch(
            `${BASE_URL}/projects/${projectId}/agents/${agentId}/evaluations/${evalId}/runs/${runId}`,
            {
              headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
              }
            }
          );
          
          if (!response.ok) {
            throw new Error(`Failed to fetch run: ${response.status}`);
          }
          
          const runData = await response.json();
          console.log(`[SSE] Run data: ${runData.status}`);
          // Send SSE message with full run data
          const message = `data: ${JSON.stringify({
            type: 'progress',
            data: {
              runId,
              status: runData.status,
              completed: runData.completed_test_cases || 0,
              total: runData.total_test_cases || 0,
              score: runData.overall_score,
              fullRun: runData // Include complete run object
            }
          })}\n\n`;
          
          console.log(`[SSE] Sending SSE message for run: ${runId}`);
          controller.enqueue(encoder.encode(message));
          
          // Stop polling when complete or max polls reached
          pollCount++;
          if (runData.status === 'completed' || runData.status === 'failed' || pollCount >= maxPolls) {
            isActive = false;
            
            // Send process_complete message when evaluation is completed
            if (runData.status === 'completed') {
              const completeMessage = `data: ${JSON.stringify({
                type: 'process_complete',
                data: {
                  runId,
                  status: runData.status,
                  completed: runData.completed_test_cases || 0,
                  total: runData.total_test_cases || 0,
                  score: runData.overall_score,
                  fullRun: runData
                }
              })}\n\n`;
              console.log(`[SSE] Sending process_complete message for run: ${runId}`);
              controller.enqueue(encoder.encode(completeMessage));
            }
            
            // Send final status for other cases
            if (pollCount >= maxPolls) {
              const timeoutMessage = `data: ${JSON.stringify({
                type: 'timeout',
                message: 'Polling timeout reached'
              })}\n\n`;
              console.log(`[SSE] Sending timeout message for run: ${runId}`);
              controller.enqueue(encoder.encode(timeoutMessage));
            }
            
            controller.close();
          }
        } catch (error) {
          console.error(`[SSE] Error polling run: ${runId}`, error);
          
          // Send error event
          const errorMessage = `data: ${JSON.stringify({ 
            type: 'error', 
            error: error instanceof Error ? error.message : 'Unknown error'
          })}\n\n`;
          console.log(`[SSE] Sending error message for run: ${runId}`);
          controller.enqueue(encoder.encode(errorMessage));
          
          // Continue polling on non-fatal errors
          if (pollCount < 5) {
            // Retry a few times before giving up
            pollCount++;
          } else {
            isActive = false;
            controller.close();
          }
        }
        
        // Continue polling every 15 seconds
        if (isActive) {
          setTimeout(pollRun, 15000);
        }
      };
      
      // Send initial heartbeat
      const heartbeat = `data: ${JSON.stringify({ type: 'connected' })}\n\n`;
      console.log(`[SSE] Sending heartbeat for run: ${runId}`);
      controller.enqueue(encoder.encode(heartbeat));
      
      // Start polling immediately
      pollRun();
    }
  });
  
  console.log(`[SSE] Starting SSE stream for project: ${projectId}, agent: ${agentId}, evaluation: ${evalId}, run: ${runId}`);
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no', // Disable Nginx buffering
    },
  });
}
