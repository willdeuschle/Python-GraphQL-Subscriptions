# Python-GraphQL-Subscriptions
Adds support for subscriptions to GraphQL applications using a Python backend.

## Usage
Use `PubSub` and `SubscriptionManager` from `python_graphql_subscriptions`

```
from python_graphql_subscriptions import PubSub, SubscriptionManager

pubsub = PubSub()

# provide setup_functions for subscriptions if desired
setup_functions = {}

# instantiate SubscriptionManager with your schema, pubsub engine, and setup_functions
subscription_manager = SubscriptionManager(schema, pubsub, setup_functions)

# setup a subscription server for your app (out-of-the-box-ready SubscriptionServer implementation coming soon)
subscription_server = SubscriptionServer(app, subscription_manager)

-----

# subscribe, publish, unsubscribe with the subscription_manager

# subscribe
base_params = {
     'query': query,
     'variables': variables,
     'operation_name': operation_name,
     'context': context,
     'format_response': format_response,
     'format_error': format_error,
     'callback': callback,
}
# subscribe returns subscription id
subscription_id = subscription_manager.subscribe(**base_params)

# publish
# publish(trigger, payload) - invokes the callback from the base_params
subscription_manager.publish('subscription_trigger', payload)

# unsubscribe
subscription_manager.unsubscribe(subscription_id)
```
