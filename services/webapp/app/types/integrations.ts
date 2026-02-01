import type { 
  TrainingJob, 
  DataSourceCredential, 
  DataSourceTypeDefinition,
  DataSourceFieldDefinition 
} from '~/services/chicory.server';

// Re-export types from chicory.server for convenience
export type { 
  TrainingJob, 
  DataSourceCredential, 
  DataSourceTypeDefinition,
  DataSourceFieldDefinition 
} from '~/services/chicory.server';

// Extended integration types
export interface IntegrationType extends DataSourceTypeDefinition {
  connected?: boolean;
  configuredSources?: DataSourceCredential[];
}

// Integration categories
export type IntegrationCategory = 
  | 'databases' 
  | 'cloud_storage' 
  | 'apis' 
  | 'files' 
  | 'productivity' 
  | 'analytics' 
  | 'other';

// Training status types
export type TrainingStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

// Component prop types
export interface BaseComponentProps {
  className?: string;
}

export interface EmptyStateProps extends BaseComponentProps {
  icon?: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
} 