# Frontend build + static serve. Network is needed at BUILD time (npm install);
# the running container serves pre-built files and makes no outbound calls.
FROM node:20-slim AS build

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund

COPY . .
# Vite inlines VITE_* at BUILD time; a runtime env var would be ignored and
# the UI would call /api on its own origin (:5173), where nothing answers.
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM node:20-slim
WORKDIR /app
RUN npm install -g serve@14
COPY --from=build /app/dist ./dist

EXPOSE 5173
# --single rewrites unknown paths to index.html so client-side routes work.
CMD ["serve", "-s", "dist", "-l", "5173"]
