import React from 'react';
import { BaseComponentProps } from '~/types/integrations';

interface ContentSectionProps extends BaseComponentProps {
  title?: string;
  description?: string;
  children: React.ReactNode;
  headerAction?: React.ReactNode;
  variant?: 'default' | 'card' | 'minimal';
  spacing?: 'tight' | 'normal' | 'loose';
}

/**
 * Reusable content section component
 * Provides consistent styling and spacing for content areas
 */
export default function ContentSection({
  title,
  description,
  children,
  headerAction,
  variant = 'default',
  spacing = 'normal',
  className = ""
}: ContentSectionProps) {
  const getVariantClasses = () => {
    switch (variant) {
      case 'card':
        return 'bg-transparent dark:bg-gray-900 rounded-xl dark:border-gray-800 transition-shadow duration-200';
      case 'minimal':
        return '';
      default:
        return 'bg-transparent dark:bg-gray-900 rounded-xl dark:border-gray-800';
    }
  };

  const getSpacingClasses = () => {
    switch (spacing) {
      case 'tight':
        return 'p-4';
      case 'loose':
        return 'p-8';
      default:
        return 'p-6';
    }
  };

  const getHeaderSpacing = () => {
    switch (spacing) {
      case 'tight':
        return 'px-4 pt-4 pb-3';
      case 'loose':
        return 'px-8 pt-8 pb-6';
      default:
        return 'px-6 pt-6 pb-4';
    }
  };

  const getContentSpacing = () => {
    switch (spacing) {
      case 'tight':
        return 'px-4 pb-4';
      case 'loose':
        return 'px-8 pb-8';
      default:
        return 'px-6 pb-6';
    }
  };

  const containerClasses = `${getVariantClasses()} ${className}`;

  return (
    <div className={containerClasses}>
      {/* Header */}
      {(title || description || headerAction) && (
        <div className={`${variant === 'minimal' ? 'mb-8' : `${getHeaderSpacing()} dark:border-gray-800`}`}>
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              {title && (
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white tracking-tight">
                  {title}
                </h2>
              )}
              {description && (
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                  {description}
                </p>
              )}
            </div>
            {headerAction && (
              <div className="flex-shrink-0 ml-6">
                {headerAction}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Content */}
      <div className={variant === 'minimal' ? '' : getContentSpacing()}>
        {children}
      </div>
    </div>
  );
} 