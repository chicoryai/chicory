# Multi-stage build for Remix webapp

# ---- Build Stage ----
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Install dependencies for builds
RUN apk add --no-cache python3 make g++

# Use the Yarn version that comes with Node image or install specific version if needed
RUN yarn --version || npm install -g yarn@1.22.19 --force

# Copy package files and install dependencies
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile --network-timeout 300000

# Copy application code
COPY . .

# Build the application
RUN yarn build

# ---- Runtime Stage ----
FROM node:20-alpine AS runtime

# Set working directory
WORKDIR /app

# Set environment variables
ENV NODE_ENV=production

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 remixuser \
    && chown -R remixuser:nodejs /app

# Install only production dependencies
COPY --from=builder --chown=remixuser:nodejs /app/package.json /app/yarn.lock ./

# Use the Yarn version that comes with Node image or install specific version if needed
RUN yarn --version || npm install -g yarn@1.22.19 --force

# Install only production dependencies
RUN yarn install --frozen-lockfile --production --network-timeout 300000

# Copy built application from builder stage
COPY --from=builder --chown=remixuser:nodejs /app/build ./build
COPY --from=builder --chown=remixuser:nodejs /app/public ./public

# Switch to non-root user
USER remixuser

# Expose port
EXPOSE 3000

# Set healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Start the server
CMD ["yarn", "start"]
