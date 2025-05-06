## RSS TO GRAPHQL

A microservice proxy to convert an RSS feed to a GraphQL API endpoint

## Install

```shell 
    pip install rss-to-graphql 
```

Requires Python3.6 or later.

## Usage

### CLI for starting the server

```shell
    Usage: python -m  rss_to_graphql [OPTIONS]

    optional arguments:
        -h, --help            Output usage information
        --feed_url FEED_URL   RSS feed url
        --port PORT           Server Port
        --subscriptions_enabled SUBSCRIPTIONS_ENABLED Enable subscriptions, requres a redis cache
        --subscription_ttl SUBSCRIPTION_TTL Subscriptions refresh time to live, in seconds
        --redis_url REDIS_URL Redis url string, e.g. redis://[:password]@localhost:6379/0
```

### Environment Variables

You can use the `FEED_URL` environment variable to specify the RSS feed URL instead of passing it as a `--feed_url` argument. This is particularly useful when running the service in a containerized environment.

Example:

```shell
export FEED_URL=https://example.com/rss
python -m rss_to_graphql --port 8900 --subscriptions_enabled true --redis_url redis://localhost:6379
```

## DockerHub Image

The Docker image for this project is available on DockerHub:

```
silexlabs/rss-to-graphql
```

You can pull the image using:

```bash
docker pull silexlabs/rss-to-graphql
```

## Subscriptions

Supports subscriptions for new itme in the feed. Items are refreshed based on the time-to-live provided by the feed or a user defined refresh period, defaults to 1 minute if neither is provided

## Sample queries

Retrieve channel info

```graphql
{
    channel {
        title
        link
        atomLink {
            href
            rel
        }
        language
        copyright
        description
    }
}
```

Retrieve feed items

```graphql
{
    items {
        title
        description
        link
        pubDate
    }
}
```