import path from 'path';
import fs from 'fs';

/**
 * Test data paths and generators
 */

// Base path for test data
export const TEST_DATA_DIR = path.resolve(__dirname, '../test-data');

// File paths
export const TEST_FILES = {
  sampleCsv: path.join(TEST_DATA_DIR, 'sample.csv'),
  sampleFolder: path.join(TEST_DATA_DIR, 'sample-folder'),
};

/**
 * Generate a unique name for test resources
 */
export function generateUniqueName(prefix: string): string {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 8);
  return `${prefix}-${timestamp}-${random}`;
}

/**
 * Generate test agent name
 */
export function generateAgentName(): string {
  return generateUniqueName('E2E-Agent');
}

/**
 * Generate test project name
 */
export function generateProjectName(): string {
  return generateUniqueName('E2E-Project');
}

/**
 * Generate test data source name
 */
export function generateDataSourceName(): string {
  return generateUniqueName('E2E-DataSource');
}

/**
 * Sample tasks for testing agents
 */
export const SAMPLE_TASKS = {
  simple: 'What is 2 + 2?',
  greeting: 'Hello, how are you?',
  dataQuestion: 'What data sources are available?',
  complexQuery: 'Can you analyze the data and provide a summary?',
};

/**
 * Sample agent instructions for testing
 */
export const SAMPLE_INSTRUCTIONS = {
  basic: 'You are a helpful assistant for testing purposes. Respond concisely.',
  dataAnalyst: `You are a data analyst assistant. Your job is to:
1. Answer questions about the available data
2. Provide insights and summaries
3. Be accurate and concise in your responses`,
  codeHelper: `You are a code assistant. Help users understand and work with code.
Always provide clear explanations and examples when appropriate.`,
};

/**
 * Create sample CSV content
 */
export function createSampleCsvContent(): string {
  return `id,name,value,category
1,Item A,100,Category 1
2,Item B,200,Category 2
3,Item C,150,Category 1
4,Item D,300,Category 3
5,Item E,250,Category 2
`;
}

/**
 * Create sample folder with files
 */
export function createSampleFolder(): void {
  const folderPath = TEST_FILES.sampleFolder;

  // Create folder if it doesn't exist
  if (!fs.existsSync(folderPath)) {
    fs.mkdirSync(folderPath, { recursive: true });
  }

  // Create sample files
  fs.writeFileSync(
    path.join(folderPath, 'readme.txt'),
    'This is a sample folder for E2E testing.\nIt contains multiple files.\n'
  );

  fs.writeFileSync(
    path.join(folderPath, 'data.csv'),
    'id,name,value\n1,Test,100\n2,Sample,200\n'
  );

  // Create a subfolder
  const subfolder = path.join(folderPath, 'subfolder');
  if (!fs.existsSync(subfolder)) {
    fs.mkdirSync(subfolder);
  }

  fs.writeFileSync(
    path.join(subfolder, 'nested-file.txt'),
    'This is a nested file in a subfolder.\n'
  );
}

/**
 * Create sample CSV file
 */
export function createSampleCsv(): void {
  const csvPath = TEST_FILES.sampleCsv;
  fs.writeFileSync(csvPath, createSampleCsvContent());
}

/**
 * Ensure all test data exists
 */
export function ensureTestDataExists(): void {
  // Create directory if it doesn't exist
  if (!fs.existsSync(TEST_DATA_DIR)) {
    fs.mkdirSync(TEST_DATA_DIR, { recursive: true });
  }

  // Create sample files
  createSampleCsv();
  createSampleFolder();
}

/**
 * Get BigQuery credentials path from environment
 */
export function getBigQueryCredentialsPath(): string {
  const credPath = process.env.BIGQUERY_SERVICE_ACCOUNT_PATH;
  if (!credPath) {
    throw new Error('BIGQUERY_SERVICE_ACCOUNT_PATH environment variable not set');
  }
  return credPath;
}

/**
 * Clean up test resources
 */
export function cleanupTestData(): void {
  // Remove sample CSV
  if (fs.existsSync(TEST_FILES.sampleCsv)) {
    fs.unlinkSync(TEST_FILES.sampleCsv);
  }

  // Remove sample folder
  if (fs.existsSync(TEST_FILES.sampleFolder)) {
    fs.rmSync(TEST_FILES.sampleFolder, { recursive: true, force: true });
  }
}
