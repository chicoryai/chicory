import { Dialog, Transition } from "@headlessui/react";
import { Fragment, ReactNode } from "react";
import { XMarkIcon } from "@heroicons/react/24/outline";

interface ModalProps {
  /**
   * Whether the modal is currently open
   */
  isOpen: boolean;
  /**
   * Function to call when the modal should close
   */
  onClose: () => void;
  /**
   * The title to display in the modal header
   */
  title: string;
  /**
   * The content of the modal
   */
  children: ReactNode;
  /**
   * Optional CSS class to apply to the modal panel
   */
  panelClassName?: string;
  /**
   * Optional CSS class to apply to the modal title
   */
  titleClassName?: string;
}

/**
 * A reusable modal component built on Headless UI's Dialog.
 * Provides consistent styling and behavior for all modals in the application.
 */
export function Modal({ 
  isOpen, 
  onClose, 
  title, 
  children,
  panelClassName = "w-full max-w-md",
  titleClassName = "text-lg font-medium leading-6 text-gray-900 dark:text-white"
}: ModalProps) {
  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" />
        </Transition.Child>
        
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel 
                className={`${panelClassName} transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 p-6 text-left align-middle shadow-xl transition-all`}
              >
                <div className="flex justify-between items-center mb-4">
                  <Dialog.Title as="h3" className={titleClassName}>
                    {title}
                  </Dialog.Title>
                  <button
                    type="button"
                    className="text-gray-400 hover:text-gray-500 dark:text-gray-500 dark:hover:text-gray-400 focus:outline-none"
                    onClick={onClose}
                  >
                    <span className="sr-only">Close</span>
                    <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                  </button>
                </div>
                <div>
                  {children}
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
}
