from flask import Flask, make_response
from flask_graphql import GraphQLView
from flask_sockets import Sockets
from graphql_ws.gevent import GeventSubscriptionServer
from argparse import ArgumentParser
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
import os

from rss_to_graphql import create_schema, render_graphiql
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.debug = True
sockets = Sockets(app)

if __name__ == '__main__':
    parser = ArgumentParser(description="RSS TO Graphql")
    parser.add_argument('--feed_url', type=str, required=False, help='RSS feed url')  # Remove required=True
    parser.add_argument('--port', type=int, required=False, help='Port to listen on (defaults to 8900)')
    parser.add_argument('--subscriptions_enabled', type=bool, required=False, default=False, help='Enable subscriptions, requres a redis cache')
    parser.add_argument('--subscription_ttl', type=int, required=False, help='Subscriptions refresh time to live, in seconds')
    parser.add_argument('--redis_url', type=str, required=False, help='Redis url string, e.g. redis://[:password]@localhost:6379/0')

    args = parser.parse_args()

    # Use FEED_URL from environment if not provided as an argument
    if not args.feed_url:
        args.feed_url = os.environ.get("FEED_URL")
        if not args.feed_url:
            parser.error("RSS feed URL must be provided via --feed_url or FEED_URL environment variable")

    print(f"Using feed URL: {args.feed_url}")  # Log the feed URL for debugging

    if args.subscriptions_enabled and not args.redis_url:
        parser.error("--subscriptions_enabled requires --redis_url")

    if args.port:
        port = args.port
    else:
        port = 8900

    schema = create_schema(args)
    subscription_server = GeventSubscriptionServer(schema)
    app.app_protocol = lambda environ_path_info: "graphql-ws"

    app.add_url_rule(
        "/graphql", view_func=GraphQLView.as_view("graphql", schema=schema, graphiql=False, context={'ttl': args.subscription_ttl})
    )

    @app.route("/")
    def graphql_view():
        return make_response(render_graphiql())

    @sockets.route("/subscriptions")
    def echo_socket(ws):
        subscription_server.handle(ws)
        return []

    print('Serving on port {}...'.format(port))
    server = pywsgi.WSGIServer(("", port), app, handler_class=WebSocketHandler).serve_forever()