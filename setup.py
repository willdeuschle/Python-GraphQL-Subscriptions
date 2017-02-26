from setuptools import setup

setup(name='python_graphql_subscriptions',
      version='0.1',
      description='SubscriptionManager for GraphQL with python backend',
      url='https://github.com/willdeuschle/Python-GraphQL-Subscriptions',
      author='Will Deuschle',
      author_email='wjdeuschle@gmail.com',
      license='MIT',
      packages=['python_graphql_subscriptions'],
      install_requires=[
          'pyee',
          'graphql-core',
      ],
      zip_safe=False)
