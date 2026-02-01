import { json, redirect } from "@remix-run/node";
import type { ActionFunctionArgs } from "@remix-run/node";
import { getUserOrgDetails } from "~/auth/auth.server";
import { submitTaskFeedback, type TaskFeedbackResponse } from "~/services/chicory.server";

export async function action({ request }: ActionFunctionArgs) {
  if (request.method.toUpperCase() !== "POST") {
    return json({ error: "Method not allowed" }, { status: 405 });
  }

  const formData = await request.formData();
  const taskId = formData.get("taskId");
  const agentId = formData.get("agentId");
  const feedback = formData.get("feedback");
  const rating = formData.get("rating");
  const rawTags = formData.getAll("tags");
  const projectIdFromForm = formData.get("projectId");

  if (!projectIdFromForm || typeof projectIdFromForm !== "string") {
    return json({ error: "Project ID is required" }, { status: 400 });
  }

  const userDetails = await getUserOrgDetails(request);

  if (userDetails instanceof Response) {
    return userDetails;
  }

  if (!userDetails) {
    return redirect("/api/auth/login");
  }

  const projectId = projectIdFromForm;

  if (!taskId || typeof taskId !== "string") {
    return json({ error: "Task ID is required" }, { status: 400 });
  }

  if (!agentId || typeof agentId !== "string") {
    return json({ error: "Agent ID is required" }, { status: 400 });
  }

  const normalizedTags = rawTags
    .flatMap(tag => (typeof tag === "string" ? tag.split(",") : []))
    .map(tag => tag.trim())
    .filter(Boolean);

  if (rating !== "positive" && rating !== "negative") {
    return json({ error: "Select whether the response was positive or negative." }, { status: 400 });
  }

  if (!feedback && normalizedTags.length === 0) {
    return json({ error: "Provide feedback text or at least one tag" }, { status: 400 });
  }

  try {
    const response: TaskFeedbackResponse = await submitTaskFeedback(projectId, agentId, taskId, {
      rating,
      feedback: typeof feedback === "string" ? feedback : "",
      tags: normalizedTags
    });

    return json({ success: true, feedback: response });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to submit feedback";
    return json({ error: message }, { status: 500 });
  }
}
