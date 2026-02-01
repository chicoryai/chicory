import type { Collection, Db, ObjectId } from 'mongodb';
import { generateOrgId } from '../utils/token';
import { getPermissionsForRole } from '../types';

export interface OrganizationDocument {
  _id?: ObjectId;
  orgId: string;
  name: string;
  metadata?: Record<string, unknown>;
  createdAt: Date;
  updatedAt: Date;
}

export interface OrgMembershipDocument {
  _id?: ObjectId;
  userId: string;
  orgId: string;
  role: 'Owner' | 'Admin' | 'Member';
  permissions: string[];
  joinedAt: Date;
}

export class OrganizationModel {
  private orgsCollection: Collection<OrganizationDocument>;
  private membershipsCollection: Collection<OrgMembershipDocument>;

  constructor(db: Db) {
    this.orgsCollection = db.collection<OrganizationDocument>('auth_organizations');
    this.membershipsCollection = db.collection<OrgMembershipDocument>('auth_org_memberships');
  }

  async ensureIndexes(): Promise<void> {
    await this.orgsCollection.createIndex({ orgId: 1 }, { unique: true });
    await this.membershipsCollection.createIndex({ userId: 1, orgId: 1 }, { unique: true });
    await this.membershipsCollection.createIndex({ orgId: 1 });
    await this.membershipsCollection.createIndex({ userId: 1 });
  }

  async create(name: string, creatorUserId: string): Promise<OrganizationDocument> {
    const now = new Date();
    const org: OrganizationDocument = {
      orgId: generateOrgId(),
      name,
      createdAt: now,
      updatedAt: now,
    };

    await this.orgsCollection.insertOne(org);

    // Add creator as Owner
    await this.addMember(creatorUserId, org.orgId, 'Owner');

    return org;
  }

  async findById(orgId: string): Promise<OrganizationDocument | null> {
    return this.orgsCollection.findOne({ orgId });
  }

  async addMember(
    userId: string,
    orgId: string,
    role: 'Owner' | 'Admin' | 'Member' = 'Member'
  ): Promise<void> {
    const membership: OrgMembershipDocument = {
      userId,
      orgId,
      role,
      permissions: getPermissionsForRole(role),
      joinedAt: new Date(),
    };

    await this.membershipsCollection.updateOne(
      { userId, orgId },
      { $set: membership },
      { upsert: true }
    );
  }

  async removeMember(userId: string, orgId: string): Promise<void> {
    await this.membershipsCollection.deleteOne({ userId, orgId });
  }

  async changeRole(
    userId: string,
    orgId: string,
    newRole: 'Owner' | 'Admin' | 'Member'
  ): Promise<void> {
    await this.membershipsCollection.updateOne(
      { userId, orgId },
      {
        $set: {
          role: newRole,
          permissions: getPermissionsForRole(newRole),
        },
      }
    );
  }

  async getMembership(userId: string, orgId: string): Promise<OrgMembershipDocument | null> {
    return this.membershipsCollection.findOne({ userId, orgId });
  }

  async getUserMemberships(userId: string): Promise<OrgMembershipDocument[]> {
    return this.membershipsCollection.find({ userId }).toArray();
  }

  async getOrgMembers(
    orgId: string,
    pageSize: number = 100,
    pageNumber: number = 0
  ): Promise<{ members: OrgMembershipDocument[]; total: number }> {
    const skip = pageNumber * pageSize;
    const [members, total] = await Promise.all([
      this.membershipsCollection.find({ orgId }).skip(skip).limit(pageSize).toArray(),
      this.membershipsCollection.countDocuments({ orgId }),
    ]);
    return { members, total };
  }
}
