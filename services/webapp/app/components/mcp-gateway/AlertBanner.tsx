import { CheckCircleIcon, ExclamationCircleIcon } from "@heroicons/react/24/solid";

interface AlertBannerProps {
  status: 'success' | 'error' | null;
  message: string;
  onDismiss: () => void;
  dismissing?: boolean;
}

export function AlertBanner({ 
  status, 
  message, 
  onDismiss, 
  dismissing = false 
}: AlertBannerProps) {
  if (!status) return null;

  return (
    <div className={`mb-4 px-4 py-3 rounded-lg shadow-md border-l-4 transition-all duration-300 ease-in-out transform ${
      dismissing ? 'opacity-0 scale-95 translate-y-2' : 'opacity-100 scale-100 translate-y-0'
    } ${
      status === 'success' 
        ? 'bg-gradient-to-r from-green-50 to-emerald-50 border-green-400 text-green-900' 
        : 'bg-gradient-to-r from-red-50 to-rose-50 border-red-400 text-red-900'
    }`} role="alert">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <div className={`flex-shrink-0 mr-3 p-0.5 rounded-full ${
            status === 'success' ? 'bg-green-100' : 'bg-red-100'
          }`}>
            {status === 'success' ? (
              <CheckCircleIcon className="h-5 w-5 text-green-600" aria-hidden="true" />
            ) : (
              <ExclamationCircleIcon className="h-5 w-5 text-red-600" aria-hidden="true" />
            )}
          </div>
          <div className="flex-1">
            <span className="font-medium text-sm">
              {status === 'success' ? 'Success: ' : 'Error: '}
              <span className="font-normal opacity-90">{message}</span>
            </span>
          </div>
        </div>
        <button
          onClick={onDismiss}
          className={`flex-shrink-0 ml-3 p-1 rounded-full transition-colors duration-200 ${
            status === 'success' 
              ? 'hover:bg-green-200 text-green-600' 
              : 'hover:bg-red-200 text-red-600'
          }`}
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}