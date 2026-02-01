import { useState, useRef } from "react";
import { Dialog } from "@headlessui/react";
import { CloudArrowUpIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { Form, useNavigation } from "@remix-run/react";

interface GenericFileUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  category: "document" | "code";
  onSuccess?: (ds: any) => void;
  existingDocument?: any | null; // for enforcing 1 doc limit
}

export default function GenericFileUploadModal({
  isOpen,
  onClose,
  projectId,
  category,
  onSuccess,
  existingDocument
}: GenericFileUploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigation = useNavigation();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setName(e.target.files[0].name);
    }
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    if (!file) {
      e.preventDefault();
      setError("Please select a file.");
      return;
    }
    if (!name.trim()) {
      e.preventDefault();
      setError("Please provide a name for the data source.");
      return;
    }
    if (category === "document" && existingDocument) {
      e.preventDefault();
      setError("You can only upload one document at a time. Delete the existing one first.");
      return;
    }
  };

  const isUploading = navigation.state === "submitting";

  return (
    <Dialog open={isOpen} onClose={onClose} className="fixed z-50 inset-0 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="fixed inset-0 bg-black opacity-30" aria-hidden="true" />
        <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-auto p-6 z-10">
          <div className="mb-2 text-xs text-blue-500 font-bold">DEBUG: File Upload Modal Open</div>
          <button
            type="button"
            className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            onClick={onClose}
            aria-label="Close"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
          <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Upload {category === "document" ? "Document" : "Code"} File
          </Dialog.Title>
          <Form reloadDocument onSubmit={handleSubmit} method="post" encType="multipart/form-data" action={`/projects/${projectId}/integrations`} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                File <span className="text-red-500">*</span>
              </label>
              <input
                type="file"
                ref={fileInputRef}
                accept={category === "document" ? ".pdf,.doc,.docx,.txt,.md" : undefined}
                onChange={handleFileChange}
                className="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                disabled={isUploading}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                className="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                disabled={isUploading}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Description
              </label>
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                className="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                disabled={isUploading}
                rows={2}
              />
            </div>
            {error && <div className="text-red-500 text-xs">{error}</div>}
            <div className="flex items-center justify-between mt-4">
              <button
                type="submit"
                className="inline-flex items-center px-4 py-2 bg-lime-600 text-white font-semibold rounded hover:bg-lime-700 focus:outline-none focus:ring-2 focus:ring-lime-500"
                disabled={isUploading}
              >
                <CloudArrowUpIcon className="h-5 w-5 mr-2" />
                {isUploading ? "Uploading..." : `Upload ${category === "document" ? "Document" : "Code"}`}
              </button>
            </div>
          <input type="hidden" name="_action" value="uploadGenericFile" />
            <input type="hidden" name="projectId" value={projectId} />
<input type="hidden" name="category" value={category} />
</Form>
        </div>
      </div>
    </Dialog>
  );
}
