# Multi-stage build -> a standalone Next.js server (next.config.mjs's
# output: "standalone"), run on Cloud Run. Built from the REPO ROOT as
# context (see cloudbuild.yaml's build-frontend step), same reasoning as
# app/Dockerfile.
FROM node:20-slim AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Cloud Run injects $PORT; Next.js standalone's server.js reads it too.
ENV PORT=8080
EXPOSE 8080
CMD ["node", "server.js"]
