/**
 * Event bus for managing streaming events across components
 */

import { StreamEventType, StreamEventMap } from './eventTypes';

type EventCallback<T = any> = (payload: T) => void;

class StreamEventBus {
  private static instance: StreamEventBus;
  private listeners: Map<StreamEventType, Set<EventCallback>> = new Map();
  private debug = false; // Set to true for debugging

  private constructor() {
    // Private constructor for singleton
  }

  static getInstance(): StreamEventBus {
    if (!StreamEventBus.instance) {
      StreamEventBus.instance = new StreamEventBus();
    }
    return StreamEventBus.instance;
  }

  /**
   * Emit an event to all subscribers
   */
  emit<T extends StreamEventType>(event: T, payload: StreamEventMap[T]): void {
    if (this.debug) {
      console.log(`[EventBus] Emitting ${event}:`, payload);
    }

    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(payload);
        } catch (error) {
          console.error(`[EventBus] Error in ${event} handler:`, error);
        }
      });
    }
  }

  /**
   * Subscribe to an event
   * Returns an unsubscribe function
   */
  subscribe<T extends StreamEventType>(
    event: T,
    callback: EventCallback<StreamEventMap[T]>
  ): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }

    const callbacks = this.listeners.get(event)!;
    callbacks.add(callback);

    if (this.debug) {
      console.log(`[EventBus] Subscribed to ${event}, total listeners: ${callbacks.size}`);
    }

    // Return unsubscribe function
    return () => {
      callbacks.delete(callback);
      if (this.debug) {
        console.log(`[EventBus] Unsubscribed from ${event}, remaining listeners: ${callbacks.size}`);
      }
    };
  }

  /**
   * Subscribe to multiple events at once
   * Returns a function to unsubscribe from all
   */
  subscribeMultiple(
    subscriptions: Array<{
      event: StreamEventType;
      callback: EventCallback;
    }>
  ): () => void {
    const unsubscribers = subscriptions.map(({ event, callback }) =>
      this.subscribe(event, callback)
    );

    return () => {
      unsubscribers.forEach(unsub => unsub());
    };
  }

  /**
   * Clear all listeners for a specific event
   */
  clearEvent(event: StreamEventType): void {
    this.listeners.delete(event);
  }

  /**
   * Clear all listeners
   */
  clearAll(): void {
    this.listeners.clear();
  }

  /**
   * Enable/disable debug logging
   */
  setDebug(enabled: boolean): void {
    this.debug = enabled;
  }

  /**
   * Get the number of listeners for an event
   */
  getListenerCount(event: StreamEventType): number {
    return this.listeners.get(event)?.size || 0;
  }
}

export const streamEventBus = StreamEventBus.getInstance();