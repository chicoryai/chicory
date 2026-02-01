import React from "react";
import { AgentMessageCard } from "./AgentMessageCard";
import { ThinkingBlock } from "./ThinkingBlock";
import { ToolExecutionCard } from "./ToolExecutionCard";

/**
 * Demo component showcasing the improved UI components
 *
 * This demonstrates:
 * - Individual component usage
 * - Full AgentMessageCard with all features
 * - Staggered animations
 */
export const ImprovedComponentsDemo: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8 dark:from-slate-900 dark:to-slate-800">
      <div className="mx-auto max-w-4xl space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-4xl font-bold text-slate-900 dark:text-slate-100">
            Improved Agent UI Components
          </h1>
          <p className="mt-2 text-slate-600 dark:text-slate-400">
            Clean, organized, and animated interface components
          </p>
        </div>

        {/* Individual ThinkingBlock Demo */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold text-slate-800 dark:text-slate-200">
            Thinking Block
          </h2>
          <ThinkingBlock
            content="The user wants me to run a workflow to catalog a table into a JIRA ticket. Let me understand what's being asked: I need to execute a cataloging workflow that involves running 'snowflake_describe_table_tool' to describe the table, extract relevant information, and create a JIRA ticket with the cataloged data."
            index={0}
          />
        </section>

        {/* Individual ToolExecutionCard Demo */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold text-slate-800 dark:text-slate-200">
            Tool Execution Card
          </h2>
          <ToolExecutionCard
            toolName="Read"
            toolId="toolu_01AbCdEfGhIjKlMnOpQrStUv"
            input={{
              file_path: "/app/data/a621ea97-aed0-4f1c-8b20-5ecaeb3d022c/raw/data/database_metadata/providers/snowflake/provider_overview.json"
            }}
            output={JSON.stringify({
              response: "# CLAUDE.md Created Successfully\n\nI've created a comprehensive CLAUDE.md file that serves as a context guide for AI assistants working in this environment. Here's what it covers:\n\n## Key Sections:\n\n1. **Project Overview** - Describes the main components"
            }, null, 2)}
            isError={false}
            timestamp="12:34:56.789"
            index={0}
          />

          <ToolExecutionCard
            toolName="Glob"
            toolId="toolu_01XyZaBcDeFgHiJkLmNoPqRs"
            input={{
              pattern: "**/*.json",
              path: "/app/data/a621ea97-aed0-4f1c-8b20-5ecaeb3d022c/raw/data"
            }}
            output="/app/data/a621ea97-aed0-4f1c-8b20-5ecaeb3d022c/raw/data/database_metadata/providers/snowflake/provider_overview.json\n/app/data/a621ea97-aed0-4f1c-8b20-5ecaeb3d022c/raw/data/database_metadata/providers/snowflake/tables/SDB71929/AUSTIN/AUSTIN_BOUNDARY.json"
            isError={false}
            timestamp="12:34:57.123"
            index={1}
          />
        </section>

        {/* Full AgentMessageCard Demo */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold text-slate-800 dark:text-slate-200">
            Full Agent Message Card
          </h2>
          <AgentMessageCard
            agentName="Agent 0"
            status="completed"
            timestamp={new Date().toISOString()}
            thinking={[
              "The user wants me to run a workflow to catalog a table into a JIRA ticket. Let me understand what's being asked:\n\n1. I need to execute a cataloging workflow that involves:\n   - Running 'snowflake_describe_table_tool' to describe the table\n   - Extract relevant information\n   - Create a JIRA ticket with the cataloged data"
            ]}
            text="I'll help you catalog a table into a JIRA ticket. First, let me check the context directory for information about which table to catalog."
            tools={[
              {
                toolName: "Read",
                toolId: "toolu_01AbCdEfGhIjKlMnOpQrStUv",
                input: {
                  file_path: "/app/data/context/CLAUDE.md"
                },
                output: "# CLAUDE.md Created Successfully\n\nI've created a comprehensive CLAUDE.md file...",
                isError: false
              },
              {
                toolName: "Glob",
                toolId: "toolu_01XyZaBcDeFgHiJkLmNoPqRs",
                input: {
                  pattern: "**/*.json",
                  path: "/app/data/metadata"
                },
                output: "Found 15 matching files...",
                isError: false
              }
            ]}
            index={0}
          />
        </section>

        {/* Running state demo */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold text-slate-800 dark:text-slate-200">
            Running State
          </h2>
          <AgentMessageCard
            agentName="Agent 1"
            status="running"
            timestamp={new Date().toISOString()}
            thinking={[
              "Analyzing the table structure and preparing the catalog entry..."
            ]}
            text="Processing your request..."
            index={1}
          />
        </section>

        {/* Failed state demo */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold text-slate-800 dark:text-slate-200">
            Failed State
          </h2>
          <AgentMessageCard
            agentName="Agent 2"
            status="failed"
            timestamp={new Date().toISOString()}
            text="Unable to complete the task due to an error."
            tools={[
              {
                toolName: "ExecuteQuery",
                toolId: "toolu_01ErrorExample",
                input: {
                  query: "SELECT * FROM invalid_table"
                },
                output: "Error: Table 'invalid_table' does not exist",
                isError: true
              }
            ]}
            index={2}
          />
        </section>
      </div>
    </div>
  );
};

export default ImprovedComponentsDemo;
