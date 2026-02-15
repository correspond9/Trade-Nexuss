FROM node:18-alpine AS build
WORKDIR /app

# Install dependencies with fallback strategies
COPY package*.json ./
RUN npm install --verbose --no-audit --legacy-peer-deps 2>&1 || \
    (npm cache clean --force && npm install --no-audit --legacy-peer-deps 2>&1) || \
    npm install --ignore-scripts --no-audit --legacy-peer-deps 2>&1

# Copy source and build
COPY . .
# Allow overriding API base at build time. Default to '/api/v2' to match backend routes.
ARG VITE_API_URL=/api/v2
ENV VITE_API_URL=${VITE_API_URL}
RUN echo "Building with VITE_API_URL=${VITE_API_URL}" && npm run build

FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.prod.conf /etc/nginx/conf.d/default.conf
RUN apk add --no-cache curl
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
