// Export all handler classes
export { BaseActionHandler, MultiFileUploadHandler, SimpleActionHandler } from './base';
export { ActionRouter, actionRouter } from './router';
export { CsvUploadHandler, ExcelUploadHandler, GenericFileUploadHandler, createFileUploadHandler } from './file-upload-handler';
export { DataSourceHandler } from './data-source-handler';
export { TrainingHandler } from './training-handler';
export { ConnectionTestHandler } from './connection-test-handler';
export { ProjectHandler } from './project-handler';

// Import handlers for registration
import { actionRouter } from './router';
import { CsvUploadHandler, ExcelUploadHandler, GenericFileUploadHandler } from './file-upload-handler';
import { DataSourceHandler } from './data-source-handler';
import { TrainingHandler } from './training-handler';
import { ConnectionTestHandler } from './connection-test-handler';
import { ProjectHandler } from './project-handler';

// ========================================
// REGISTER ALL HANDLERS
// ========================================

// File upload handlers
actionRouter.register('uploadCsv', new CsvUploadHandler(), {
  description: 'Handle CSV file uploads with multiple file support'
});

actionRouter.register('uploadExcel', new ExcelUploadHandler(), {
  description: 'Handle Excel file uploads with multiple file support'
});

actionRouter.register('uploadGenericFile', new GenericFileUploadHandler(), {
  description: 'Handle generic document and code file uploads'
});

// Data source CRUD handlers
const dataSourceHandler = new DataSourceHandler();
actionRouter.register('createDataSource', dataSourceHandler, {
  description: 'Create new data source configurations'
});

actionRouter.register('editDataSource', dataSourceHandler, {
  description: 'Update existing data source configurations'
});

actionRouter.register('deleteDataSource', dataSourceHandler, {
  description: 'Delete data source configurations'
});

// Training handlers
actionRouter.register('startTraining', new TrainingHandler(), {
  description: 'Start new training jobs'
});

// Connection test handlers
const connectionTestHandler = new ConnectionTestHandler();
actionRouter.register('testConnection', connectionTestHandler, {
  description: 'Test data source connections'
});

actionRouter.register('validateCredentials', connectionTestHandler, {
  description: 'Validate data source credentials'
});

// Project handlers
actionRouter.register('create-project', new ProjectHandler(), {
  description: 'Create new projects'
});

// Log registered handlers
console.log(`[ActionHandlers] Registered ${Object.keys(actionRouter.getHandlerInfo()).length} action handlers:`, 
  Object.keys(actionRouter.getHandlerInfo()).join(', '));

// Export the configured router
export { actionRouter as configuredActionRouter }; 