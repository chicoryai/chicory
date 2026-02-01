/**
 * Centralized markdown plugin configuration
 * Standardizes remark/rehype plugin usage across the application
 */

import remarkGfm from 'remark-gfm';
import type { MarkdownPlugin, MarkdownConfig } from '~/types/markdown';

/**
 * Default plugin configuration for standard markdown rendering
 */
export const defaultPlugins = {
  remark: [
    remarkGfm, // GitHub Flavored Markdown support
  ],
  rehype: [
    // Add rehype plugins here as needed
  ],
};

/**
 * Plugin configurations for different use cases
 */
export const pluginConfigs = {
  // Standard configuration for chat and task messages
  standard: {
    remark: [...defaultPlugins.remark],
    rehype: [...defaultPlugins.rehype],
  },
  
  // Minimal configuration for simple text
  minimal: {
    remark: [], // No plugins for simple rendering
    rehype: [],
  },
  
  // Enhanced configuration for advanced features (Phase 4)
  enhanced: {
    remark: [
      ...defaultPlugins.remark,
      // Future: remarkMath, remarkFootnotes, etc.
    ],
    rehype: [
      ...defaultPlugins.rehype,
      // Future: rehypeKatex, rehypeMermaid, etc.
    ],
  },
};

/**
 * Get plugin configuration by name
 */
export function getPluginConfig(configName: keyof typeof pluginConfigs = 'standard') {
  return pluginConfigs[configName];
}

/**
 * Create custom plugin configuration
 */
export function createPluginConfig(options: {
  includeGfm?: boolean;
  additionalRemarkPlugins?: any[];
  additionalRehypePlugins?: any[];
} = {}) {
  const {
    includeGfm = true,
    additionalRemarkPlugins = [],
    additionalRehypePlugins = [],
  } = options;

  return {
    remark: [
      ...(includeGfm ? [remarkGfm] : []),
      ...additionalRemarkPlugins,
    ],
    rehype: [
      ...additionalRehypePlugins,
    ],
  };
}

/**
 * Default markdown configuration
 * Used by MarkdownRenderer and other components
 */
export const defaultMarkdownConfig: MarkdownConfig = {
  plugins: [
    {
      name: 'remark-gfm',
      version: '4.0.1',
      remark: remarkGfm,
    },
  ],
  security: {
    allowHtml: false,
    maxContentLength: 100000, // 100KB limit
    sanitizeLinks: true,
  },
  performance: {
    enableCodeHighlighting: true,
    codeHighlightThreshold: 100, // lines
    enableVirtualization: false, // Phase 3 feature
  },
};

/**
 * Validate plugin configuration
 */
export function validatePluginConfig(config: Partial<MarkdownConfig>): MarkdownConfig {
  return {
    plugins: config.plugins || defaultMarkdownConfig.plugins,
    security: {
      ...defaultMarkdownConfig.security,
      ...config.security,
    },
    performance: {
      ...defaultMarkdownConfig.performance,
      ...config.performance,
    },
  };
}

/**
 * Plugin registry for dynamic loading (Phase 4 feature)
 */
export class MarkdownPluginRegistry {
  private plugins = new Map<string, MarkdownPlugin>();

  register(plugin: MarkdownPlugin) {
    this.plugins.set(plugin.name, plugin);
  }

  get(name: string): MarkdownPlugin | undefined {
    return this.plugins.get(name);
  }

  getAll(): MarkdownPlugin[] {
    return Array.from(this.plugins.values());
  }

  unregister(name: string): boolean {
    return this.plugins.delete(name);
  }
}

// Global plugin registry instance
export const pluginRegistry = new MarkdownPluginRegistry();

// Register default plugins
pluginRegistry.register({
  name: 'remark-gfm',
  version: '4.0.1',
  remark: remarkGfm,
});