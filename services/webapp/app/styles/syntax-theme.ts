/**
 * Custom syntax highlighting theme that uses the webapp's design system colors
 * Replaces hardcoded 'oneDark' theme with consistent theming
 */

// Using Record<string, any> since PrismTheme types are not properly exported
type PrismTheme = Record<string, React.CSSProperties>;

// Import design system colors from Tailwind config
// These should match the purple/lime theme defined in tailwind.config.ts
export const customSyntaxTheme: PrismTheme = {
  'code[class*="language-"]': {
    color: '#F5F7F9', // text-dark from design system
    background: 'none',
    textShadow: '0 1px rgba(0, 0, 0, 0.3)',
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
    color: '#F5F7F9', // text-dark
    background: '#111827', // gray-900 for dark background
    textShadow: '0 1px rgba(0, 0, 0, 0.3)',
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
  },
  ':not(pre) > code[class*="language-"]': {
    background: '#111827',
    padding: '.1em',
    borderRadius: '.3em',
    whiteSpace: 'normal',
  },
  'comment': {
    color: '#9CA3AF', // gray-400 for better contrast (4.5:1 ratio)
  },
  'prolog': {
    color: '#9CA3AF',
  },
  'doctype': {
    color: '#9CA3AF',
  },
  'cdata': {
    color: '#9CA3AF',
  },
  'punctuation': {
    color: '#E5E7EB', // gray-200 for punctuation (better contrast)
  },
  '.namespace': {
    opacity: '.7',
  },
  'property': {
    color: '#BEF264', // lime.300 - better contrast for accessibility
  },
  'tag': {
    color: '#A78BFA', // purple.300 - better contrast than purple.400
  },
  'constant': {
    color: '#BEF264',
  },
  'symbol': {
    color: '#BEF264',
  },
  'deleted': {
    color: '#F87171', // red-400 for better contrast
  },
  'boolean': {
    color: '#BEF264',
  },
  'number': {
    color: '#BEF264',
  },
  'selector': {
    color: '#34D399', // green-400 for better contrast
  },
  'attr-name': {
    color: '#34D399',
  },
  'string': {
    color: '#34D399', // green for strings with better contrast
  },
  'char': {
    color: '#34D399',
  },
  'builtin': {
    color: '#34D399',
  },
  'inserted': {
    color: '#34D399',
  },
  'operator': {
    color: '#D1D5DB', // gray-300 for operators
  },
  'entity': {
    color: '#D1D5DB',
    cursor: 'help',
  },
  'url': {
    color: '#D1D5DB',
  },
  '.language-css .token.string': {
    color: '#D1D5DB',
  },
  '.style .token.string': {
    color: '#D1D5DB',
  },
  'variable': {
    color: '#D1D5DB',
  },
  'atrule': {
    color: '#6C5CE7', // purple.400 for at-rules
  },
  'attr-value': {
    color: '#6C5CE7',
  },
  'function': {
    color: '#6C5CE7', // purple for functions
  },
  'class-name': {
    color: '#F59E0B', // yellow-500 for class names
  },
  'keyword': {
    color: '#6C5CE7', // purple.400 for keywords
  },
  'regex': {
    color: '#F59E0B', // yellow for regex
  },
  'important': {
    color: '#F59E0B',
    fontWeight: 'bold',
  },
  'bold': {
    fontWeight: 'bold',
  },
  'italic': {
    fontStyle: 'italic',
  },
};

/**
 * Light theme variant for light mode
 */
export const customSyntaxThemeLight: PrismTheme = {
  ...customSyntaxTheme,
  'code[class*="language-"]': {
    ...customSyntaxTheme['code[class*="language-"]'],
    color: '#111827', // text-light for light mode
  },
  'pre[class*="language-"]': {
    ...customSyntaxTheme['pre[class*="language-"]'],
    color: '#111827',
    background: '#F9FAFB', // gray-50 for light background
  },
  ':not(pre) > code[class*="language-"]': {
    ...customSyntaxTheme[':not(pre) > code[class*="language-"]'],
    background: '#F9FAFB',
  },
};