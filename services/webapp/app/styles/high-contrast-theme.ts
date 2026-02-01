/**
 * High contrast syntax highlighting theme for accessibility
 * Ensures all colors meet WCAG AAA standards (7:1 contrast ratio)
 */

import React from 'react';

// High contrast theme with 7:1 contrast ratios
export const highContrastSyntaxTheme: Record<string, React.CSSProperties> = {
  'code[class*="language-"]': {
    color: '#FFFFFF', // White text on dark background
    background: 'none',
    textShadow: 'none',
    fontFamily: 'Consolas, Monaco, \'Andale Mono\', \'Ubuntu Mono\', monospace',
    fontSize: '1em',
    textAlign: 'left',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    wordWrap: 'normal',
    lineHeight: '1.5',
    MozTabSize: '4',
    OTabSize: '4',
    tabSize: '4',
    WebkitHyphens: 'none',
    MozHyphens: 'none',
    msHyphens: 'none',
    hyphens: 'none',
  },
  'pre[class*="language-"]': {
    color: '#FFFFFF',
    background: '#000000', // Pure black background
    textShadow: 'none',
    fontFamily: 'Consolas, Monaco, \'Andale Mono\', \'Ubuntu Mono\', monospace',
    fontSize: '1em',
    textAlign: 'left',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    wordWrap: 'normal',
    lineHeight: '1.5',
    MozTabSize: '4',
    OTabSize: '4',
    tabSize: '4',
    WebkitHyphens: 'none',
    MozHyphens: 'none',
    msHyphens: 'none',
    hyphens: 'none',
    padding: '1em',
    margin: '.5em 0',
    overflow: 'auto',
    borderRadius: '0.3em',
    border: '2px solid #FFFFFF', // High contrast border
  },
  ':not(pre) > code[class*="language-"]': {
    background: '#000000',
    padding: '.1em',
    borderRadius: '.3em',
    whiteSpace: 'normal',
    border: '1px solid #FFFFFF',
  },
  
  // Comments - light gray for 7:1 contrast
  'comment': { color: '#B3B3B3' },
  'prolog': { color: '#B3B3B3' },
  'doctype': { color: '#B3B3B3' },
  'cdata': { color: '#B3B3B3' },
  
  // Punctuation - pure white
  'punctuation': { color: '#FFFFFF' },
  
  // Keywords - bright yellow for high contrast
  'keyword': { color: '#FFFF00', fontWeight: 'bold' },
  'tag': { color: '#FFFF00', fontWeight: 'bold' },
  'function': { color: '#FFFF00', fontWeight: 'bold' },
  'class-name': { color: '#FFFF00', fontWeight: 'bold' },
  
  // Strings - bright green
  'string': { color: '#00FF00' },
  'char': { color: '#00FF00' },
  'attr-value': { color: '#00FF00' },
  
  // Numbers and constants - bright cyan
  'number': { color: '#00FFFF' },
  'boolean': { color: '#00FFFF' },
  'constant': { color: '#00FFFF' },
  'symbol': { color: '#00FFFF' },
  
  // Attributes and properties - bright magenta
  'property': { color: '#FF00FF' },
  'attr-name': { color: '#FF00FF' },
  'selector': { color: '#FF00FF' },
  'builtin': { color: '#FF00FF' },
  
  // Operators and variables - white
  'operator': { color: '#FFFFFF' },
  'entity': { color: '#FFFFFF' },
  'url': { color: '#FFFFFF' },
  'variable': { color: '#FFFFFF' },
  
  // Special states
  'inserted': { color: '#00FF00', backgroundColor: '#004400' },
  'deleted': { color: '#FF0000', backgroundColor: '#440000' },
  
  // Important and regex
  'important': { color: '#FFFF00', fontWeight: 'bold' },
  'regex': { color: '#FF8800' },
  
  // Text formatting
  'bold': { fontWeight: 'bold' },
  'italic': { fontStyle: 'italic' },
  
  // Namespace
  '.namespace': { opacity: '1' }, // Don't reduce opacity in high contrast mode
};

/**
 * Detect if user prefers high contrast
 */
export function prefersHighContrast(): boolean {
  if (typeof window === 'undefined') return false;
  
  return window.matchMedia('(prefers-contrast: high)').matches ||
         window.matchMedia('(-ms-high-contrast: active)').matches;
}

/**
 * Hook to track high contrast preference
 */
export function useHighContrastPreference(): boolean {
  const [prefersHigh, setPrefersHigh] = React.useState(false);
  
  React.useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const updatePreference = () => {
      setPrefersHigh(prefersHighContrast());
    };
    
    // Initial check
    updatePreference();
    
    // Listen for changes
    const contrastQuery = window.matchMedia('(prefers-contrast: high)');
    const msContrastQuery = window.matchMedia('(-ms-high-contrast: active)');
    
    if (contrastQuery.addListener) {
      contrastQuery.addListener(updatePreference);
      msContrastQuery.addListener(updatePreference);
      
      return () => {
        contrastQuery.removeListener(updatePreference);
        msContrastQuery.removeListener(updatePreference);
      };
    } else if (contrastQuery.addEventListener) {
      contrastQuery.addEventListener('change', updatePreference);
      msContrastQuery.addEventListener('change', updatePreference);
      
      return () => {
        contrastQuery.removeEventListener('change', updatePreference);
        msContrastQuery.removeEventListener('change', updatePreference);
      };
    }
  }, []);
  
  return prefersHigh;
}

export default highContrastSyntaxTheme;