import type { LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";

/**
 * Health check endpoint for monitoring and container orchestration
 */
export async function loader({ request }: LoaderFunctionArgs) {
  // You could add more sophisticated health checks here
  // like database connectivity tests or external service checks
  return json(
    {
      status: "healthy"
    },
    { status: 200 }
  );
}
