from setuptools import setup, find_packages

setup(
    name='jangl-utils',
    version='0.6.2',
    packages=find_packages(),
    package_data={'jangl_utils': ['templates/bootstrap/*']},
    install_requires=[
        'boto',
        'bumpversion',
        'django-storages',
        'djangorestframework',
        'prettyconf',
        'requests',
        'simpleflake',
        'pytz',
    ],
    extras_require={
        'kafka': ['rpm-confluent-schemaregistry', 'pykafka'],
        'dev': ['bumpversion', 'fabric', 'pytest-django']
    },
    scripts=['bin/chronos-sync.rb'],
    url='https://github.com/revpoint/jangl-utils',
    author='RevPoint Media LLC',
    author_email='jangl@revpointmedia.com',
    description='Common utilities shared among Jangl services.',
)
