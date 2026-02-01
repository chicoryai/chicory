import { createClient } from '@supabase/supabase-js';

// Ensure environment variables are set
if (!process.env.SUPABASE_URL || !process.env.SUPABASE_ANON_KEY) {
  console.error('Missing Supabase environment variables');
}

// Create a single supabase client for interacting with your database
export const supabase = createClient(
  process.env.SUPABASE_URL || '',
  process.env.SUPABASE_ANON_KEY || ''
);

// Project-related types
export interface Project {
  id: string;
  propelauth_org_id: string;
  created_by_user_id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectMember {
  id: string;
  project_id: string;
  propelauth_user_id: string;
  role: string;
  created_at: string;
}

// Create a new project
export async function createProject({
  name,
  description,
  propelauth_org_id,
  created_by_user_id
}: {
  name: string;
  description?: string;
  propelauth_org_id: string;
  created_by_user_id: string;
}): Promise<Project> {
  try {
    console.log('Creating project:', { name, propelauth_org_id, created_by_user_id });
    
    const { data, error } = await supabase
      .from('projects')
      .insert({
        name,
        description,
        propelauth_org_id,
        created_by_user_id
      })
      .select()
      .single();
    
    if (error) {
      console.error('Error creating project:', error);
      throw new Error(`Failed to create project: ${error.message}`);
    }
    
    console.log('Project created successfully:', data);
    
    // Add the creator as a project member with 'admin' role
    await addProjectMember({
      project_id: data.id,
      propelauth_user_id: created_by_user_id,
      role: 'admin'
    });
    
    return data;
  } catch (error: any) {
    console.error('Error in createProject:', error);
    throw error;
  }
}

// Add a member to a project
export async function addProjectMember({
  project_id,
  propelauth_user_id,
  role
}: {
  project_id: string;
  propelauth_user_id: string;
  role: string;
}): Promise<ProjectMember> {
  try {
    console.log('Adding project member:', { project_id, propelauth_user_id, role });
    
    const { data, error } = await supabase
      .from('project_members')
      .insert({
        project_id,
        propelauth_user_id,
        role
      })
      .select()
      .single();
    
    if (error) {
      console.error('Error adding project member:', error);
      throw new Error(`Failed to add project member: ${error.message}`);
    }
    
    console.log('Project member added successfully:', data);
    return data;
  } catch (error: any) {
    console.error('Error in addProjectMember:', error);
    throw error;
  }
}

// Get projects for an organization
export async function getProjectsByOrgId(propelauth_org_id: string): Promise<Project[]> {
  try {
    const { data, error } = await supabase
      .from('projects')
      .select('*')
      .eq('propelauth_org_id', propelauth_org_id)
      .order('created_at', { ascending: false });
    
    if (error) {
      console.error('Error fetching projects:', error);
      throw new Error(`Failed to fetch projects: ${error.message}`);
    }
    
    return data || [];
  } catch (error: any) {
    console.error('Error in getProjectsByOrgId:', error);
    throw error;
  }
}

// Get a project by ID
export async function getProjectById(id: string): Promise<Project | null> {
  try {
    const { data, error } = await supabase
      .from('projects')
      .select('*')
      .eq('id', id)
      .single();
    
    if (error) {
      if (error.code === 'PGRST116') {
        // PGRST116 is the error code for "no rows returned"
        return null;
      }
      console.error('Error fetching project:', error);
      throw new Error(`Failed to fetch project: ${error.message}`);
    }
    
    return data;
  } catch (error: any) {
    console.error('Error in getProjectById:', error);
    throw error;
  }
}

// Get project members
export async function getProjectMembers(project_id: string): Promise<ProjectMember[]> {
  try {
    const { data, error } = await supabase
      .from('project_members')
      .select('*')
      .eq('project_id', project_id);
    
    if (error) {
      console.error('Error fetching project members:', error);
      throw new Error(`Failed to fetch project members: ${error.message}`);
    }
    
    return data || [];
  } catch (error: any) {
    console.error('Error in getProjectMembers:', error);
    throw error;
  }
}

// Chat Message related types
export interface ChatMessage {
  id: string;
  project_id: string;
  content: string;
  role: 'user' | 'assistant';
  created_by_user_id: string;
  created_at: string;
}

// Chat Thread related types
export interface ChatThread {
  id: string;
  project_id: string;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

// Create a new chat thread
export async function createChatThread({
  project_id,
  created_by_user_id
}: {
  project_id: string;
  created_by_user_id: string;
}): Promise<ChatThread> {
  try {
    console.log('Creating chat thread:', { project_id });
    
    const { data, error } = await supabase
      .from('chat_threads')
      .insert({
        project_id,
        created_by_user_id
      })
      .select()
      .single();
    
    if (error) {
      console.error('Error creating chat thread:', error);
      throw error;
    }
    
    return data as ChatThread;
  } catch (error) {
    console.error('Error creating chat thread:', error);
    throw error;
  }
}

// Get chat threads for a project
export async function getChatThreadsByProjectId(project_id: string): Promise<ChatThread[]> {
  try {
    console.log('Getting chat threads for project:', project_id);
    
    const { data, error } = await supabase
      .from('chat_threads')
      .select('*')
      .eq('project_id', project_id)
      .order('created_at', { ascending: false });
    
    if (error) {
      console.error('Error getting chat threads:', error);
      throw error;
    }
    
    return data as ChatThread[];
  } catch (error) {
    console.error('Error getting chat threads:', error);
    throw error;
  }
}

// Add a message to a project chat
export async function addChatMessage({
  project_id,
  content,
  role,
  created_by_user_id
}: {
  project_id: string;
  content: string;
  role: 'user' | 'assistant';
  created_by_user_id: string;
}): Promise<ChatMessage> {
  try {
    console.log('Adding chat message:', { project_id, role });
    
    const { data, error } = await supabase
      .from('chat_messages')
      .insert({
        project_id,
        content,
        role,
        created_by_user_id
      })
      .select()
      .single();
    
    if (error) {
      console.error('Error adding chat message:', error);
      throw new Error(`Failed to add chat message: ${error.message}`);
    }
    
    console.log('Chat message added successfully:', data);
    return data;
  } catch (error: any) {
    console.error('Error in addChatMessage:', error);
    throw error;
  }
}

// Get messages for a project
export async function getChatMessagesByProjectId(project_id: string): Promise<ChatMessage[]> {
  try {
    const { data, error } = await supabase
      .from('chat_messages')
      .select('*')
      .eq('project_id', project_id)
      .order('created_at', { ascending: true });
    
    if (error) {
      console.error('Error fetching chat messages:', error);
      throw new Error(`Failed to fetch chat messages: ${error.message}`);
    }
    
    return data || [];
  } catch (error: any) {
    console.error('Error in getChatMessagesByProjectId:', error);
    throw error;
  }
}
