FROM node:22-alpine AS build
WORKDIR /workspace
COPY package.json package-lock.json ./
COPY packages/core/package.json packages/core/package.json
COPY frontend/package.json frontend/package.json
RUN npm ci
COPY packages/core packages/core
COPY frontend frontend
RUN npm --workspace ai-tutor-web run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build /workspace/frontend/.next/standalone ./
COPY --from=build /workspace/frontend/.next/static ./frontend/.next/static
COPY --from=build /workspace/frontend/public ./frontend/public
CMD ["node", "frontend/server.js"]
