import { useState, useEffect } from "react";
import { useFetcher } from "@remix-run/react";
import { XMarkIcon, KeyIcon, EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";

interface AddEnvVariableModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentId: string;
  onSuccess?: () => void;
  actionPath?: string;
}

export default function AddEnvVariableModal({ 
  isOpen, 
  onClose, 
  agentId, 
  onSuccess,
  actionPath
}: AddEnvVariableModalProps) {
  const fetcher = useFetcher();
  
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [description, setDescription] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showValue, setShowValue] = useState(false);
  
  // Check if submission was successful
  useEffect(() => {
    const data = fetcher.data as { success?: boolean; intent?: string; error?: string } | undefined;
    if (data?.success && data?.intent === "addEnvVariable") {
      onSuccess?.();
      resetForm();
    } else if (data?.error) {
      setErrors({ submit: data.error });
    }
  }, [fetcher.data, onSuccess]);
  
  const resetForm = () => {
    setKey("");
    setValue("");
    setDescription("");
    setErrors({});
    setShowValue(false);
  };
  
  // Reserved environment variable keys that conflict with system keys
  const RESERVED_KEYS = ["ANTHROPIC_API_KEY"];
  
  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    const trimmedKey = key.trim().toUpperCase();
    
    if (!key.trim()) {
      newErrors.key = "Variable name is required";
    } else if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key.trim())) {
      newErrors.key = "Variable name must start with a letter or underscore and contain only letters, numbers, and underscores";
    } else if (RESERVED_KEYS.includes(trimmedKey)) {
      newErrors.key = `"${trimmedKey}" is a reserved system key. Use a prefix like "MY_${trimmedKey}" or "CUSTOM_${trimmedKey}" instead.`;
    }
    
    if (!value.trim()) {
      newErrors.value = "Value is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    const formData = new FormData();
    formData.append("intent", "addEnvVariable");
    formData.append("key", key.trim());
    formData.append("value", value.trim());
    if (description.trim()) {
      formData.append("description", description.trim());
    }
    
    fetcher.submit(formData, {
      method: "post",
      action: actionPath ?? '.'
    });
  };
  
  const isSubmitting = fetcher.state !== "idle";
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen p-4">
        {/* Glassmorphism backdrop */}
        <div 
          className="fixed inset-0 bg-gradient-to-br from-emerald-900/20 via-gray-900/50 to-emerald-900/20 backdrop-blur-sm transition-opacity" 
          aria-hidden="true"
          onClick={onClose}
        />
        
        {/* Glassmorphism modal with emerald theme */}
        <div className="relative inline-block w-full max-w-lg align-middle transition-all transform">
          <div className="relative bg-white/90 dark:bg-gray-900/90 backdrop-blur-xl rounded-2xl shadow-2xl border border-emerald-500/20 dark:border-emerald-400/20 overflow-hidden">
            {/* Emerald gradient glow effect */}
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 via-transparent to-emerald-600/10 pointer-events-none" />
            {/* Header with gradient */}
            <div className="relative px-6 pt-6 pb-4 bg-gradient-to-r from-emerald-600/10 to-emerald-500/10 border-b border-emerald-500/20">
              <button
                type="button"
                className="absolute top-4 right-4 p-2 rounded-lg bg-white/10 hover:bg-white/20 backdrop-blur-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-all focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                onClick={onClose}
              >
                <span className="sr-only">Close</span>
                <XMarkIcon className="h-5 w-5" />
              </button>
              
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-emerald-500/20 rounded-lg backdrop-blur-sm">
                  <KeyIcon className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold bg-gradient-to-r from-emerald-600 to-emerald-500 bg-clip-text text-transparent">
                    Add Environment Variable
                  </h3>
                  <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                    Configure a new environment variable for this agent
                  </p>
                </div>
              </div>
            </div>
          
            <div className="p-6 space-y-6">
              {errors.submit && (
                <div className="p-3 bg-red-50/50 dark:bg-red-900/20 backdrop-blur-sm border border-red-200/50 dark:border-red-800/50 rounded-lg">
                  <p className="text-sm text-red-800 dark:text-red-200">{errors.submit}</p>
                </div>
              )}
              
              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Key */}
                <div className="space-y-2">
                  <label htmlFor="envKey" className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                    Variable Name *
                  </label>
                  <input
                    type="text"
                    id="envKey"
                    value={key}
                    onChange={(e) => setKey(e.target.value.toUpperCase())}
                    className={`w-full px-4 py-2.5 rounded-lg border backdrop-blur-sm transition-all font-mono
                      ${errors.key 
                        ? 'border-red-300 dark:border-red-600 bg-red-50/50 dark:bg-red-900/10' 
                        : 'border-gray-300/50 dark:border-gray-600/50 bg-white/50 dark:bg-gray-800/50 hover:bg-white/70 dark:hover:bg-gray-800/70 focus:bg-white dark:focus:bg-gray-800'
                      }
                      text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400
                      focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500`}
                    placeholder="e.g., API_KEY, DATABASE_URL"
                    disabled={isSubmitting}
                  />
                  {errors.key && (
                    <p className="text-xs text-red-600 dark:text-red-400">{errors.key}</p>
                  )}
                </div>

                {/* Value */}
                <div className="space-y-2">
                  <label htmlFor="envValue" className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                    Value *
                  </label>
                  <div className="relative">
                    <input
                      type={showValue ? "text" : "password"}
                      id="envValue"
                      value={value}
                      onChange={(e) => setValue(e.target.value)}
                      className={`w-full px-4 py-2.5 pr-10 rounded-lg border backdrop-blur-sm transition-all
                        ${errors.value 
                          ? 'border-red-300 dark:border-red-600 bg-red-50/50 dark:bg-red-900/10' 
                          : 'border-gray-300/50 dark:border-gray-600/50 bg-white/50 dark:bg-gray-800/50 hover:bg-white/70 dark:hover:bg-gray-800/70 focus:bg-white dark:focus:bg-gray-800'
                        }
                        text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400
                        focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500`}
                      placeholder="Enter the value"
                      disabled={isSubmitting}
                    />
                    <button
                      type="button"
                      onClick={() => setShowValue(!showValue)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 transition-colors"
                      aria-label={showValue ? "Hide value" : "Show value"}
                    >
                      {showValue ? (
                        <EyeSlashIcon className="h-5 w-5" />
                      ) : (
                        <EyeIcon className="h-5 w-5" />
                      )}
                    </button>
                  </div>
                  {errors.value && (
                    <p className="text-xs text-red-600 dark:text-red-400">{errors.value}</p>
                  )}
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Value will be stored securely and masked in the UI
                  </p>
                </div>

                {/* Description */}
                <div className="space-y-2">
                  <label htmlFor="envDescription" className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                    Description
                  </label>
                  <input
                    type="text"
                    id="envDescription"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-lg border border-gray-300/50 dark:border-gray-600/50 
                      bg-white/50 dark:bg-gray-800/50 hover:bg-white/70 dark:hover:bg-gray-800/70 
                      focus:bg-white dark:focus:bg-gray-800 backdrop-blur-sm
                      text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400
                      focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
                    placeholder="Optional description for this variable"
                    disabled={isSubmitting}
                  />
                </div>

                {/* Action Buttons */}
                <div className="flex justify-end space-x-3 pt-2">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-5 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 
                      bg-white/50 dark:bg-gray-700/50 backdrop-blur-sm
                      border border-gray-300/50 dark:border-gray-600/50 rounded-lg 
                      hover:bg-white/70 dark:hover:bg-gray-700/70 
                      focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all"
                    disabled={isSubmitting}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2.5 text-sm font-medium text-white 
                      bg-gradient-to-r from-emerald-600 to-emerald-500 
                      hover:from-emerald-700 hover:to-emerald-600
                      border border-transparent rounded-lg shadow-lg shadow-emerald-500/25
                      focus:outline-none focus:ring-2 focus:ring-emerald-500/50 
                      disabled:opacity-50 disabled:cursor-not-allowed 
                      flex items-center transition-all transform hover:scale-105"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Adding...
                      </>
                    ) : (
                      'Add Variable'
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
