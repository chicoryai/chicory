import type { Collection, Db, ObjectId } from 'mongodb';
import { generateSessionId } from '../utils/token';

export interface SessionDocument {
  _id?: ObjectId;
  sessionId: string;
  userId: string;
  expiresAt: Date;
  createdAt: Date;
  userAgent?: string;
  ipAddress?: string;
}

const DEFAULT_SESSION_MAX_AGE = 7 * 24 * 60 * 60; // 7 days in seconds

export class SessionModel {
  private collection: Collection<SessionDocument>;
  private maxAge: number;

  constructor(db: Db, maxAge: number = DEFAULT_SESSION_MAX_AGE) {
    this.collection = db.collection<SessionDocument>('auth_sessions');
    this.maxAge = maxAge;
  }

  async ensureIndexes(): Promise<void> {
    await this.collection.createIndex({ sessionId: 1 }, { unique: true });
    await this.collection.createIndex({ userId: 1 });
    await this.collection.createIndex({ expiresAt: 1 }, { expireAfterSeconds: 0 });
  }

  async create(
    userId: string,
    options?: { userAgent?: string; ipAddress?: string }
  ): Promise<SessionDocument> {
    const now = new Date();
    const session: SessionDocument = {
      sessionId: generateSessionId(),
      userId,
      expiresAt: new Date(now.getTime() + this.maxAge * 1000),
      createdAt: now,
      userAgent: options?.userAgent,
      ipAddress: options?.ipAddress,
    };

    await this.collection.insertOne(session);
    return session;
  }

  async findById(sessionId: string): Promise<SessionDocument | null> {
    const session = await this.collection.findOne({ sessionId });
    if (!session) return null;

    // Check if expired
    if (new Date() > session.expiresAt) {
      await this.delete(sessionId);
      return null;
    }

    return session;
  }

  async delete(sessionId: string): Promise<void> {
    await this.collection.deleteOne({ sessionId });
  }

  async deleteAllForUser(userId: string): Promise<void> {
    await this.collection.deleteMany({ userId });
  }

  async refresh(sessionId: string): Promise<SessionDocument | null> {
    const now = new Date();
    const result = await this.collection.findOneAndUpdate(
      { sessionId },
      { $set: { expiresAt: new Date(now.getTime() + this.maxAge * 1000) } },
      { returnDocument: 'after' }
    );
    return result;
  }

  async cleanExpired(): Promise<number> {
    const result = await this.collection.deleteMany({
      expiresAt: { $lt: new Date() },
    });
    return result.deletedCount;
  }
}
