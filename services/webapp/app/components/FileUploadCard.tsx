import { DocumentIcon, CodeBracketIcon, ArrowUpTrayIcon } from "@heroicons/react/24/outline";

interface FileUploadCardProps {
  category: "document" | "code";
  onUpload: () => void;
}

export default function FileUploadCard({ category, onUpload }: FileUploadCardProps) {
  const Icon = category === "document" ? DocumentIcon : CodeBracketIcon;
  
  return (
    <div className="bg-gray-50 dark:bg-gray-800/40 rounded-lg border border-gray-100 dark:border-gray-700 p-5 relative hover:shadow-md transition-shadow duration-200">
      <div className="flex items-center">
        <div className="flex-shrink-0 h-12 w-12 flex items-center justify-center rounded-full bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-700 shadow-sm">
          <Icon className="h-6 w-6 text-gray-600 dark:text-gray-300" />
        </div>
        <div className="ml-4">
          <h3 className="text-base font-medium text-gray-900 dark:text-white">
            {category === "document" ? "Document" : "Code"} Upload
          </h3>
        </div>
      </div>
      
      <div className="mt-4 flex justify-end">
        <button
          onClick={onUpload}
          className="inline-flex items-center px-4 py-2 bg-purple-500 text-white text-sm font-semibold rounded hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500"
        >
          <ArrowUpTrayIcon className="h-5 w-5 mr-2" />
          Upload
        </button>
      </div>
    </div>
  );
} 