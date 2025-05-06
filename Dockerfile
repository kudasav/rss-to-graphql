# Optimized Dockerfile for a multi-RSS feeds to GraphQL server
# docker build -t rss-to-graphql-proxy . && docker run -p 80:80 rss-to-graphql-proxy
# docker build -t rss-to-graphql-proxy . && docker run -p 80:80 -e FEED_URL=https://fosstodon.org/@keila.rss rss-to-graphql-proxy
FROM python:3.9-slim

# Install Redis and Supervisord
RUN apt-get update && apt-get install -y redis-server supervisor && apt-get clean

# Setup the Python app
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy Supervisord configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose the application port
EXPOSE 80

# Allow FEED_URL to be set during build time with a default value
ARG FEED_URL=https://fosstodon.org/@silex.rss
ENV FEED_URL=${FEED_URL}

# Start Supervisord
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
