import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { useFetcher } from '@remix-run/react';
import { twMerge } from 'tailwind-merge';
import { HandThumbDownIcon, HandThumbUpIcon } from '@heroicons/react/24/outline';
import { Modal } from '~/components/ui/Modal';

export type TaskFeedbackEntry = {
  rating?: 'positive' | 'negative';
  feedback?: string | null;
  tags?: string[];
};

interface TaskFeedbackModalProps {
  isOpen: boolean;
  taskId: string;
  agentId: string;
  projectId: string;
  defaultRating: 'positive' | 'negative';
  onClose: () => void;
  onSubmitted?: (entry: TaskFeedbackEntry) => void;
  existingFeedback?: TaskFeedbackEntry | null;
}

interface FeedbackFetcherData {
  success?: boolean;
  error?: string;
}

const ratingCopy: Record<'positive' | 'negative', { title: string; description: string }> = {
  positive: {
    title: 'Positive feedback',
    description: 'Let us know what worked well.'
  },
  negative: {
    title: 'Needs work',
    description: 'Share what could be improved.'
  }
};

export function TaskFeedbackModal({
  isOpen,
  taskId,
  agentId,
  projectId,
  defaultRating,
  onClose,
  onSubmitted,
  existingFeedback
}: TaskFeedbackModalProps) {
  const fetcher = useFetcher<FeedbackFetcherData>();
  const isSubmitting = fetcher.state !== 'idle';
  const hasExisting = Boolean(existingFeedback);

  const [rating, setRating] = useState<'positive' | 'negative'>(defaultRating);
  const [comment, setComment] = useState('');
  const [status, setStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    if (hasExisting) {
      setRating(existingFeedback?.rating === 'negative' ? 'negative' : 'positive');
      setComment(existingFeedback?.feedback ?? '');
    } else {
      setRating(defaultRating);
      setComment('');
    }
    setStatus(null);
  }, [isOpen, hasExisting, existingFeedback?.rating, existingFeedback?.feedback, defaultRating]);

  useEffect(() => {
    if (!fetcher.data || fetcher.state !== 'idle') {
      return;
    }

    if (fetcher.data.success) {
      setStatus({ type: 'success', message: 'Feedback submitted. Thank you!' });
      if (onSubmitted) {
        onSubmitted({ rating, feedback: comment.trim(), tags: [] });
      }
    } else if (fetcher.data.error) {
      setStatus({ type: 'error', message: fetcher.data.error });
    }
  }, [fetcher.data, fetcher.state, onSubmitted]);

  const handleSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (hasExisting) {
        return;
      }

      const formData = new FormData(event.currentTarget);
      formData.set('rating', rating);
      formData.set('feedback', comment.trim());
      formData.delete('tags');
      formData.set('projectId', projectId);

      fetcher.submit(formData, {
        method: 'post',
        action: '/api/task-feedback'
      });
    },
    [comment, fetcher, hasExisting, projectId, rating]
  );

  const modalTitle = hasExisting
    ? 'Task feedback'
    : ratingCopy[rating].title;

  const modalBodyDescription = useMemo(() => {
    if (hasExisting) {
      return existingFeedback?.rating === 'negative'
        ? 'This response was previously marked as needing work.'
        : 'This response already has positive feedback.';
    }
    return ratingCopy[rating].description;
  }, [existingFeedback?.rating, hasExisting, rating]);

  const ratingButtonClass = (target: 'positive' | 'negative') =>
    twMerge(
      'inline-flex h-10 w-10 items-center justify-center rounded-full bg-transparent text-slate-400 transition hover:text-purple-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 dark:text-slate-500 dark:hover:text-purple-300',
      rating === target ? 'text-purple-600 dark:text-purple-200' : ''
    );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={modalTitle}
      panelClassName="w-full max-w-lg"
    >
      <div className="space-y-4 max-h-[40vh] overflow-y-auto pr-1">
        <p className="text-sm text-slate-600 dark:text-slate-300">{modalBodyDescription}</p>

        <fetcher.Form
          method="post"
          action="/api/task-feedback"
          onSubmit={handleSubmit}
          className="space-y-4"
        >
          <input type="hidden" name="taskId" value={taskId} />
          <input type="hidden" name="agentId" value={agentId} />
          <input type="hidden" name="projectId" value={projectId} />

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                setRating('positive');
                setStatus(current => (current?.type === 'error' ? null : current));
              }}
              className={ratingButtonClass('positive')}
              disabled={hasExisting}
            >
              <HandThumbUpIcon className="h-5 w-5" aria-hidden="true" />
              <span className="sr-only">Positive</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setRating('negative');
                setStatus(current => (current?.type === 'error' ? null : current));
              }}
              className={ratingButtonClass('negative')}
              disabled={hasExisting}
            >
              <HandThumbDownIcon className="h-5 w-5" aria-hidden="true" />
              <span className="sr-only">Needs work</span>
            </button>
            {hasExisting ? (
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {existingFeedback?.rating === 'negative' ? 'Needs work' : 'Positive'}
              </span>
            ) : null}
          </div>

          {status && (
            <div
              className={twMerge(
                'rounded-lg border px-3 py-2 text-sm',
                status.type === 'success'
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200'
                  : 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200'
              )}
            >
              {status.message}
            </div>
          )}

          <div>
            <label
              htmlFor={`feedback-notes-${taskId}`}
              className="block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
            >
              Additional notes
            </label>
            <textarea
              id={`feedback-notes-${taskId}`}
              name="feedback"
              rows={4}
              value={comment}
              onChange={event => {
                setComment(event.target.value);
                setStatus(current => (current?.type === 'error' ? null : current));
              }}
              disabled={hasExisting}
              placeholder={hasExisting ? 'Feedback already submitted.' : 'Share any context that will help us improve.'}
              className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-200 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400 dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-100 dark:focus:border-purple-400 dark:focus:ring-purple-700/30 disabled:dark:bg-slate-900/40 disabled:dark:text-slate-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="text-sm font-medium text-slate-500 transition-colors hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            >
              Close
            </button>
            {!hasExisting ? (
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isSubmitting ? 'Submitting…' : 'Submit feedback'}
              </button>
            ) : null}
          </div>
        </fetcher.Form>
      </div>
    </Modal>
  );
}

export default TaskFeedbackModal;
