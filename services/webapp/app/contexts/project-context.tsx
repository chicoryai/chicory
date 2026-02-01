import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import type { Project } from '~/services/chicory.server';

interface ProjectContextType {
  activeProject: Project | null;
  projects: Project[];
  setActiveProject: (project: Project | null) => void;
  setProjects: (projects: Project[]) => void;
  addProject: (project: Project) => void;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

interface ProjectProviderProps {
  children: ReactNode;
  initialProject?: Project | null;
  initialProjects?: Project[];
  authoritativeProjectId?: string | null;
}

export function ProjectProvider({ 
  children, 
  initialProject = null, 
  initialProjects = [],
  authoritativeProjectId = null,
}: ProjectProviderProps) {
  const [activeProject, setActiveProject] = useState<Project | null>(initialProject);
  const [projects, setProjects] = useState<Project[]>(initialProjects);

  useEffect(() => {
    setProjects(initialProjects);
  }, [initialProjects]);

  useEffect(() => {
    if (authoritativeProjectId) {
      setActiveProject(initialProject ?? null);
    } else if (!activeProject && initialProject) {
      setActiveProject(initialProject);
    }
  }, [authoritativeProjectId, initialProject, initialProject?.id, activeProject]);

  const addProject = (project: Project) => {
    setProjects(prev => [...prev, project]);
    setActiveProject(project); // Make the new project active
  };

  const value: ProjectContextType = {
    activeProject,
    projects,
    setActiveProject,
    setProjects,
    addProject,
  };

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  const context = useContext(ProjectContext);
  if (context === undefined) {
    throw new Error('useProject must be used within a ProjectProvider');
  }
  return context;
}
