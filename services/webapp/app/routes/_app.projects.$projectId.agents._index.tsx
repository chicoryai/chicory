import { json } from "@remix-run/node";
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { Link, useFetcher, useLoaderData, useNavigate } from "@remix-run/react";
import { PlayCircleIcon, RocketLaunchIcon, ChartBarSquareIcon, ClipboardDocumentListIcon, TrashIcon } from "@heroicons/react/24/outline";
import { GiVintageRobot } from "react-icons/gi";
import { useEffect, useState, type ReactNode } from "react";
import { getUserOrgDetails } from "~/auth/auth.server";
import { deleteAgent, getAgents, getProjectById, type Agent, type Project } from "~/services/chicory.server";

interface LoaderData {
  project: Project;
  agents: Agent[];
}

export async function loader({ request, params }: LoaderFunctionArgs) {
  const projectId = params.projectId;

  if (!projectId) {
    throw new Response("Project ID is required", { status: 400 });
  }

  const userDetails = await getUserOrgDetails(request);
  if (userDetails instanceof Response) {
    return userDetails;
  }

  const orgId = 'orgId' in userDetails ? (userDetails as any).orgId : undefined;
  const project = await getProjectById(projectId);

  if (!project || (orgId && project.organization_id !== orgId)) {
    throw new Response("Project not found", { status: 404 });
  }

  const agents = await getAgents(projectId);

  return json<LoaderData>({ project, agents });
}

export async function action({ request, params }: ActionFunctionArgs) {
  const projectId = params.projectId;

  if (!projectId) {
    throw new Response("Project ID is required", { status: 400 });
  }

  const userDetails = await getUserOrgDetails(request);
  if (userDetails instanceof Response) {
    return userDetails;
  }

  const orgId = 'orgId' in userDetails ? (userDetails as any).orgId : undefined;
  const project = await getProjectById(projectId);

  if (!project || (orgId && project.organization_id !== orgId)) {
    return json({ success: false, error: "Project not found" }, { status: 404 });
  }

  const formData = await request.formData();
  const intent = formData.get("intent");

  if (intent === "deleteAgent") {
    const agentId = (formData.get("agentId") || "").toString();

    if (!agentId) {
      return json({ success: false, error: "Agent ID is required" }, { status: 400 });
    }

    try {
      await deleteAgent(projectId, agentId);
      return json({ success: true });
    } catch (error) {
      console.error("Error deleting agent:", error);
      return json({ success: false, error: "Failed to delete agent" }, { status: 500 });
    }
  }

  return json({ success: false, error: "Unsupported action" }, { status: 400 });
}

export default function AgentsPage() {
  const { project, agents } = useLoaderData<typeof loader>();
  const hasAgents = agents.length > 0;

  return (
    <div className="min-h-full bg-transparent">
      <div className="mx-auto max-w-7xl px-6 py-10 lg:px-8">
        <header className="flex flex-col gap-6 rounded-3xl  bg-white/50 p-8 transition dark:border-white/10 dark:bg-white/10 dark:shadow-purple-900/40 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-whitePurple-100/80 text-purple-600 shadow-lg shadow-whitePurple-50/70 dark:bg-white/10 dark:text-purple-200 dark:shadow-purple-900/30">
              <GiVintageRobot className="h-6 w-6" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-purple-500 dark:text-purple-200">Agents</p>
              <h1 className="text-3xl font-semibold text-gray-900 drop-shadow-sm dark:text-white">{project.name}</h1>
              {project.description && (
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">{project.description}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to={`/projects/${project.id}/new`}
              className="inline-flex items-center rounded-2xl border border-white/40 bg-purple-600/90 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-whitePurple-50/70 dark:shadow-purple-900/40 backdrop-blur focus:outline-none focus:ring-2 focus:ring-purple-300 focus:ring-offset-0 hover:bg-purple-500"
            >
              Create Agent
            </Link>
          </div>
        </header>

        {hasAgents ? (
          <section className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">
            {agents.map((agent: Agent) => (
              <AgentCard key={agent.id} agent={agent} projectId={project.id} />
            ))}
          </section>
        ) : (
          <div className="mt-16 flex flex-col items-center rounded-2xl border border-dashed border-gray-300 bg-white py-16 text-center dark:border-gray-700 dark:bg-gray-900">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-purple-100 text-purple-600 dark:bg-purple-900/40 dark:text-purple-200">
              <GiVintageRobot className="h-7 w-7" />
            </div>
            <h2 className="mt-6 text-xl font-semibold text-gray-900 dark:text-white">No agents yet</h2>
            <p className="mt-2 max-w-md text-sm text-gray-600 dark:text-gray-400">
              Create your first agent to start building, evaluating, and deploying AI workflows for this project.
            </p>
            <Link
              to={`/projects/${project.id}/new`}
              className="mt-6 inline-flex items-center rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
            >
              Create Agent
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

type DeleteFetcherData = {
  success?: boolean;
  error?: string;
};

function AgentCard({ agent, projectId }: { agent: Agent; projectId: string }) {
  const navigate = useNavigate();
  const deleteFetcher = useFetcher<DeleteFetcherData>();
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const deleteError = deleteFetcher.data?.error;
  const isDeleting = deleteFetcher.state !== "idle";
  const createdAtLabel = new Date(agent.created_at).toLocaleDateString();

  useEffect(() => {
    if (deleteFetcher.state !== "idle") {
      return;
    }

    if (deleteFetcher.data?.success) {
      setIsConfirmingDelete(false);
    }
  }, [deleteFetcher.state, deleteFetcher.data]);
  const statusStyles = getStatusStyles(agent.status);
  const deployedBadge = agent.deployed ? "text-emerald-600 bg-emerald-100 dark:text-emerald-200 dark:bg-emerald-900/40" : "text-amber-600 bg-amber-100 dark:text-amber-200 dark:bg-amber-900/40";
  const deployedLabel = agent.deployed ? "Deployed" : "Not deployed";

  return (
    <article
      onClick={() => navigate(`/projects/${projectId}/agents/${agent.id}`)}
      className="group relative flex h-full flex-col overflow-hidden rounded-3xl border border-whitePurple-100/40 bg-white/30 p-6 shadow-xl shadow-whitePurple-50/60 dark:shadow-purple-900/40 backdrop-blur-2xl transition hover:-translate-y-1 hover:border-whitePurple-200/70 hover:shadow-whitePurple-50/80 dark:border-whitePurple-200/20 dark:bg-white/10 cursor-pointer"
      role="link"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          navigate(`/projects/${projectId}/agents/${agent.id}`);
        }
      }}
    >
      {isConfirmingDelete && (
        <div
          className="absolute inset-0 z-10 flex flex-col justify-between rounded-3xl border border-red-200 bg-red-50/95 p-6 text-left text-red-600 backdrop-blur-sm dark:border-red-800/70 dark:bg-red-950/60 dark:text-red-200"
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
          }}
        >
          <div>
            <p className="text-sm font-semibold">Delete {agent.name}?</p>
            <p className="mt-1 text-xs text-red-500/90 dark:text-red-300/90">This agent and its configuration will be permanently removed.</p>
            {deleteError && (
              <p className="mt-2 rounded-md bg-red-100 px-2 py-1 text-xs font-medium text-red-700 dark:bg-red-900/40 dark:text-red-200">
                {deleteError}
              </p>
            )}
          </div>
          <div className="mt-4 flex items-center gap-2">
            <button
              type="button"
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                const formData = new FormData();
                formData.append("intent", "deleteAgent");
                formData.append("agentId", agent.id);
                deleteFetcher.submit(formData, {
                  method: "post"
                });
              }}
              disabled={isDeleting}
              className="inline-flex items-center rounded-md bg-red-500 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-red-600 disabled:opacity-60 dark:bg-red-600 dark:hover:bg-red-500"
            >
              {isDeleting ? "Deleting…" : "Delete"}
            </button>
            <button
              type="button"
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                setIsConfirmingDelete(false);
              }}
              className="inline-flex items-center rounded-md border border-red-200 px-3 py-1.5 text-sm font-medium text-red-500 transition hover:bg-red-100 dark:border-red-800 dark:text-red-200 dark:hover:bg-red-900/30"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{agent.name}</h3>
            <span className="inline-flex items-center rounded-full bg-white/80 px-3 py-1 text-xs font-medium text-gray-600 shadow-sm shadow-whitePurple-50/60 backdrop-blur dark:bg-white/10 dark:text-gray-200 dark:shadow-purple-900/30">
              {createdAtLabel}
            </span>
          </div>
          <div className="mt-2 flex flex-wrap gap-2 text-xs font-medium">
            <span className={`inline-flex items-center rounded-full px-2.5 py-1 ${statusStyles}`}>{agent.status || "unknown"}</span>
            <span className={`inline-flex items-center rounded-full px-2.5 py-1 ${deployedBadge}`}>
              {deployedLabel}
            </span>
          </div>
        </div>
        {!isConfirmingDelete && (
          <button
            type="button"
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              setIsConfirmingDelete(true);
            }}
            className="inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-sm font-semibold text-red-600 transition hover:bg-red-500/20 dark:bg-red-900/40 dark:text-red-200 dark:hover:bg-red-900/60"
            aria-label={`Delete ${agent.name}`}
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        )}
      </div>

      {agent.description && (
        <p className="mt-4 line-clamp-3 text-sm text-gray-700 dark:text-gray-300">{agent.description}</p>
      )}

      <dl className="mt-6 grid grid-cols-2 gap-3 text-sm text-gray-700 dark:text-gray-300">
        <div className="rounded-2xl border border-whitePurple-100/40 bg-white/40 p-3 shadow-sm shadow-whitePurple-50/50 dark:shadow-purple-900/30 backdrop-blur dark:border-whitePurple-200/20 dark:bg-white/5">
          <dt className="text-xs uppercase tracking-wide text-purple-600 dark:text-purple-200">Tasks</dt>
          <dd className="mt-1 text-lg font-semibold text-gray-900 dark:text-gray-100">{agent.task_count}</dd>
        </div>
        <div className="rounded-2xl border border-whitePurple-100/40 bg-white/40 p-3 shadow-sm shadow-whitePurple-50/50 dark:shadow-purple-900/30 backdrop-blur dark:border-whitePurple-200/20 dark:bg-white/5">
          <dt className="text-xs uppercase tracking-wide text-purple-600 dark:text-purple-200">Updated</dt>
          <dd className="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">{new Date(agent.updated_at).toLocaleDateString()}</dd>
        </div>
      </dl>

      <div className="mt-6 flex flex-1 flex-col justify-end gap-3">
        <ActionLink
          to={`/projects/${projectId}/agents/${agent.id}/playground`}
          icon={<PlayCircleIcon className="h-5 w-5" />}
          label="Open Playground"
          variant="primary"
          fullWidth
        />
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <ActionLink
            to={`/projects/${projectId}/agents/${agent.id}/tasks`}
            icon={<ClipboardDocumentListIcon className="h-5 w-5" />}
            label="Tasks"
            variant="glass"
          />
          <ActionLink
            to={`/projects/${projectId}/agents/${agent.id}/evaluations`}
            icon={<ChartBarSquareIcon className="h-5 w-5" />}
            label="Evaluate"
            variant="glass"
          />
          <ActionLink
            to={`/projects/${projectId}/agents/${agent.id}/deploy`}
            icon={<RocketLaunchIcon className="h-5 w-5" />}
            label="Deploy"
            variant="glass"
          />
        </div>
      </div>
    </article>
  );
}

interface ActionLinkProps {
  to: string;
  icon: ReactNode;
  label: string;
  variant?: "primary" | "accent" | "glass" | "ghost";
  fullWidth?: boolean;
}

function ActionLink({ to, icon, label, variant = "primary", fullWidth = false }: ActionLinkProps) {
  const baseClasses = "inline-flex items-center justify-center gap-2 rounded-2xl px-3 py-2.5 text-sm font-semibold transition";
  const styles = {
    primary: "bg-gradient-to-r from-purple-500 via-purple-400 to-purple-500 text-white shadow-lg shadow-whitePurple-50/70 dark:shadow-purple-900/40 hover:from-purple-400 hover:via-purple-300 hover:to-purple-400",
    accent: "bg-whitePurple-100/80 text-purple-600 shadow-md shadow-whitePurple-50/70 dark:shadow-purple-900/30 hover:bg-whitePurple-100",
    glass: "border border-white/40 bg-white/30 text-gray-700 shadow-sm shadow-whitePurple-50/40 dark:shadow-purple-900/20 hover:border-purple-200/60 hover:text-purple-600 dark:border-white/10 dark:bg-white/5 dark:text-gray-200",
    ghost: "border border-white/40 bg-transparent text-gray-700 shadow-sm shadow-whitePurple-50/30 dark:shadow-purple-900/20 hover:text-purple-600 hover:border-purple-200/60 dark:border-white/10 dark:text-gray-200"
  } as const;

  return (
    <Link
      to={to}
      onClick={(event) => event.stopPropagation()}
      className={`${baseClasses} ${styles[variant]} ${fullWidth ? "w-full" : ""}`}
    >
      {icon}
      <span>{label}</span>
    </Link>
  );
}

function getStatusStyles(status: string | undefined) {
  switch (status) {
    case "running":
      return "bg-emerald-200/70 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200";
    case "error":
      return "bg-rose-200/70 text-rose-700 dark:bg-rose-500/20 dark:text-rose-200";
    case "stopped":
      return "bg-amber-200/70 text-amber-700 dark:bg-amber-500/20 dark:text-amber-200";
    default:
      return "bg-white/60 text-gray-700 dark:bg-white/10 dark:text-gray-200";
  }
}
