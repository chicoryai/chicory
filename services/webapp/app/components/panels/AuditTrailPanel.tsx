/**
 * AuditTrailPanel Component
 * Displays real-time audit trail events in the right side panel
 */

import React, { useRef } from 'react';
import { motion } from 'framer-motion';
import { XMarkIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import AuditTrailItem from '~/components/AuditTrailItem';
import type { TrailItem, ToolResultBlock, UserMessageData } from '~/types/auditTrail';
import { extractToolResultBlocks, parseStructuredData, shouldDisplayTrailItem } from '~/types/auditTrail';

interface AuditTrailPanelProps {
  auditTrail: TrailItem[];
  onClose: () => void;
  isStreaming?: boolean;
  isMobile?: boolean;
}

export function AuditTrailPanel({
  auditTrail,
  onClose,
  isStreaming = false,
  isMobile = false
}: AuditTrailPanelProps) {
  const visibleTrail = React.useMemo(
    () => auditTrail.filter(item => shouldDisplayTrailItem(item)),
    [auditTrail]
  );

  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Build a map of tool results by tool_use_id for linking
  const toolResultsMap = React.useMemo(() => {
    const map = new Map<string, ToolResultBlock>();
    
    auditTrail.forEach(item => {
      if (item.message_type === 'UserMessage') {
        const parsed = parseStructuredData(item.structured_data);
        if (parsed && typeof parsed === 'object' && (parsed as any).type === 'UserMessage') {
          const results = extractToolResultBlocks(parsed as UserMessageData);
          results.forEach(result => {
            if (result.tool_use_id) {
              map.set(result.tool_use_id, result);
            }
          });
        }
      }
    });
    
    return map;
  }, [auditTrail]);

  return (
    <div className="flex h-full flex-col bg-white dark:bg-slate-900">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700">
        <div className="flex items-center gap-3">
          {isStreaming && (
            <ArrowPathIcon className="w-4 h-4 text-purple-500 animate-spin" />
          )}
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Execution Trail
          </h3>
        </div>
        <button
          onClick={onClose}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          aria-label="Close audit trail"
        >
          <XMarkIcon className="w-5 h-5 text-gray-500 dark:text-gray-400" />
        </button>
      </div>

      {/* Scrollable Content */}
      <div 
        ref={scrollContainerRef}
        className="audit-trail-scroll flex-1 px-4 py-4"
      >
        {visibleTrail.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400">
            <ArrowPathIcon className="w-8 h-8 mb-3 animate-pulse" />
            <p className="text-sm">Waiting for execution events...</p>
          </div>
        ) : (
          <div className="space-y-3">
            {visibleTrail.map((item, index) => (
              <motion.div
                key={`${item.id}-${item.message_id}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: index * 0.02 }}
              >
                <AuditTrailItem 
                  item={item} 
                  toolResults={toolResultsMap}
                />
              </motion.div>
            ))}
          </div>
        )}

        {/* Streaming Indicator */}
        {isStreaming && visibleTrail.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-4 flex items-center gap-2 text-sm text-purple-600 dark:text-purple-400"
          >
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse delay-75" />
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse delay-150" />
            </div>
            <span>Receiving events...</span>
          </motion.div>
        )}
      </div>

    </div>
  );
}
