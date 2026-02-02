# Multi-stage build for Remix webapp (monorepo-aware)

# ---- Build Stage ----
FROM node:25-alpine AS builder

# Set working directory
WORKDIR /app

# Install dependencies for builds
RUN apk add --no-cache python3 make g++

# Use the Yarn version that comes with Node image or install specific version if needed
RUN yarn --version || npm install -g yarn@1.22.19 --force

# Copy root package files for workspace resolution
COPY package.json yarn.lock ./

# Copy packages directory (auth-core and auth-propelauth)
COPY packages/ ./packages/

# Copy webapp service
COPY services/webapp/ ./services/webapp/

# Install all dependencies (workspaces-aware)
RUN yarn install --frozen-lockfile --network-timeout 300000

# Build the auth packages first
RUN yarn workspace @chicory/auth-core build
RUN yarn workspace @chicory/auth-propelauth build

# Build the webapp
RUN yarn workspace webapp build

# ---- Runtime Stage ----
FROM node:25-alpine AS runtime

# Set working directory
WORKDIR /app

# Set environment variables
ENV NODE_ENV=production

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 remixuser \
    && chown -R remixuser:nodejs /app

# Use the Yarn version that comes with Node image or install specific version if needed
RUN yarn --version || npm install -g yarn@1.22.19 --force

# Copy necessary files for production install
COPY --from=builder --chown=remixuser:nodejs /app/package.json /app/yarn.lock ./
COPY --from=builder --chown=remixuser:nodejs /app/packages/ ./packages/
COPY --from=builder --chown=remixuser:nodejs /app/services/webapp/package.json ./services/webapp/

# Install only production dependencies
RUN yarn install --frozen-lockfile --production --network-timeout 300000

# Copy built application from builder stage
COPY --from=builder --chown=remixuser:nodejs /app/services/webapp/build ./services/webapp/build
COPY --from=builder --chown=remixuser:nodejs /app/services/webapp/public ./services/webapp/public

# Set workdir to webapp for running
WORKDIR /app/services/webapp

# Switch to non-root user
USER remixuser

# Expose port
EXPOSE 3000

# Set healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Start the server
CMD ["yarn", "start"]
