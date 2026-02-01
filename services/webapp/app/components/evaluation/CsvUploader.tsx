/**
 * CsvUploader Component
 * Handles CSV file upload with drag-and-drop, validation, and preview
 */

import { useState, useRef, DragEvent } from 'react';
import { CloudArrowUpIcon, DocumentTextIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { clsx } from 'clsx';

export interface ParsedData {
  headers: string[];
  rows: string[][];
  isValid: boolean;
  errors: string[];
}

interface CsvUploaderProps {
  onFileSelect: (file: File, preview: ParsedData) => void;
  onError: (message: string) => void;
  maxSize?: number; // in MB
  required?: boolean;
  className?: string;
}

export function CsvUploader({
  onFileSelect,
  onError,
  maxSize = 10,
  required = false,
  className = ''
}: CsvUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ParsedData | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const requiredColumns = ['task', 'expected_output', 'evaluation_guideline'];
  
  const parseCSV = (text: string): ParsedData => {
    const lines = text.split('\n').filter(line => line.trim());
    if (lines.length === 0) {
      return {
        headers: [],
        rows: [],
        isValid: false,
        errors: ['CSV file is empty']
      };
    }
    
    // Parse headers
    const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
    
    // Validate required columns
    const errors: string[] = [];
    const missingColumns = requiredColumns.filter(col => !headers.includes(col));
    if (missingColumns.length > 0) {
      errors.push(`Missing required columns: ${missingColumns.join(', ')}`);
    }
    
    // Parse rows (max 5 for preview)
    const rows = lines.slice(1, 6).map(line => {
      const values = line.split(',').map(v => v.trim());
      return values;
    });
    
    return {
      headers,
      rows,
      isValid: errors.length === 0,
      errors
    };
  };
  
  const processFile = async (file: File) => {
    setIsProcessing(true);
    
    try {
      // Validate file type
      if (!file.name.endsWith('.csv')) {
        throw new Error('Only CSV files are accepted');
      }
      
      // Validate file size
      const maxSizeBytes = maxSize * 1024 * 1024;
      if (file.size > maxSizeBytes) {
        throw new Error(`File size must be less than ${maxSize}MB`);
      }
      
      // Read and parse file
      const text = await file.text();
      const parsed = parseCSV(text);
      
      if (!parsed.isValid) {
        throw new Error(parsed.errors.join('. '));
      }
      
      setFile(file);
      setPreview(parsed);
      onFileSelect(file, parsed);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to process file';
      onError(message);
      setFile(null);
      setPreview(null);
    } finally {
      setIsProcessing(false);
    }
  };
  
  const handleDragEnter = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };
  
  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget === e.target) {
      setIsDragging(false);
    }
  };
  
  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };
  
  const handleDrop = async (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      await processFile(files[0]);
    }
  };
  
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      await processFile(files[0]);
    }
  };
  
  const handleRemoveFile = () => {
    setFile(null);
    setPreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  
  return (
    <div className={className}>
      {!file ? (
        <div
          className={clsx(
            'relative rounded-lg border-2 border-dashed p-6 text-center transition-colors',
            isDragging
              ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
              : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500',
            isProcessing && 'opacity-50 pointer-events-none'
          )}
          onDragEnter={handleDragEnter}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileSelect}
            className="sr-only"
            id="csv-upload"
            required={required}
            aria-label="Upload CSV file"
          />
          
          <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
          
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            <label
              htmlFor="csv-upload"
              className="font-medium text-purple-600 dark:text-purple-400 hover:text-purple-500 cursor-pointer"
            >
              Click to upload
            </label>
            {' '}or drag and drop
          </p>
          
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            CSV file up to {maxSize}MB
          </p>
          
          {isProcessing && (
            <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80 rounded-lg">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-purple-500 border-t-transparent" />
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {/* File info */}
          <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="flex items-center gap-3">
              <DocumentTextIcon className="h-8 w-8 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {file.name}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
            </div>
            <button
              onClick={handleRemoveFile}
              className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
              aria-label="Remove file"
            >
              <XMarkIcon className="h-5 w-5 text-gray-500" />
            </button>
          </div>
          
          {/* Preview table */}
          {preview && preview.rows.length > 0 && (
            <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                      {preview.headers.map((header, i) => (
                        <th
                          key={i}
                          className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                        >
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                    {preview.rows.map((row, i) => (
                      <tr key={i}>
                        {row.map((cell, j) => (
                          <td
                            key={j}
                            className="px-4 py-2 text-sm text-gray-900 dark:text-gray-100 truncate max-w-xs"
                            title={cell}
                          >
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="px-4 py-2 bg-gray-50 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400">
                Showing first {preview.rows.length} rows of {file.name}
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Template download link */}
      <div className="mt-4 text-center">
        <a
          href="/templates/evaluation-template.csv"
          download
          className="text-sm text-purple-600 dark:text-purple-400 hover:text-purple-500 underline"
        >
          Download CSV template
        </a>
      </div>
    </div>
  );
}