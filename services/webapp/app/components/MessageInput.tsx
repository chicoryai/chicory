import React, { useState, useEffect, useRef } from 'react';
import { Form, useNavigation, useSubmit } from '@remix-run/react';

interface MessageInputProps {
  projectId: string;
  chatId: string;
  isDisabled?: boolean;
}

/**
 * Component for message input with auto-resize and submission handling
 */
export function MessageInput({ projectId, chatId, isDisabled = false }: MessageInputProps) {
  const [inputValue, setInputValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const navigation = useNavigation();
  const submit = useSubmit();
  const isSubmitting = navigation.state === "submitting";
  const prevNavigationStateRef = useRef(navigation.state);

  // Auto-resize textarea as user types
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [inputValue]);

  // Clear input after successful submission
  useEffect(() => {
    const prevState = prevNavigationStateRef.current;
    const currentState = navigation.state;
    prevNavigationStateRef.current = currentState;
    
    // If we were submitting and now we're idle, clear the input
    if (prevState === "submitting" && currentState === "idle") {
      setInputValue("");
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  }, [navigation.state]);

  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!inputValue.trim()) {
      return;
    }
    
    // Manually submit the form
    const formData = new FormData(formRef.current || undefined);
    submit(formData, { method: "post" });
    
    // Clear the input immediately after submission
    setInputValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  return (
    <Form 
      ref={formRef}
      method="post" 
      className="w-full relative" 
      onSubmit={handleSubmit}
    >
      <textarea
        ref={textareaRef}
        name="message"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        className="block w-full px-4 py-3 dark:bg-gray-800 bg-white border dark:border-gray-600 border-gray-200 rounded-md text-gray-800 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-purple-500 focus:border-purple-500 resize-none min-h-[80px] pr-12"
        placeholder="Give me a task..."
        required
        disabled={isSubmitting || isDisabled}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (inputValue.trim()) {
              handleSubmit(e);
            }
          }
        }}
      />
      <button
        type="submit"
        disabled={isSubmitting || !inputValue.trim() || isDisabled}
        className="absolute bottom-3 right-3 inline-flex items-center justify-center p-2 rounded-md bg-purple-600 text-white hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
          <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
        </svg>
      </button>
    </Form>
  );
}

export default MessageInput;
