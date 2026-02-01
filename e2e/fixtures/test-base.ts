import { test as base, expect, Page } from '@playwright/test';
import { BasePage } from '../pages/base.page';
import { LoginPage } from '../pages/login.page';
import { IntegrationsPage } from '../pages/integrations.page';
import { AgentsPage } from '../pages/agents.page';
import { AgentPlaygroundPage } from '../pages/agent-playground.page';
import { AgentDeployPage } from '../pages/agent-deploy.page';
import { AgentManagePage } from '../pages/agent-manage.page';

/**
 * Extended test fixture with page objects
 */
export const test = base.extend<{
  // Page objects
  basePage: BasePage;
  loginPage: LoginPage;
  integrationsPage: IntegrationsPage;
  agentsPage: AgentsPage;
  playgroundPage: AgentPlaygroundPage;
  deployPage: AgentDeployPage;
  managePage: AgentManagePage;
}>({
  basePage: async ({ page }, use) => {
    await use(new BasePage(page));
  },

  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },

  integrationsPage: async ({ page }, use) => {
    await use(new IntegrationsPage(page));
  },

  agentsPage: async ({ page }, use) => {
    await use(new AgentsPage(page));
  },

  playgroundPage: async ({ page }, use) => {
    await use(new AgentPlaygroundPage(page));
  },

  deployPage: async ({ page }, use) => {
    await use(new AgentDeployPage(page));
  },

  managePage: async ({ page }, use) => {
    await use(new AgentManagePage(page));
  },
});

export { expect };
