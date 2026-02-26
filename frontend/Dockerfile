# =============================================================================
# AI Publisher Pro — Production Frontend Dockerfile
# Next.js 16 standalone build
# =============================================================================

FROM node:22-alpine AS builder

WORKDIR /app

# Install deps first (cache layer)
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source and build
COPY . .

# Set API URL at build time (can be overridden at runtime)
ARG NEXT_PUBLIC_API_URL=http://localhost:3000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# --- Production stage ---
FROM node:22-alpine

WORKDIR /app

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copy build output
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public 2>/dev/null || true

USER nextjs

EXPOSE 3001

ENV PORT=3001 \
    HOSTNAME="0.0.0.0" \
    NODE_ENV=production

CMD ["node", "server.js"]
