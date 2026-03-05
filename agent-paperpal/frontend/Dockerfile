# frontend/Dockerfile
# React + Vite frontend for Agent Paperpal

FROM node:20-slim AS base

WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy application source
COPY . .

EXPOSE 5173

# Development mode (default)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ── Production build (multi-stage) ─────────────────────────────────────────
FROM base AS build
RUN npm run build

FROM nginx:alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
