import type { Collection, Db, ObjectId } from 'mongodb';
import { hashPassword, verifyPassword, generateApiKeyToken, getApiKeyDisplayParts } from '../utils/password';
import { generateApiKeyId, calculateExpirationDate, isExpired } from '../utils/token';
import type { CreateApiKeyParams, ApiKeyInfo, ApiKeyValidationResult } from '../types';

export interface ApiKeyDocument {
  _id?: ObjectId;
  apiKeyId: string;
  keyHash: string;
  keyPrefix: string;
  keySuffix: string;
  userId?: string;
  orgId?: string;
  resourceType?: 'agent' | 'gateway';
  resourceId?: string;
  metadata?: Record<string, unknown>;
  expiresAt?: Date;
  lastUsedAt?: Date;
  createdAt: Date;
}

export class ApiKeyModel {
  private collection: Collection<ApiKeyDocument>;

  constructor(db: Db) {
    this.collection = db.collection<ApiKeyDocument>('auth_api_keys');
  }

  async ensureIndexes(): Promise<void> {
    await this.collection.createIndex({ apiKeyId: 1 }, { unique: true });
    await this.collection.createIndex({ keyPrefix: 1 });
    await this.collection.createIndex({ userId: 1 });
    await this.collection.createIndex({ orgId: 1 });
    await this.collection.createIndex({ resourceId: 1 });
  }

  async create(params: CreateApiKeyParams): Promise<{ apiKeyId: string; apiKeyToken: string }> {
    const apiKeyToken = generateApiKeyToken();
    const { prefix, suffix } = getApiKeyDisplayParts(apiKeyToken);
    const keyHash = await hashPassword(apiKeyToken);

    const apiKey: ApiKeyDocument = {
      apiKeyId: generateApiKeyId(),
      keyHash,
      keyPrefix: prefix,
      keySuffix: suffix,
      userId: params.userId,
      orgId: params.orgId,
      resourceType: params.resourceType,
      resourceId: params.resourceId,
      metadata: {
        ...params.metadata,
        created_at: new Date().toISOString(),
      },
      expiresAt: calculateExpirationDate(params.expiresAtSeconds),
      createdAt: new Date(),
    };

    await this.collection.insertOne(apiKey);

    return {
      apiKeyId: apiKey.apiKeyId,
      apiKeyToken,
    };
  }

  async validate(apiKeyToken: string): Promise<ApiKeyValidationResult | null> {
    const { prefix } = getApiKeyDisplayParts(apiKeyToken);

    // Find all keys with matching prefix
    const candidates = await this.collection.find({ keyPrefix: prefix }).toArray();

    for (const candidate of candidates) {
      const isValid = await verifyPassword(apiKeyToken, candidate.keyHash);
      if (isValid) {
        // Check expiration
        if (isExpired(candidate.expiresAt)) {
          return null;
        }

        // Update last used
        await this.collection.updateOne(
          { apiKeyId: candidate.apiKeyId },
          { $set: { lastUsedAt: new Date() } }
        );

        return {
          user: candidate.userId ? { userId: candidate.userId } : undefined,
          org: candidate.orgId ? { orgId: candidate.orgId } : undefined,
          metadata: candidate.metadata,
        };
      }
    }

    return null;
  }

  async delete(apiKeyId: string): Promise<void> {
    await this.collection.deleteOne({ apiKeyId });
  }

  async findByUser(userId: string, pageSize: number = 100, pageNumber: number = 0): Promise<ApiKeyInfo[]> {
    const skip = pageNumber * pageSize;
    const keys = await this.collection
      .find({ userId })
      .skip(skip)
      .limit(pageSize)
      .toArray();

    return keys.map(this.toApiKeyInfo);
  }

  async findByOrg(orgId: string, pageSize: number = 100, pageNumber: number = 0): Promise<ApiKeyInfo[]> {
    const skip = pageNumber * pageSize;
    const keys = await this.collection
      .find({ orgId })
      .skip(skip)
      .limit(pageSize)
      .toArray();

    return keys.map(this.toApiKeyInfo);
  }

  async findByResource(resourceId: string): Promise<ApiKeyInfo | null> {
    const key = await this.collection.findOne({ resourceId });
    if (!key) return null;
    return this.toApiKeyInfo(key);
  }

  private toApiKeyInfo(doc: ApiKeyDocument): ApiKeyInfo {
    return {
      apiKeyId: doc.apiKeyId,
      keyPrefix: doc.keyPrefix,
      keySuffix: doc.keySuffix,
      orgId: doc.orgId,
      userId: doc.userId,
      resourceType: doc.resourceType,
      resourceId: doc.resourceId,
      metadata: doc.metadata,
      createdAt: doc.createdAt,
      expiresAt: doc.expiresAt,
      lastUsedAt: doc.lastUsedAt,
    };
  }
}
