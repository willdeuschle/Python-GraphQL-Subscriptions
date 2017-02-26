import pytest
from mock import Mock
from pyee import EventEmitter

from python_graphql_subscriptions import PubSub, SubscriptionManager
from .schema import Schema

###
# testing PubSub
###

@pytest.fixture
def pubsub():
    return PubSub()

def test_PubSub_init(pubsub):
    assert isinstance(pubsub.ee, EventEmitter)
    assert pubsub.subscriptions == {}
    assert pubsub.sub_id_counter == 0

def test_PubSub_publish(pubsub):
    assert pubsub.publish('foo', 'bar') == True

def test_PubSub_subscribe(pubsub):
    assert pubsub.sub_id_counter == 0
    assert pubsub.subscriptions == {}
    trigger_name = 'foo'
    on_message = 'bar'
    pubsub.subscribe(trigger_name, on_message)
    assert pubsub.sub_id_counter == 1
    assert len(pubsub.subscriptions.keys()) == 1
    assert pubsub.subscriptions[1] == [trigger_name, on_message]

def test_PubSub_unsubscribe(pubsub):
    trigger_name = 'foo'
    on_message = 'bar'
    pubsub.subscribe(trigger_name, on_message)
    assert pubsub.sub_id_counter == 1
    assert len(pubsub.subscriptions.keys()) == 1
    assert pubsub.subscriptions[1] == [trigger_name, on_message]
    pubsub.unsubscribe(1)
    assert pubsub.sub_id_counter == 1
    assert len(pubsub.subscriptions.keys()) == 0

def test_PubSub_events(pubsub):
    not_triggered = ['foo']
    trigger_name = 'bar'
    def on_message(payload):
        not_triggered[0] = payload
        return
    pubsub.subscribe(trigger_name, on_message)
    assert not_triggered == ['foo']
    payload = 'baz'
    pubsub.publish(trigger_name, payload)
    assert not_triggered == [payload]
    pubsub.unsubscribe(1)
    ineffective_payload = 'qux'
    pubsub.publish(trigger_name, payload)
    assert not_triggered == [payload]


###
# testing SubscriptionManager
###

def test_SubscriptionManager_init():
    schema = 'schema'
    pubsub = 'pubsub'
    setup_functions = {}
    subscriptions = {}
    max_subs = 0
    sub_manager = SubscriptionManager(
        schema,
        pubsub,
        setup_functions,
    )
    assert sub_manager.schema == schema
    assert sub_manager.pubsub == pubsub
    assert sub_manager.setup_functions == setup_functions
    assert sub_manager.max_subscription_id == max_subs
    assert sub_manager.subscriptions == subscriptions

def test_SubscriptionManager_publishes(pubsub):
    schema = 'schema'
    setup_functions = {}
    sub_manager = SubscriptionManager(
        schema,
        pubsub,
        setup_functions,
    )
    trigger_name = 'foo'
    on_message = 'bar'
    pubsub.publish = Mock()
    sub_manager.publish(trigger_name, on_message)
    pubsub.publish.assert_called_with(trigger_name, on_message)

def test_SubscriptionManager_errors_on_subscription_with_missing_query(pubsub):
    schema = Schema
    setup_functions = {}
    sub_manager = SubscriptionManager(
        schema,
        pubsub,
        setup_functions,
    )
    pytest.raises(KeyError, sub_manager.subscribe, **{})

def test_SubscriptionManager_errors_on_bad_query(pubsub):
    schema = Schema
    setup_functions = {}
    sub_manager = SubscriptionManager(
        schema,
        pubsub,
        setup_functions,
    )
    kwargs = { 'query': 'query a{ testInt }' }
    pytest.raises(ValueError, sub_manager.subscribe, **kwargs)


def test_SubscriptionManager_subscribes_with_valid_query(pubsub):
    schema = Schema
    setup_functions = {}
    sub_manager = SubscriptionManager(
        schema,
        pubsub,
        setup_functions,
    )
    kwargs = {'query': 'subscription X{ test_subscription }'}
    sub_id = sub_manager.subscribe(**kwargs)
    assert sub_id == 1

def test_SubscriptionManager_filters_properly(pubsub):
    schema = Schema
    setup_functions = {
        'test_filter_sub': lambda options, context, variables: {
            'filter_1': {
                'filter': lambda root, context, **variables: root['filter_bool'] == variables['filter_bool']

            },
        }
    }
    sub_manager = SubscriptionManager(
        schema,
        pubsub,
        setup_functions,
    )
    def callback(error=None, result=None):
        assert result.data['test_filter_sub'] == 'SUCCESS'
    kwargs = {'query': 'subscription test_filter($filter_bool: Boolean){ \
                  test_filter_sub(filter_bool: $filter_bool) }',
              'operation_name': 'test_filter',
              'variables': {'filter_bool': True},
              'callback': callback,
              'context': {},
    }
    sub_id = sub_manager.subscribe(**kwargs)
    sub_manager.publish('filter_1', { 'filter_bool': True })

def test_SubscriptionManager_subscribes_multiple_triggers(pubsub):
    called = [0]
    schema = Schema
    setup_functions = {
        'test_filter_sub': lambda options, context, variables: {
            'sub_1': {},
            'sub_2': {}
        }
    }
    sub_manager = SubscriptionManager(
        schema,
        pubsub,
        setup_functions,
    )
    def callback(error=None, result=None):
        called[0] += 1
        assert result.data['test_filter_sub'] == 'SUCCESS'
    kwargs = {'query': 'subscription test_filter($filter_bool: Boolean){ \
                  test_filter_sub(filter_bool: $filter_bool) }',
              'operation_name': 'test_filter',
              'variables': {'filter_bool': True},
              'callback': callback,
              'context': {},
    }
    sub_id = sub_manager.subscribe(**kwargs)
    assert called == [0]
    sub_manager.publish('sub_1', {})
    assert called == [1]
    sub_manager.publish('sub_2', {})
    assert called == [2]

def test_SubscriptionManager_can_unsubscribe(pubsub):
    called = [0]
    schema = Schema
    setup_functions = {
        'test_filter_sub': lambda options, context, variables: {
            'sub_1': {},
        }
    }
    sub_manager = SubscriptionManager(
        schema,
        pubsub,
        setup_functions,
    )
    def callback(error=None, result=None):
        called[0] += 1
        assert result.data['test_filter_sub'] == 'SUCCESS'
    kwargs = {'query': 'subscription test_filter($filter_bool: Boolean){ \
                  test_filter_sub(filter_bool: $filter_bool) }',
              'operation_name': 'test_filter',
              'variables': {'filter_bool': True},
              'callback': callback,
              'context': {},
    }
    sub_id = sub_manager.subscribe(**kwargs)
    assert called == [0]
    sub_manager.publish('sub_1', {})
    assert called == [1]
    sub_manager.unsubscribe(sub_id)
    sub_manager.publish('sub_1', {})
    assert called == [1]

def test_SubscriptionManager_errors_on_unknown_sub_id(pubsub):
    schema = Schema
    setup_functions = {}
    sub_manager = SubscriptionManager(
        schema,
        pubsub,
        setup_functions,
    )
    pytest.raises(KeyError, sub_manager.unsubscribe, 1)

def test_SubscriptionManager_errors_on_repeat_unsubscribe(pubsub):
    schema = Schema
    setup_functions = {}
    sub_manager = SubscriptionManager(
        schema,
        pubsub,
        setup_functions,
    )
    kwargs = {'query': 'subscription X{ test_subscription }'}
    sub_id = sub_manager.subscribe(**kwargs)
    assert sub_id == 1
    sub_manager.unsubscribe(sub_id)
    pytest.raises(KeyError, sub_manager.unsubscribe, sub_id)


def test_SubscriptionManager_calls_context_if_a_function(pubsub):
    schema = Schema
    setup_functions = {
        'test_filter_sub': lambda options, context, variables: {
            'sub_1': {},
        }
    }
    sub_manager = SubscriptionManager(
        schema,
        pubsub,
        setup_functions,
    )
    context = Mock(return_value={})
    kwargs = {'query': 'subscription test_filter($filter_bool: Boolean){ \
                  test_filter_sub(filter_bool: $filter_bool) }',
              'operation_name': 'garbage',
              'variables': {},
              'callback': lambda error: True,
              'context': context,
    }
    sub_id = sub_manager.subscribe(**kwargs)
    assert context.call_count == 0
    sub_manager.pubsub.publish('sub_1', {})
    assert context.call_count == 1
