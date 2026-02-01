import { json } from "@remix-run/node";
import { SimpleActionHandler } from "./base";
import type { 
  ActionContext, 
  TrainingActionResponse 
} from "~/types/action-handlers";
import { 
  createProjectTrainingJob,
  getProjectTrainingJobs
} from "~/services/chicory.server";
import { 
  createErrorResponse
} from "~/utils/action-utils";

// ========================================
// TRAINING JOB HANDLER
// ========================================

export class TrainingHandler extends SimpleActionHandler {
  protected async processAction(context: ActionContext): Promise<Response> {
    try {
      return await this.handleStartTraining(context);
    } catch (error) {
      this.logError("Error starting training:", error);
      return createErrorResponse(
        error instanceof Error ? error.message : "Failed to start training",
        'startTraining',
        500
      );
    }
  }

  private async handleStartTraining(context: ActionContext): Promise<Response> {
    // Get data source IDs from form data
    const dataSourceIds = context.formData.getAll("dataSourceIds[]") as string[];
    
    this.log(`Starting training with ${dataSourceIds.length} data sources`);
    
    if (dataSourceIds.length === 0) {
      return createErrorResponse(
        "No data sources selected for training",
        'startTraining',
        400
      );
    }

    // Create training job
    const trainingJob = await createProjectTrainingJob(
      context.projectId,
      "default", // Using default model name
      dataSourceIds,
      "Training job started from Integrations page"
    );

    this.log(`Training job created: ${trainingJob.id}`);

    const response: TrainingActionResponse = {
      success: true,
      message: "Training job started successfully",
      trainingJob,
      _action: 'startTraining'
    };

    return json(response);
  }
} 