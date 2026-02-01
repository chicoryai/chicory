import { Link, useLocation, useLoaderData, useFetcher } from "@remix-run/react";
import { PlusIcon, FolderIcon, ChatBubbleLeftRightIcon, CubeIcon, SparklesIcon, CubeTransparentIcon, RocketLaunchIcon, ChevronDownIcon, ChevronRightIcon, ChevronDoubleRightIcon, CodeBracketIcon, ChatBubbleBottomCenterTextIcon } from "@heroicons/react/24/outline";
import { GiVintageRobot } from "react-icons/gi";
import { UserMenu } from "~/components/UserMenu";
import { ProjectSelector } from "~/components/ProjectSelector";
import { useProject } from "~/contexts/project-context";
import { useState, useEffect, useMemo } from "react";
import type { Agent } from "~/services/chicory.server";

interface SidebarProps {
  isOpen: boolean;
  user: any;
  toggleSidebar: () => void;
  organizationId?: string;
}

interface SidebarLinkProps {
  to: string;
  icon: React.ReactNode;
  label: string;
  isOpen: boolean;
}

interface SidebarSectionProps {
  title: string;
  icon: React.ReactNode;
  isOpen: boolean;
  to?: string;
  iconTo?: string;
  isExpanded?: boolean;
  onToggle?: () => void;
  trailing?: React.ReactNode;
  children?: React.ReactNode;
}

function SidebarLink({ to, icon, label, isOpen }: SidebarLinkProps) {
  const location = useLocation();
  const isActive = location.pathname === to;
  const baseClasses = isOpen
    ? "px-4 py-2.5 justify-start w-full"
    : "px-0 justify-center w-full";

  const iconClasses = isOpen
    ? "mr-3 flex items-center justify-center"
    : "flex h-10 w-10 items-center justify-center rounded-md";

  return (
    <Link
      to={to}
      className={`flex items-center ${baseClasses} rounded-lg text-sm transition-all duration-200 ${isActive
        ? "bg-whitePurple-100/60 text-purple-700 shadow-sm shadow-whitePurple-100/50 dark:bg-whitePurple-200/20 dark:text-purple-200 dark:shadow-purple-900/30"
        : "text-gray-600 hover:bg-whitePurple-50/70 hover:text-purple-700 dark:text-gray-400 dark:hover:bg-whitePurple-200/10 dark:hover:text-purple-200"
        }`}
    >
      <span className={iconClasses}>{icon}</span>
      <span className={isOpen ? "" : "hidden"}>{label}</span>
    </Link>
  );
}

function SidebarSection({ title, icon, isOpen, to, iconTo, isExpanded, onToggle, trailing, children }: SidebarSectionProps) {
  const iconLinkTarget = iconTo ?? to ?? "/";

  return (
    <div className="w-full">
      <div className={`flex items-center ${isOpen ? "justify-between px-4" : "justify-center"} py-3`}>
        <div className={`flex items-center ${isOpen ? "" : "justify-center"}`}>
          {isOpen ? (
            <Link
              to={iconLinkTarget}
              className="flex items-center text-sm font-medium text-gray-700 transition hover:text-purple-600 dark:text-gray-300 dark:hover:text-purple-200"
            >
              <span className="mr-3 flex h-6 w-6 items-center justify-center">{icon}</span>
              <span>{title}</span>
            </Link>
          ) : (
            <Link to={iconLinkTarget} className="flex h-10 w-10 items-center justify-center rounded-md">
              <span className="flex h-6 w-6 items-center justify-center">{icon}</span>
            </Link>
          )}
        </div>
        {isOpen && (
          <div className="flex items-center gap-1">
            {trailing}
            {onToggle && typeof isExpanded === 'boolean' && (
              <button
                type="button"
                onClick={onToggle}
                className="rounded-md p-1 text-gray-500 hover:text-purple-600 hover:bg-whitePurple-100/60 dark:text-gray-400 dark:hover:text-purple-200 dark:hover:bg-whitePurple-200/20 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-purple-400"
                aria-label={isExpanded ? `Collapse ${title}` : `Expand ${title}`}
              >
                {isExpanded ? (
                  <ChevronDownIcon className="h-4 w-4" />
                ) : (
                  <ChevronRightIcon className="h-4 w-4" />
                )}
              </button>
            )}
            {to && (
              <Link
                to={to}
                className="p-1 rounded-md text-gray-500 hover:text-purple-600 hover:bg-whitePurple-100/60 dark:text-gray-400 dark:hover:text-purple-200 dark:hover:bg-whitePurple-200/20 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-purple-400"
                title={`New ${title}`}
              >
                <PlusIcon className="h-4 w-4" />
              </Link>
            )}
          </div>
        )}
      </div>
      {(!isOpen || onToggle == null || isExpanded) && children}
    </div>
  );
}


export function Sidebar({ isOpen, user, toggleSidebar, organizationId }: SidebarProps) {
  const location = useLocation();
  const { activeProject, projects } = useProject();
  const projectBasePath = activeProject?.id ? `/projects/${activeProject.id}` : null;
  const agentsIndexPath = projectBasePath ? `${projectBasePath}/agents` : '/new';
  const newAgentPath = projectBasePath ? `${projectBasePath}/new` : '/new';
  const integrationsPath = projectBasePath ? `${projectBasePath}/integrations` : '/integrations';
  const mcpGatewayPath = projectBasePath ? `${projectBasePath}/mcp-gateway` : '/mcp-gateway';
  const chicoryAgentPath = projectBasePath ? `${projectBasePath}/chicory-agent` : '/chicory-agent';
  const [sidebarAgents, setSidebarAgents] = useState<Agent[]>([]);
  const [isLoadingAgents, setIsLoadingAgents] = useState(false);
  const fetcher = useFetcher();
  const [agentsExpanded, setAgentsExpanded] = useState(true);

  // Filter projects to only those the user is a member of
  const userProjects = useMemo(
    () => user?.userId
      ? projects.filter(project => project.members?.includes(user.userId))
      : projects,
    [user?.userId, projects]
  );

  // Fetch agents when active project changes
  useEffect(() => {
    // Only fetch agents if the user is actually a member of the active project
    const isUserMemberOfActiveProject = activeProject?.id && userProjects.some(p => p.id === activeProject.id);

    if (isUserMemberOfActiveProject && fetcher.state === 'idle') {
      setIsLoadingAgents(true);
      // Use fetcher to get agents for the active project
      fetcher.load(`/api/projects/${activeProject.id}/agents`);
    } else if (!activeProject?.id || !isUserMemberOfActiveProject) {
      // Clear agents if no active project or user is not a member
      setSidebarAgents([]);
      setIsLoadingAgents(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeProject?.id, userProjects]);

  // Update agents when fetcher data changes
  useEffect(() => {
    if (fetcher.data && typeof fetcher.data === 'object' && 'agents' in fetcher.data && Array.isArray(fetcher.data.agents)) {
      setSidebarAgents(fetcher.data.agents as Agent[]);
      setIsLoadingAgents(false);
    } else if (fetcher.state === 'idle' && fetcher.data && typeof fetcher.data === 'object' && !('agents' in fetcher.data)) {
      setSidebarAgents([]);
      setIsLoadingAgents(false);
    }
  }, [fetcher.data, fetcher.state]);

  // Memoized sorted agents (by updated_at, most recent first)
  const sortedAgents = useMemo(() => {
    return [...sidebarAgents].sort((a, b) =>
      new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    );
  }, [sidebarAgents]);

  // Render agent links
  const renderAgentLinks = (agents: Agent[]) => {
    return agents.map((agent) => {
      const agentPath = projectBasePath ? `${projectBasePath}/agents/${agent.id}` : `/agents/${agent.id}`;
      const isActive = location.pathname === agentPath;
      return (
        <Link
          key={agent.id}
          to={agentPath}
          className={`flex items-center px-6 py-2 text-sm transition-all duration-200 ${isActive
            ? "bg-whitePurple-100/60 text-purple-700 shadow-sm shadow-whitePurple-100/50 dark:bg-whitePurple-200/20 dark:text-purple-200 dark:shadow-purple-900/30"
            : "text-gray-600 hover:bg-whitePurple-50/70 hover:text-purple-700 dark:text-gray-400 dark:hover:bg-whitePurple-200/10 dark:hover:text-purple-200"
            }`}
        >
          <span className="truncate">{agent.name}</span>
        </Link>
      );
    });
  };

  return (
    <aside
      className={`${isOpen ? 'w-52 border-none' : 'w-14'
        } relative flex flex-col fixed inset-y-0 z-10 bg-transparent border-r border-gray-200 dark:bg-gray-900 dark:border-gray-700 transition-all duration-300 md:relative`}
    >
      {/* Logo and toggle button */}
      <div className={`flex pt-4 pb-6 items-center ${isOpen ? 'pl-4 justify-between' : 'justify-center'} w-full`}>
        <Link to={agentsIndexPath} className="flex h-12 w-12 items-center justify-center rounded-md">
          <img src="/icons/chicory-icon.png" alt="Chicory Logo" className="h-12 w-12" />
        </Link>
      </div>

      {/* Workzone Link */}
      <div className={`${isOpen ? 'px-3' : 'px-0 flex justify-center'} pb-2 pt-3`}>
        <Link
          to="/workzone"
          className={`flex items-center ${isOpen ? 'px-4 justify-start w-full' : 'px-0 justify-center w-full'
            } py-2 rounded-lg my-1 text-sm transition-all duration-200 ${isOpen
              ? `border-2 border-gray-200 text-gray-600 dark:border-gray-700 dark:text-gray-400 hover:border-purple-300 hover:text-purple-700 dark:hover:border-purple-600 dark:hover:text-purple-200 ${location.pathname === '/workzone' ? 'border-purple-400 text-purple-700 dark:border-purple-500 dark:text-purple-200' : ''
              }`
              : 'text-gray-600 dark:text-gray-400 hover:text-purple-700 dark:hover:text-purple-200'
            }`}
        >
          <span className={isOpen ? 'mr-3 flex items-center justify-center' : 'flex h-10 w-10 items-center justify-center rounded-md'}>
            <CodeBracketIcon className="h-6 w-6" />
          </span>
          <span className={isOpen ? '' : 'hidden'}>Workzone</span>
        </Link>
      </div>

      {/* Project Selector */}
      {organizationId && (
        <div className="pb-2">
          {isOpen && (
            <div className="px-4 pb-1">
              <span className="text-xs text-gray-500 dark:text-gray-400">Project</span>
            </div>
          )}
          <ProjectSelector
            organizationId={organizationId}
            isOpen={isOpen}
            userId={user?.userId}
          />
        </div>
      )}

      {/* Divider */}
      <div className={`${isOpen ? 'mx-4' : 'mx-2'} mb-2 border-t border-gray-200/50 dark:border-gray-700/50`} />

      {/* Navigation links */}
      <nav className="audit-trail-scroll overflow-y-auto flex-1 pt-2 pb-4 flex flex-col items-center w-full min-h-0">
        {/* Only show project-specific navigation if user has access to projects */}
        {userProjects.length > 0 && activeProject ? (
          <>
            {/* Agents section */}
            <SidebarSection
              title="Agents"
              icon={<GiVintageRobot className="h-5 w-5" />}
              isOpen={isOpen}
              to={newAgentPath}
              iconTo={agentsIndexPath}
              isExpanded={agentsExpanded}
              onToggle={() => setAgentsExpanded(prev => !prev)}
            >
              {isOpen && agentsExpanded && (
                <div className="mt-2 pl-9 max-h-96 overflow-y-auto audit-trail-scroll">
                  {sortedAgents.length > 0 ? (
                    renderAgentLinks(sortedAgents)
                  ) : (
                    <div className="pl-4 pr-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                      No agents found
                    </div>
                  )}
                </div>
              )}
            </SidebarSection>

            {/* Chicory Agent link */}
            <div className={`${isOpen ? 'px-3' : 'px-0 flex justify-center'} py-1`}>
              <SidebarLink
                to={chicoryAgentPath}
                icon={<ChatBubbleBottomCenterTextIcon className="h-6 w-6" />}
                label="Chicory Agent"
                isOpen={isOpen}
              />
            </div>

            <div className="flex flex-col items-center w-full">
              <SidebarLink
                to={integrationsPath}
                icon={<CubeTransparentIcon className="h-6 w-6" />}
                label="Integrations"
                isOpen={isOpen}
              />
              <SidebarLink
                to={mcpGatewayPath}
                icon={
                  <img
                    height="24"
                    width="24"
                    src="https://unpkg.com/@lobehub/icons-static-svg@latest/icons/mcp.svg"
                    className="dark:invert"
                    alt="MCP Gateway"
                  />
                }
                label="MCP Gateway"
                isOpen={isOpen}
              />
            </div>
          </>
        ) : (
          /* Show message when user has no project access */
          isOpen && (
            <div className="px-4 py-6 text-center">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                {userProjects.length === 0 ? 'No projects available' : 'No project selected'}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-500">
                {userProjects.length === 0
                  ? 'Join a project to access agents, integrations, and more'
                  : 'Select a project to continue'}
              </p>
            </div>
          )
        )}
        {!isOpen && (
          <button
            onClick={toggleSidebar}
            className="mt-auto flex h-10 w-10 items-center justify-center rounded-full text-purple-500 transition hover:bg-whitePurple-50/60 hover:text-purple-600 dark:text-gray-300 dark:hover:bg-whitePurple-200/10 dark:hover:text-purple-300"
            title="Expand sidebar"
          >
            <ChevronDoubleRightIcon className="h-5 w-5" />
          </button>
        )}
      </nav>
      <div className="mt-auto w-full px-3 pb-4 flex flex-col items-center gap-3">
        <div className="w-full">
          {user && <UserMenu user={user} compact={!isOpen} className={isOpen ? "w-full" : ""} onClose={toggleSidebar} showCloseButton={isOpen} />}
        </div>
      </div>
    </aside>
  );
}
