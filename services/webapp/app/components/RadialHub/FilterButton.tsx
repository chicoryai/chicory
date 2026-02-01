import { motion } from 'framer-motion';

interface FilterButtonProps {
  label: string;
  count: number;
  isActive: boolean;
  onClick: () => void;
}

export function FilterButton({ 
  label, 
  count, 
  isActive, 
  onClick 
}: FilterButtonProps) {
  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      className={`
        inline-flex items-center px-4 py-2 rounded-full text-sm font-medium
        transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500
        dark:focus:ring-offset-gray-900 shadow-sm
        ${isActive 
          ? 'bg-lime-100 text-lime-800 dark:bg-lime-900 dark:text-lime-200 shadow-md' 
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
        }
      `}
      aria-pressed={isActive}
    >
      {label}
      <span className={`
        ml-2 px-2 py-0.5 text-xs rounded-full font-bold
        ${isActive 
          ? 'bg-lime-200 text-lime-800 dark:bg-lime-800 dark:text-lime-200' 
          : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
        }
      `}>
        {count}
      </span>
    </motion.button>
  );
}
