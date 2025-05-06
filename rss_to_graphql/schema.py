import json, re, requests
import xmltodict
import random
import graphene, base64
from rx import Observable
import redis
import hashlib

# sanitise keys
def postprocessor(path, key, value):
    key = key.replace(':', '_')
    key = re.sub(r'\W', '', key)
    
    return key, value

global cache

cache = []

class map_schema:
    def __init__(self, feed_url):

        data = requests.get(feed_url)
        text = data.content.decode('utf-8', 'ignore')

        rss = json.loads(
            json.dumps(
                xmltodict.parse(
                    text,
                    process_namespaces=False,
                    postprocessor=postprocessor
                ),
                indent=4
            )
        )

        if 'ttl' in rss['rss']['channel']:
            self.ttl = int(rss['rss']['channel']['ttl']) * 60000
        else:
            # default = 1 minute
            self.ttl = 60000

        self.items = rss["rss"]["channel"]["item"]
        self.types = {}
        self.items_schema = self.map(self.items[0])

        del rss["rss"]["channel"]['item']
        
        self.channel_schema = self.map(rss["rss"]["channel"])
       

    def map(self, item):
        result = {}
        
        for key in item:
            key = key.strip()

            if type(item[key]) == str:
                result[key] = graphene.String()

            if type(item[key]) == int:
                result[key] = graphene.Int()

            if type(item[key]) == dict:
                if key not in self.types:
                    schema_type = type(key, (graphene.ObjectType,), self.map(item[key]))
                    self.types[key] = schema_type
                else:
                    schema_type = self.types[key]

                result[key] = graphene.Field(schema_type)
            
            if type(item[key]) == list:
                # check if list of strings
                if bool(item[key]) and all(isinstance(i, str) for i in item[key]):
                    result[key] = graphene.List(graphene.String)

                # check if list of integers
                if bool(item[key]) and all(isinstance(i, int) for i in item[key]):
                    result[key] = graphene.List(graphene.Int)
                
                # check if list of dictionarys
                if bool(item[key]) and all(isinstance(i, dict) for i in item[key]):
                    if key not in self.types:
                        schema_type = type(key, (graphene.ObjectType,), self.map(item[key][0]))
                        self.types[key] = schema_type
                    else:
                        schema_type = self.types[key]

                    result[key] = graphene.List(schema_type)
        
        return result


def create_schema(args):

    schema = map_schema(args.feed_url)
    ItemType = type('Item', (graphene.ObjectType,), schema.items_schema)
    ChannelType = type('Channel', (graphene.ObjectType,), schema.channel_schema)

    def fetch():
        data = requests.get(args.feed_url)
        text = data.content.decode('utf-8', 'ignore')

        feed = json.loads(
            json.dumps(
                xmltodict.parse(
                    text,
                    process_namespaces=False,
                    postprocessor=postprocessor
                ),
                indent=4
            )
        )

        return feed

    class Query(graphene.ObjectType):
        items = graphene.List(ItemType)
        channel = graphene.Field(ChannelType)

        def resolve_items(self, info):
            feed = fetch()
            return feed["rss"]["channel"]["item"]

        def resolve_channel(self, info):
            feed = fetch()
            return feed["rss"]["channel"]
    
    genarated_schema = {'query': Query, 'types': [ItemType, ChannelType]+list(schema.types.values())}

    if args.subscriptions_enabled:
        cache = redis.StrictRedis.from_url(args.redis_url)
        cache.ping()

        # add fetched items to cache
        for item in schema.items:
            item_hash = hashlib.sha256(item.get('title', '').encode()).hexdigest()
            if not cache.get('items:'+item_hash):
                cache.set('items:'+item_hash, json.dumps(item))

                # expire item after 1 day
                cache.expire(name='items:'+item_hash, time=1440)

        def subscription_resolver():
            feed = fetch()
            items = feed['rss']['channel']['item']
            new_items = []

            for item in items:
                item_hash = hashlib.sha256(item.get('title', '').encode()).hexdigest()
                if not cache.get('items:'+item_hash):
                    cache.set('items:'+item_hash, json.dumps(item))
                    
                    # expire item after 1 day
                    cache.expire(name='items:'+item_hash, time=1440)
                    new_items.append(item)

            return new_items

        class Subscription(graphene.ObjectType):
            items = graphene.List(ItemType)

            def resolve_items(root, info):

                if not args.subscription_ttl:
                    timeout = schema.ttl
                else:
                    timeout = args.subscription_ttl * 60000

                event =  Observable.interval(timeout) \
                    .map(lambda i: subscription_resolver()) \
                    .filter(lambda i:
                        len(i) > 0
                    )

                return event
        
        genarated_schema['subscription'] = Subscription
    

    return graphene.Schema(**genarated_schema)