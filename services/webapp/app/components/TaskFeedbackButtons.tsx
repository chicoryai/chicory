import { HandThumbUpIcon, HandThumbDownIcon } from '@heroicons/react/24/outline';
import { twMerge } from 'tailwind-merge';

interface TaskFeedbackButtonsProps {
  currentRating?: 'positive' | 'negative' | null;
  onSelect: (rating: 'positive' | 'negative') => void;
}

export function TaskFeedbackButtons({ currentRating = null, onSelect }: TaskFeedbackButtonsProps) {
  const baseClass = 'inline-flex h-9 w-9 items-center justify-center rounded-full bg-transparent text-slate-400 transition hover:text-purple-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 dark:text-slate-500 dark:hover:text-purple-300';

  return (
    <div className="flex flex-col items-end gap-2">
      <button
        type="button"
        onClick={() => onSelect('positive')}
        className={twMerge(baseClass, currentRating === 'positive' ? 'text-purple-600 dark:text-purple-200' : '')}
        aria-pressed={currentRating === 'positive'}
      >
        <HandThumbUpIcon className="h-5 w-5" aria-hidden="true" />
        <span className="sr-only">Thumbs up</span>
      </button>
      <button
        type="button"
        onClick={() => onSelect('negative')}
        className={twMerge(baseClass, currentRating === 'negative' ? 'text-purple-600 dark:text-purple-200' : '')}
        aria-pressed={currentRating === 'negative'}
      >
        <HandThumbDownIcon className="h-5 w-5" aria-hidden="true" />
        <span className="sr-only">Thumbs down</span>
      </button>
    </div>
  );
}

export default TaskFeedbackButtons;
