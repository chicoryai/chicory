/**
 * TopNavBar Component
 * Navigation bar with Build/Evaluate/Deploy navigation for agent views
 */

import { useNavigate } from "@remix-run/react";
import type { Agent } from "~/services/chicory.server";

interface TopNavBarProps {
  agent: Agent;
  projectId: string;
  activeView: 'build' | 'evaluate' | 'deploy' | 'manage';
  indicatorLabel?: string;
  className?: string;
  leftSlot?: React.ReactNode;
  rightSlot?: React.ReactNode;
}

export function TopNavBar({ agent, projectId, activeView, indicatorLabel, className = "", leftSlot, rightSlot }: TopNavBarProps) {
  const navigate = useNavigate();

  return (
    <header className={`px-6 pt-4 pb-2 bg-transparent ${className}`}>
      <div className="flex w-full items-center justify-between gap-4">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          {leftSlot}
        </div>
        {/* Main Navigation with optional indicator */}
        <div className="flex items-center gap-3">
          <div className="relative overflow-hidden rounded-2xl border border-whitePurple-100/50 shadow-md shadow-whitePurple-50/50 dark:border-whitePurple-200/30 dark:shadow-purple-900/20">
            {/* Light mode gradient background */}
            <div
              className="absolute inset-0 dark:hidden"
              style={{
                background: 'radial-gradient(circle at center, rgba(255, 255, 255, 0.9) 95%, rgba(245, 243, 255, 0.6) 100%)',
              }}
            />
            {/* Dark mode gradient background */}
            <div
              className="absolute inset-0 hidden dark:block"
              style={{
                background: 'radial-gradient(circle at center, rgba(17, 24, 39, 0.9) 95%, rgba(88, 28, 135, 0.2) 100%)',
              }}
            />

            <div className="relative flex items-center p-1">
              {/* Build Button */}
              <button
              onClick={() => navigate(`/projects/${projectId}/agents/${agent.id}/playground`)}
                className={`
                  relative px-6 py-2 rounded-xl text-sm font-medium transition-all duration-300 overflow-hidden
                  ${activeView === 'build'
                  ? 'text-purple-600 dark:text-purple-400 border border-whitePurple-100/50 dark:border-whitePurple-200/30 shadow-md shadow-whitePurple-50/50 dark:shadow-purple-900/20'
                  : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-white/10 dark:hover:bg-white/5 border border-transparent'
                }
              `}
            >
              {activeView === 'build' && (
                <>
                  {/* Light mode gradient */}
                  <div
                    className="absolute inset-0 dark:hidden pointer-events-none"
                    style={{
                      background: 'radial-gradient(circle at center, rgba(255, 255, 255, 0.9) 95%, rgba(245, 243, 255, 0.6) 100%)',
                    }}
                  />
                  {/* Dark mode gradient */}
                  <div
                    className="absolute inset-0 hidden dark:block pointer-events-none"
                    style={{
                      background: 'radial-gradient(circle at center, rgba(17, 24, 39, 0.9) 95%, rgba(88, 28, 135, 0.2) 100%)',
                    }}
                  />
                </>
              )}
              <span className="relative z-10">Build</span>
            </button>

            {/* Divider */}
            <div className="w-px h-5 bg-gradient-to-b from-transparent via-gray-300/30 to-transparent dark:via-gray-600/30" />

            {/* Evaluate Button */}
            <button
              onClick={() => navigate(`/projects/${projectId}/agents/${agent.id}/evaluations`)}
              className={`
                relative px-6 py-2 rounded-xl text-sm font-medium transition-all duration-300 overflow-hidden
                ${activeView === 'evaluate'
                  ? 'text-purple-600 dark:text-purple-400 border border-whitePurple-100/50 dark:border-whitePurple-200/30 shadow-md shadow-whitePurple-50/50 dark:shadow-purple-900/20'
                  : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-white/10 dark:hover:bg-white/5 border border-transparent'
                }
              `}
            >
              {activeView === 'evaluate' && (
                <>
                  {/* Light mode gradient */}
                  <div
                    className="absolute inset-0 dark:hidden pointer-events-none"
                    style={{
                      background: 'radial-gradient(circle at center, rgba(255, 255, 255, 0.9) 95%, rgba(245, 243, 255, 0.6) 100%)',
                    }}
                  />
                  {/* Dark mode gradient */}
                  <div
                    className="absolute inset-0 hidden dark:block pointer-events-none"
                    style={{
                      background: 'radial-gradient(circle at center, rgba(17, 24, 39, 0.9) 95%, rgba(88, 28, 135, 0.2) 100%)',
                    }}
                  />
                </>
              )}
              <span className="relative z-10">Evaluate</span>
            </button>

            {/* Divider */}
            <div className="w-px h-5 bg-gradient-to-b from-transparent via-gray-300/30 to-transparent dark:via-gray-600/30" />

            {/* Deploy Button */}
            <button
              onClick={() => navigate(`/projects/${projectId}/agents/${agent.id}/deploy`)}
              className={`
                relative px-6 py-2 rounded-xl text-sm font-medium transition-all duration-300 overflow-hidden
                ${activeView === 'deploy'
                  ? 'text-purple-600 dark:text-purple-400 border border-whitePurple-100/50 dark:border-whitePurple-200/30 shadow-md shadow-whitePurple-50/50 dark:shadow-purple-900/20'
                  : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-white/10 dark:hover:bg-white/5 border border-transparent'
                }
              `}
            >
              {activeView === 'deploy' && (
                <>
                  {/* Light mode gradient */}
                  <div
                    className="absolute inset-0 dark:hidden pointer-events-none"
                    style={{
                      background: 'radial-gradient(circle at center, rgba(255, 255, 255, 0.9) 95%, rgba(245, 243, 255, 0.6) 100%)',
                    }}
                  />
                  {/* Dark mode gradient */}
                  <div
                    className="absolute inset-0 hidden dark:block pointer-events-none"
                    style={{
                      background: 'radial-gradient(circle at center, rgba(17, 24, 39, 0.9) 95%, rgba(88, 28, 135, 0.2) 100%)',
                    }}
                  />
                </>
              )}
              <span className="relative z-10">Deploy</span>
            </button>

            {/* Divider */}
            <div className="w-px h-5 bg-gradient-to-b from-transparent via-gray-300/30 to-transparent dark:via-gray-600/30" />

            {/* Manage Button */}
            <button
              onClick={() => navigate(`/projects/${projectId}/agents/${agent.id}/manage`)}
              className={`
                relative px-6 py-2 rounded-xl text-sm font-medium transition-all duration-300 overflow-hidden
                ${activeView === 'manage'
                  ? 'text-purple-600 dark:text-purple-400 border border-whitePurple-100/50 dark:border-whitePurple-200/30 shadow-md shadow-whitePurple-50/50 dark:shadow-purple-900/20'
                  : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-white/10 dark:hover:bg-white/5 border border-transparent'
                }
              `}
            >
              {activeView === 'manage' && (
                <>
                  {/* Light mode gradient */}
                  <div
                    className="absolute inset-0 dark:hidden pointer-events-none"
                    style={{
                      background: 'radial-gradient(circle at center, rgba(255, 255, 255, 0.9) 95%, rgba(245, 243, 255, 0.6) 100%)',
                    }}
                  />
                  {/* Dark mode gradient */}
                  <div
                    className="absolute inset-0 hidden dark:block pointer-events-none"
                    style={{
                      background: 'radial-gradient(circle at center, rgba(17, 24, 39, 0.9) 95%, rgba(88, 28, 135, 0.2) 100%)',
                    }}
                  />
                </>
              )}
              <span className="relative z-10">Manage</span>
            </button>
            </div>
          </div>
          {indicatorLabel && (
            <div className="relative inline-flex items-center gap-2 rounded-xl border border-purple-200/70 bg-white/80 px-3 py-1 text-sm font-semibold text-purple-600 shadow-sm shadow-whitePurple-50/60 backdrop-blur dark:border-purple-500/40 dark:bg-purple-900/40 dark:text-purple-200">
              <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-inner shadow-emerald-200/40 dark:shadow-purple-300/40 animate-pulse" aria-hidden="true" />
              <span>{indicatorLabel}</span>
            </div>
          )}
        </div>
        <div className="flex flex-1 items-center justify-end gap-3">
          {rightSlot}
        </div>
      </div>
    </header>
  );
}
