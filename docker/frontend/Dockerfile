# DSP AI Indicator — Frontend (multi-stage, RC1)
FROM node:22-alpine AS deps
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web ./
ARG NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
ARG NEXT_PUBLIC_APP_NAME="DSP AI Indicator"
ARG NEXT_PUBLIC_BUILD_TIMESTAMP
ARG NEXT_PUBLIC_AI_PROVIDER=backend
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NEXT_PUBLIC_APP_NAME=$NEXT_PUBLIC_APP_NAME \
    NEXT_PUBLIC_BUILD_TIMESTAMP=$NEXT_PUBLIC_BUILD_TIMESTAMP \
    NEXT_PUBLIC_AI_PROVIDER=$NEXT_PUBLIC_AI_PROVIDER \
    NODE_ENV=production
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup -S dsp && adduser -S dsp -G dsp

COPY --from=builder /app/public ./public
COPY --from=builder --chown=dsp:dsp /app/.next/standalone ./
COPY --from=builder --chown=dsp:dsp /app/.next/static ./.next/static

USER dsp
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD wget -qO- http://127.0.0.1:3000/api/health || exit 1

CMD ["node", "server.js"]
