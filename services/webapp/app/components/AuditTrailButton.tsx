import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { XMarkIcon } from '@heroicons/react/24/outline';
import TrailIcon from './icons/TrailIcon';
import AuditTrailItem from './AuditTrailItem';
import type { TrailItem, ToolResultBlock } from '~/types/auditTrail';
import { extractToolResultBlocks, shouldDisplayTrailItem } from '~/types/auditTrail';

interface AuditTrailButtonProps {
  agentTrail?: TrailItem[];  // Real-time streaming data
  s3Url?: string;             // Historical data URL
  s3Bucket?: string | null;
  s3Key?: string | null;
  taskId: string;
  className?: string;
}

const AuditTrailButton: React.FC<AuditTrailButtonProps> = ({ 
  agentTrail, 
  s3Url,
  s3Bucket,
  s3Key,
  taskId, 
  className = '' 
}) => {

  const [isOpen, setIsOpen] = useState(false);
  const [historicalTrail, setHistoricalTrail] = useState<TrailItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLDivElement>(null);
  const hasFetchedRef = useRef(false);
  const [drawerMetrics, setDrawerMetrics] = useState({ top: 0, height: 0 });
  const portalRef = useRef<HTMLDivElement | null>(null);
  const [hasPortal, setHasPortal] = useState(false);

  useEffect(() => {
    if (typeof document === 'undefined') {
      return;
    }

    const portalNode = document.createElement('div');
    portalNode.className = 'audit-trail-drawer-portal';
    document.body.appendChild(portalNode);
    portalRef.current = portalNode;
    setHasPortal(true);

    return () => {
      setHasPortal(false);
      if (portalRef.current && portalRef.current.parentNode) {
        portalRef.current.parentNode.removeChild(portalRef.current);
      }
      portalRef.current = null;
    };
  }, []);

  const fetchTrail = async () => {
    if (hasFetchedRef.current) return;

    const hasS3Info = Boolean(s3Bucket && (s3Key || s3Url));
    if (!s3Url && !hasS3Info) {
      hasFetchedRef.current = true;
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (hasS3Info) {
        if (s3Bucket) params.set('bucket', s3Bucket);
        if (s3Key) params.set('key', s3Key);
        if (!s3Key && s3Url) {
          params.set('url', s3Url);
        }
      } else if (s3Url) {
        params.set('url', s3Url);
      }

      const response = await fetch(`/api/audit-trail/${taskId}?${params.toString()}`);

      if (response.status === 404) {
        const data = await response.json().catch(() => ({}));
        setError(data?.error || 'Audit trail will be available after task completes');
      } else if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        setError(data?.error || 'Failed to load audit trail');
      } else {
        const data = await response.json();
        setHistoricalTrail(Array.isArray(data.trail) ? data.trail : []);
      }
    } catch (err) {
      console.error('Error fetching audit trail:', err);
      setError('Failed to load audit trail');
    } finally {
      setIsLoading(false);
      hasFetchedRef.current = true;
    }
  };

  // Reset historical data when task changes
  useEffect(() => {
    setHistoricalTrail([]);
    setError(null);
    hasFetchedRef.current = false;
    setIsOpen(false);
  }, [taskId, s3Url, s3Bucket, s3Key]);

  useEffect(() => {
    const updateWidth = () => {
      const availableWidth = Math.max(window.innerWidth - 32, 0);
      const panelWidth = availableWidth > 0 ? Math.min(32 * 16, availableWidth) : Math.min(32 * 16, window.innerWidth);
      const totalMargin = Math.min(panelWidth + 32, window.innerWidth);
      document.documentElement.style.setProperty('--audit-trail-panel-width', `${panelWidth}px`);
      document.documentElement.style.setProperty('--audit-trail-width', `${totalMargin}px`);

      const header = document.querySelector('[data-playground-header]');
      const headerRect = header instanceof HTMLElement ? header.getBoundingClientRect() : null;
      const headerHeight = headerRect ? headerRect.height : 72;
      const headerOffset = headerRect ? headerRect.top : 0;
      const minHeight = 220;
      const edgePadding = 8;
      const desiredTop = headerOffset + headerHeight + edgePadding;
      const maxTop = Math.max(window.innerHeight - minHeight - edgePadding, edgePadding);
      const top = Number.isFinite(desiredTop)
        ? Math.min(Math.max(desiredTop, edgePadding), maxTop)
        : edgePadding;
      const height = Math.max(window.innerHeight - top - edgePadding, minHeight) - 8;
      setDrawerMetrics({ top, height });
    };

    if (isOpen) {
      document.body.classList.add('audit-trail-open');
      updateWidth();
      window.addEventListener('resize', updateWidth);
      window.addEventListener('scroll', updateWidth, true);
    } else {
      document.body.classList.remove('audit-trail-open');
      document.documentElement.style.removeProperty('--audit-trail-width');
      document.documentElement.style.removeProperty('--audit-trail-panel-width');
    }

    return () => {
      window.removeEventListener('resize', updateWidth);
      window.removeEventListener('scroll', updateWidth, true);
      document.body.classList.remove('audit-trail-open');
      document.documentElement.style.removeProperty('--audit-trail-width');
      document.documentElement.style.removeProperty('--audit-trail-panel-width');
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    const handleClickOutside = (event: MouseEvent) => {
      if (
        drawerRef.current &&
        !drawerRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleEscape);
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      window.removeEventListener('keydown', handleEscape);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // Combine historical + streaming data
  type NormalizedTrailItem = TrailItem & { structured_data: any };

  const normalizeStructuredData = (item: TrailItem | (TrailItem & { structured_data: any })): any => {
    const raw = (item as any).structured_data ?? item;
    if (typeof raw === 'string') {
      try {
        return JSON.parse(raw);
      } catch (error) {
        console.warn('Failed to parse structured_data JSON for audit trail item', { item, error });
        return null;
      }
    }
    return raw;
  };

  const combinedTrail = useMemo(() => [...historicalTrail, ...(agentTrail || [])], [historicalTrail, agentTrail]);

  const normalizedTrail: NormalizedTrailItem[] = useMemo(
    () =>
      combinedTrail.map(item => ({
        ...item,
        structured_data: normalizeStructuredData(item)
      })),
    [combinedTrail]
  );

  const toolResultsMap = useMemo(() => {
    const map = new Map<string, ToolResultBlock>();
    normalizedTrail.forEach(item => {
      const data = item.structured_data;
      if (data && typeof data === 'object' && data.type === 'UserMessage') {
        const results = extractToolResultBlocks(data);
        results.forEach(result => {
          if (result.tool_use_id) {
            map.set(result.tool_use_id, result);
          }
        });
      }
    });
    return map;
  }, [normalizedTrail]);

  const renderedTrailItems = useMemo(() => (
    normalizedTrail
      .map((item, index) => {
        if (!shouldDisplayTrailItem(item)) {
          return null;
        }
        return (
          <AuditTrailItem
            key={`${item.id}-${item.message_id}-${index}`}
            item={item}
            toolResults={toolResultsMap}
          />
        );
      })
      .filter((node): node is React.ReactElement => node !== null)
  ), [normalizedTrail, toolResultsMap]);

  const visibleCount = renderedTrailItems.length;

  // Don't show button if no trail data is available
  if (!s3Url && !s3Bucket && (!agentTrail || agentTrail.length === 0)) {
    return null;
  }

  const handleToggle = () => {
    setIsOpen(prev => {
      const next = !prev;
      if (next) {
        fetchTrail();
      }
      return next;
    });
  };

  return (
    <div className={`inline-flex ${className}`}>
      <button
        ref={buttonRef}
        onClick={handleToggle}
        className={`
          group ml-2 p-1.5 rounded-md
          text-gray-400 hover:text-purple-500 dark:text-gray-500 dark:hover:text-purple-400
          hover:bg-whitePurple-50 dark:hover:bg-purple-900/20
          transition-all duration-200
          ${isOpen ? 'text-purple-600 dark:text-purple-300 bg-whitePurple-50 dark:bg-purple-900/20' : ''}
        `}
        title="View Execution Trail"
        aria-label="View execution trail for this message"
        aria-expanded={isOpen}
      >
        <TrailIcon 
          size={16} 
          className="transition-transform group-hover:scale-110"
        />
      </button>

      {isOpen && hasPortal && portalRef.current ? (
        createPortal(
          <div
            ref={drawerRef}
            className="fixed right-4 z-50 max-w-[calc(100vw-2rem)] overflow-hidden rounded-2xl border border-whitePurple-100/60 bg-white shadow-xl shadow-whitePurple-50/70 dark:border-whitePurple-200/30 dark:bg-gray-900 dark:shadow-purple-900/30"
            style={{
              width: 'var(--audit-trail-panel-width, min(32rem, calc(100vw - 2rem)))',
              top: drawerMetrics.top,
              height: drawerMetrics.height
            }}
          >
            <div className="relative flex h-full flex-col">
              <div className="flex h-full flex-col">
                <div className="flex items-center justify-between border-b border-whitePurple-100/50 px-6 py-4 dark:border-whitePurple-200/20">
                  <div>
                    <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">Execution Trail</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{visibleCount} event{visibleCount !== 1 ? 's' : ''}</p>
                  </div>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="rounded-md p-1 text-gray-400 hover:text-gray-600 dark:text-gray-400 dark:hover:text-gray-200"
                    aria-label="Close execution trail"
                  >
                    <XMarkIcon className="h-4 w-4" />
                  </button>
                </div>

                <div className="audit-trail-scroll no-scrollbar flex-1 px-6 py-6">
                  {isLoading ? (
                    <div className="flex items-center justify-center py-6 text-sm text-gray-500 dark:text-gray-400">
                      <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
                      Loading audit trail…
                    </div>
                  ) : error ? (
                    <div className={`py-4 text-center text-sm ${error.includes('available') ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-500 dark:text-red-400'}`}>
                      {error}
                    </div>
                  ) : visibleCount === 0 ? (
                    <div className="py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                      No audit trail data available
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {renderedTrailItems}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>,
          portalRef.current
        )
      ) : null}
    </div>
  );
};

export default AuditTrailButton;
