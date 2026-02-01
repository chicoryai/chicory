/**
 * Type definitions for the Agent Playground panels
 */

import type { Agent, Evaluation, EvaluationRun, Tool } from "~/services/chicory.server";
import type { TrailItem } from "~/types/auditTrail";

// Re-export Tool type
export type { Tool };

// Tab types
export type TabType = 'configuration' | 'mcp-tools' | 'evaluations' | 'deployment' | 'test-cases' | 'runs' | string;

// Animation states
export type AnimationState = 'entering' | 'entered' | 'exiting' | 'exited';

// Panel visibility states
export interface PanelState {
  isOpen: boolean;
  activeTab: TabType;
  animationState: AnimationState;
  width: 'collapsed' | 'normal' | 'expanded';
}

// Configuration panel types
export interface AgentConfig {
  name: string;
  description: string;
  systemInstructions: string;
  outputFormat: string;
  tools: string[]; // Tool IDs
  isDirty?: boolean;
}

export interface ConfigurationPanelProps {
  agent: Agent;
  tools: Tool[];
  onSave: (config: AgentConfig) => Promise<void>;
  onReset: () => void;
  onDelete?: () => Promise<void>;
  isLoading?: boolean;
  error?: Error | null;
  className?: string;
}

// Evaluations panel types
export interface EvaluationStats {
  totalEvaluations: number;
  totalRuns: number;
  avgPassRate: number;
  totalTestCases: number;
  recentRuns?: EvaluationRun[];
}

export interface EvaluationsPanelProps {
  agent: Agent;
  evaluations: Evaluation[];
  stats: EvaluationStats;
  onRunEvaluation: (evalId: string) => Promise<void>;
  onCreateEvaluation: () => void;
  onDeleteEvaluation?: (evalId: string) => Promise<void>;
  onEditEvaluation?: (evalId: string) => void;
  currentRun?: EvaluationRun | null;
  isLoading?: boolean;
  error?: Error | null;
  className?: string;
}


// Section collapse states
export interface CollapsibleSectionProps {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  icon?: React.ReactNode;
  badge?: string | number;
  className?: string;
  onToggle?: (isOpen: boolean) => void;
}

// Tab component props
export interface TabsProps {
  activeTab: TabType;
  onChange: (tab: TabType) => void;
  tabs: TabConfig[];
  className?: string;
}

export interface TabConfig {
  id: TabType;
  label: string;
  icon?: React.ReactNode;
  badge?: string | number;
  disabled?: boolean;
}

// Animation configurations
export interface AnimationConfig {
  duration: {
    instant: number;
    fast: number;
    normal: number;
    slow: number;
    deliberate: number;
  };
  easing: {
    smooth: string;
    bounce: string;
    sharp: string;
    elastic: string;
  };
}

// Form field types for configuration
export interface FormField {
  name: string;
  label: string;
  type: 'text' | 'textarea' | 'select' | 'toggle' | 'code';
  value: any;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  helpText?: string;
  options?: { value: string; label: string }[];
  onChange: (value: any) => void;
  onBlur?: () => void;
}

// Tool selection types
export interface ToolSelectionProps {
  availableTools: Tool[];
  selectedTools: string[];
  onToolsChange: (tools: string[]) => void;
  isLoading?: boolean;
  className?: string;
}

// Evaluation run status
export type RunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface EvaluationRunProgress {
  runId: string;
  status: RunStatus;
  currentTest: number;
  totalTests: number;
  passedTests: number;
  failedTests: number;
  startTime: string;
  endTime?: string;
  logs?: string[];
}

// Mobile gesture handlers
export interface SwipeHandlers {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  threshold?: number;
  preventScroll?: boolean;
}

// Theme context for panels
export interface PanelTheme {
  backgroundColor: string;
  borderColor: string;
  textColor: string;
  accentColor: string;
  isDark: boolean;
}