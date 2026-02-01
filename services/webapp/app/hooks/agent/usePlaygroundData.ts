import { useEffect, useRef } from "react";
import { useActionData, useNavigation } from "@remix-run/react";

export interface UsePlaygroundDataOptions {
  agentId?: string;
  onNewInvocation?: (data: {
    userTaskId: string;
    invocationId: string;
    assistantTaskId?: string;
  }) => void;
}

export interface UsePlaygroundDataReturn {
  taskListRef: React.RefObject<HTMLDivElement>;
  actionData: any;
  isSubmitting: boolean;
  error: string | null;
}

export function usePlaygroundData({
  agentId,
  onNewInvocation
}: UsePlaygroundDataOptions = {}): UsePlaygroundDataReturn {
  const actionData = useActionData();
  const navigation = useNavigation();
  const taskListRef = useRef<HTMLDivElement>(null);
  const processedInvocationRef = useRef<string | null>(null);

  useEffect(() => {
    processedInvocationRef.current = null;
  }, [agentId]);

  // Handle new invocation from action data
  useEffect(() => {
    if (
      actionData?.success &&
      actionData?.invocationId &&
      navigation.state === 'idle' &&
      (!actionData?.agentId || !agentId || actionData.agentId === agentId)
    ) {
      // Check if we've already processed this invocation
      const invocationKey = `${actionData.invocationId}-${actionData.assistantTaskId}`;
      if (processedInvocationRef.current === invocationKey) {
        console.log(`[PLAYGROUND_DATA] Already processed invocation ${invocationKey}, skipping`);
        return;
      }

      // Mark as processed
      processedInvocationRef.current = invocationKey;

      if (onNewInvocation) {
        onNewInvocation({
          userTaskId: actionData.userTaskId,
          invocationId: actionData.invocationId,
          assistantTaskId: actionData.assistantTaskId
        });
      }
    }
    // Don't retry on errors - just display them
  }, [actionData, navigation.state, onNewInvocation]);

  // Extract error from action data
  const error = actionData?.error || null;

  return {
    taskListRef,
    actionData,
    isSubmitting: navigation.state === 'submitting',
    error
  };
}
