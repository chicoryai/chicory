import { Modal } from "~/components/ui/Modal";
import { DataSourceForm } from "~/components/forms/DataSourceForm";
import type { DataSourceFieldDefinition } from "~/services/chicory.server";

interface DataSourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  dataSource: {
    id: string;
    name: string;
    requiredFields: DataSourceFieldDefinition[];
  };
  projectId: string;
  isEditing?: boolean;
  selectedDataSourceId?: string;
  initialValues?: Record<string, string>;
}

export default function DataSourceModal({
  isOpen,
  onClose,
  dataSource,
  projectId,
  isEditing = false,
  selectedDataSourceId = "",
  initialValues = {}
}: DataSourceModalProps) {
  if (!isOpen) return null;

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      title={isEditing ? `Manage ${dataSource.name} Connection` : `Connect to ${dataSource.name}`}
    >
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        {isEditing 
          ? "Update your connection settings below."
          : "Enter the required information to connect to this data source."
        }
      </p>
      
      <DataSourceForm 
        dataSource={dataSource} 
        projectId={projectId} 
        onSuccess={onClose}
        isEditing={isEditing}
        dataSourceId={selectedDataSourceId}
        initialValues={initialValues}
      />
    </Modal>
  );
}
