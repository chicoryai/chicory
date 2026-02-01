/**
 * SSE Connection Pool Manager
 * Manages Server-Sent Events connections with a maximum limit
 */

class SSEConnectionPool {
  private activeConnections = new Map<string, EventSource>();
  private readonly MAX_CONNECTIONS = 5;

  /**
   * Check if a new connection can be established
   */
  canConnect(): boolean {
    return this.activeConnections.size < this.MAX_CONNECTIONS;
  }

  /**
   * Add a new connection to the pool
   * Returns false if the pool is at capacity
   */
  addConnection(id: string, eventSource: EventSource): boolean {
    if (!this.canConnect()) {
      console.warn(`[ConnectionPool] Cannot add connection ${id}: Pool at capacity (${this.MAX_CONNECTIONS})`);
      return false;
    }

    this.activeConnections.set(id, eventSource);
    console.log(`[ConnectionPool] Added connection ${id}. Active: ${this.activeConnections.size}/${this.MAX_CONNECTIONS}`);
    return true;
  }

  /**
   * Remove and close a connection from the pool
   */
  removeConnection(id: string): void {
    const eventSource = this.activeConnections.get(id);
    if (eventSource) {
      eventSource.close();
      this.activeConnections.delete(id);
      console.log(`[ConnectionPool] Removed connection ${id}. Active: ${this.activeConnections.size}/${this.MAX_CONNECTIONS}`);
    }
  }

  /**
   * Get the number of active connections
   */
  getActiveCount(): number {
    return this.activeConnections.size;
  }

  /**
   * Get the maximum number of allowed connections
   */
  getMaxConnections(): number {
    return this.MAX_CONNECTIONS;
  }

  /**
   * Close all active connections and clear the pool
   */
  closeAll(): void {
    console.log(`[ConnectionPool] Closing all ${this.activeConnections.size} connections`);
    this.activeConnections.forEach((eventSource, id) => {
      console.log(`[ConnectionPool] Closing connection ${id}`);
      eventSource.close();
    });
    this.activeConnections.clear();
  }

  /**
   * Check if a specific connection is active
   */
  hasConnection(id: string): boolean {
    return this.activeConnections.has(id);
  }
}

// Export singleton instance
export const sseConnectionPool = new SSEConnectionPool();
