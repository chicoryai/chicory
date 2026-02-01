import type { Collection, Db, ObjectId } from 'mongodb';
import { hashPassword, verifyPassword } from '../utils/password';
import { generateUserId } from '../utils/token';

export interface UserDocument {
  _id?: ObjectId;
  userId: string;
  email: string;
  passwordHash: string;
  firstName?: string;
  lastName?: string;
  username?: string;
  pictureUrl?: string;
  emailVerified: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface CreateUserParams {
  email: string;
  password: string;
  firstName?: string;
  lastName?: string;
}

export class UserModel {
  private collection: Collection<UserDocument>;

  constructor(db: Db) {
    this.collection = db.collection<UserDocument>('auth_users');
  }

  async ensureIndexes(): Promise<void> {
    await this.collection.createIndex({ email: 1 }, { unique: true });
    await this.collection.createIndex({ userId: 1 }, { unique: true });
  }

  async create(params: CreateUserParams): Promise<UserDocument> {
    const now = new Date();
    const passwordHash = await hashPassword(params.password);

    const user: UserDocument = {
      userId: generateUserId(),
      email: params.email.toLowerCase().trim(),
      passwordHash,
      firstName: params.firstName,
      lastName: params.lastName,
      emailVerified: false,
      createdAt: now,
      updatedAt: now,
    };

    await this.collection.insertOne(user);
    return user;
  }

  async findByEmail(email: string): Promise<UserDocument | null> {
    return this.collection.findOne({ email: email.toLowerCase().trim() });
  }

  async findById(userId: string): Promise<UserDocument | null> {
    return this.collection.findOne({ userId });
  }

  async verifyCredentials(email: string, password: string): Promise<UserDocument | null> {
    const user = await this.findByEmail(email);
    if (!user) return null;

    const isValid = await verifyPassword(password, user.passwordHash);
    if (!isValid) return null;

    return user;
  }

  async updateMetadata(
    userId: string,
    metadata: {
      firstName?: string;
      lastName?: string;
      pictureUrl?: string;
      username?: string;
    }
  ): Promise<void> {
    const update: Partial<UserDocument> = {
      updatedAt: new Date(),
    };

    if (metadata.firstName !== undefined) update.firstName = metadata.firstName;
    if (metadata.lastName !== undefined) update.lastName = metadata.lastName;
    if (metadata.pictureUrl !== undefined) update.pictureUrl = metadata.pictureUrl;
    if (metadata.username !== undefined) update.username = metadata.username;

    await this.collection.updateOne({ userId }, { $set: update });
  }

  async updatePassword(userId: string, newPassword: string): Promise<void> {
    const passwordHash = await hashPassword(newPassword);
    await this.collection.updateOne(
      { userId },
      { $set: { passwordHash, updatedAt: new Date() } }
    );
  }
}
