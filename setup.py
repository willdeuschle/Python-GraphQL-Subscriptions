from setuptools import setup

required_packages = ['pyee', 'graphql-core']

setup(name='python_graphql_subscriptions',
      version='0.1.5',
      description='Adds support for subscriptions to GraphQL applications that use a Python backend.',
      url='https://github.com/willdeuschle/Python-GraphQL-Subscriptions',
      author='Will Deuschle',
      author_email='wjdeuschle@gmail.com',
      license='MIT',
      packages=['python_graphql_subscriptions'],
      install_requires=required_packages,
      tests_require=['pytest'],
      zip_safe=False)
