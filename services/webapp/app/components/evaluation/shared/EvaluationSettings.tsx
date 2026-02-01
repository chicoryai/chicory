import React, { useState, useEffect } from 'react';
import type { Evaluation } from '~/services/chicory.server';
import { Button } from '~/components/Button';

interface EvaluationSettingsProps {
  evaluation: Evaluation;
  onSave: (settings: { name: string; description: string; criteria: string }) => Promise<void>;
  isLoading?: boolean;
}

export function EvaluationSettings({ evaluation, onSave, isLoading = false }: EvaluationSettingsProps) {
  const [settings, setSettings] = useState({
    name: evaluation.name,
    description: evaluation.description || '',
    criteria: evaluation.criteria || ''
  });
  
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Reset form when evaluation changes
  useEffect(() => {
    setSettings({
      name: evaluation.name,
      description: evaluation.description || '',
      criteria: evaluation.criteria || ''
    });
    setIsDirty(false);
    setError(null);
  }, [evaluation]);
  
  // Track if form has changes
  useEffect(() => {
    const hasChanges = 
      settings.name !== evaluation.name ||
      settings.description !== (evaluation.description || '') ||
      settings.criteria !== (evaluation.criteria || '');
    setIsDirty(hasChanges);
  }, [settings, evaluation]);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate required fields
    if (!settings.name.trim()) {
      setError('Evaluation name is required');
      return;
    }
    
    setIsSaving(true);
    setError(null);
    
    try {
      await onSave({
        name: settings.name.trim(),
        description: settings.description.trim(),
        criteria: settings.criteria.trim()
      });
      setIsDirty(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };
  
  const handleCancel = () => {
    setSettings({
      name: evaluation.name,
      description: evaluation.description || '',
      criteria: evaluation.criteria || ''
    });
    setError(null);
  };
  
  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Basic Settings */}
      <div className="relative shadow-sm shadow-whitePurple-100 dark:shadow-none bg-white/25 dark:bg-whitePurple-50/5 backdrop-blur-lg rounded-lg p-6 border border-whitePurple-100/70 dark:border-purple-900/20">
        <div className="absolute inset-0 bg-gradient-to-br from-white/10 via-transparent to-white/5 dark:from-transparent dark:to-transparent rounded-lg pointer-events-none" />
        <h3 className="relative text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Basic Settings</h3>
        <div className="relative space-y-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Evaluation Name
            </label>
            <input
              type="text"
              id="name"
              value={settings.name}
              onChange={(e) => setSettings({ ...settings, name: e.target.value })}
              className="w-full px-3 py-2 bg-white/50 dark:bg-gray-800 border border-gray-300/50 dark:border-purple-900/20 rounded-lg text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400/30 backdrop-blur-sm"
            />
          </div>
          
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              id="description"
              value={settings.description}
              onChange={(e) => setSettings({ ...settings, description: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 bg-white/50 dark:bg-gray-800 border border-gray-300/50 dark:border-purple-900/20 rounded-lg text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400/30 backdrop-blur-sm resize-none"
            />
          </div>
          
          <div>
            <label htmlFor="criteria" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Evaluation Criteria
            </label>
            <textarea
              id="criteria"
              value={settings.criteria}
              onChange={(e) => setSettings({ ...settings, criteria: e.target.value })}
              rows={4}
              className="w-full px-3 py-2 bg-white/50 dark:bg-gray-800 border border-gray-300/50 dark:border-purple-900/20 rounded-lg text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400/30 backdrop-blur-sm resize-none"
              placeholder="Define the criteria for evaluating test cases..."
            />
          </div>
        </div>
      </div>
      
      {/* Error Message */}
      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}
      
      {/* Actions */}
      <div className="flex justify-end gap-3">
        <Button 
          type="button" 
          variant="secondary"
          onClick={handleCancel}
          disabled={!isDirty || isSaving}
        >
          Cancel
        </Button>
        <Button 
          type="submit" 
          variant="primary"
          disabled={!isDirty || isSaving || isLoading}
        >
          {isSaving ? 'Saving...' : 'Save Settings'}
        </Button>
      </div>
    </form>
  );
}