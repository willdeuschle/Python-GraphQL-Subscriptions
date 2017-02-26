#
# implements PubSub and SubscriptionManager
#

from pyee import EventEmitter
from graphql import (
    parse,
    validate,
    specified_rules,
    value_from_ast,
    execute,
)
from graphql.language.ast import OperationDefinition


class PubSub(object):
    """
    Fulfills the necessary subscription engine interface by defining:
    - publish
    - subscribe
    - unsubscribe
    """
    def __init__(self):
        # use an event emitter similar to that of node.js EventEmitter
        self.ee = EventEmitter()
        self.subscriptions = {}
        self.sub_id_counter = 0

    def publish(self, trigger_name, payload):
        """
        publish a payload to the specified channel
        """
        self.ee.emit(trigger_name, payload)
        return True

    def subscribe(self, trigger_name, on_message, **options):
        """
        subscribe to a given channel to get updates from mutations
        """
        self.ee.on(trigger_name, on_message)
        self.sub_id_counter += 1
        self.subscriptions[self.sub_id_counter] = [trigger_name, on_message]
        return self.sub_id_counter

    def unsubscribe(self, subId):
        """
        removes the listener for this subscription
        """
        trigger_name, on_message = self.subscriptions[subId]
        self.subscriptions.pop(subId)
        self.ee.remove_listener(trigger_name, on_message)


class SubscriptionManager(object):
    """
    Handles the actual graphql subscriptions. Exposes:
    - publish
    - subscribe
    - unsubscribe
    """
    def __init__(self,
                 schema,
                 pubsub,
                 setup_functions={},
                 **kwargs):
        self.schema = schema
        self.pubsub = pubsub
        self.setup_functions = setup_functions
        self.subscriptions = {}
        self.max_subscription_id = 0

    def publish(self, trigger_name, payload):
        """
        just publish using pubsub engine
        """
        self.pubsub.publish(trigger_name, payload)

    def subscribe(self, **kwargs):
        """
        set up a subscription
        """
        # first validate the query, operation_name, variables
        parsed_query = parse(kwargs['query'])
        # TODO enforce that the subscription only has a single root field
        errors = validate(
            self.schema,
            parsed_query,
            specified_rules,
        )

        # reject right here if there are any errors
        if errors:
            raise ValueError('There was a problem with your subscription')

        args = {}

        # access the root field, subscription name,
        # and parse the arguments passed in
        subscription_name = ''
        for definition in parsed_query.definitions:
            if isinstance(definition, OperationDefinition):
                # there can only be a single root field on a subscription
                # the root field will be the first selection
                root_field = definition.selection_set.selections[0]
                subscription_name = root_field.name.value

                fields = self.schema.get_subscription_type().fields
                for arg in root_field.arguments:
                    # access argument's definition from the schema
                    arg_definition = fields[subscription_name].args.get(arg.name.value, None)
                    # parse the variable value and add it to our args
                    if arg_definition:
                        args[arg.name.value] = value_from_ast(arg.value, arg_definition.type, kwargs['variables'])

        # see if the channel we are trying to subscribe to was declared
        # in the setup_functions and do some prep if it was
        if self.setup_functions.get(subscription_name, None):
            # execute the setup_function for this subscription_name
            trigger_map = self.setup_functions[subscription_name](kwargs, args, subscription_name)
        else:
            # otherwise use the defaults, with the subscription_name being
            # the key for the trigger_map
            trigger_map = {subscription_name: {}}


        # increment the current subscription id
        self.max_subscription_id += 1
        # for this subscription channel, we will set up an array of
        # subscriptions (if, for example, multiple components were to
        # subscribe to this channel)
        self.subscriptions[self.max_subscription_id] = []

        # each channel this subscription subscribes us to
        for trigger_name in trigger_map.keys():
            # access properties of the trigger_map and assign defaults if absent
            channel_options = trigger_map[trigger_name].get('channel_options', {})
            # default is to let all things pass through
            filter_func = trigger_map[trigger_name].get('filter', lambda *args, **kwargs: True)

            # generate the handler function
            # root_value is the payload returned by the EventEmitter / trigger,
            # by default it is the value returned from the mutation resolver
            def on_message(root_value):
                # check if it's a funciotn
                if callable(kwargs['context']):
                    context = kwargs['context']()
                else:
                    context = kwargs['context']
                # eval the filter function to see how we should proceed
                do_execute = filter_func(root_value, context, **kwargs['variables'])
                if not do_execute:
                    return
                try:
                    data = execute(self.schema,
                                   parsed_query,
                                   root_value,
                                   context,
                                   kwargs['variables'],
                                   kwargs.get('operation_name', None))
                    kwargs['callback'](None, data)
                except Exception as e:
                    kwargs['callback'](e)

            # subscribe and keep the sub id
            sub_id = self.pubsub.subscribe(trigger_name, on_message, **channel_options)
            self.subscriptions[self.max_subscription_id].append(sub_id)

        # return the subscription id for this whole subscribe operation
        return self.max_subscription_id

    def unsubscribe(self, sub_id):
        # pass id through to pubsub to unsubscribe every subscription
        for internal_sub_id in self.subscriptions[sub_id]:
            self.pubsub.unsubscribe(internal_sub_id)
        self.subscriptions.pop(sub_id)
