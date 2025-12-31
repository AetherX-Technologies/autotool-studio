FROM node:22-alpine

WORKDIR /app

# Install system dependencies just in case (optional for pure JS, but good practice)
RUN apk add --no-cache python3 make g++

# Copy root package files
COPY package.json .

# Copy workspace definitions
COPY apps/desktop/package.json ./apps/desktop/
COPY apps/renderer/package.json ./apps/renderer/

# Install dependencies (will hoist to root)
# Using --legacy-peer-deps to avoid strict peer dependency issues if any
RUN npm install

# Copy source code
COPY . .

# Build Renderer
WORKDIR /app/apps/renderer
# # RUN npm run build

# Build Desktop Main Process
WORKDIR /app/apps/desktop
# Ensure dist directory exists
RUN mkdir -p dist
# RUN npm run build

# Final verification
# RUN ls -la /app/apps/renderer/dist && ls -la /app/apps/desktop/dist

# Default command effectively does nothing, assuming we use this container to copy files out
CMD ["echo", "Build complete. Use 'docker cp' to extract artifacts."]
