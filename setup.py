from setuptools import setup, find_packages


INSTALL_REQUIREMENTS = [
    'boto3',
    'bumpversion',
    'cachetools',
    'colorlog',
    'django-storages==1.6.3',
    'djangorestframework>=3.3.0,<3.4',
    'prettyconf',
    'requests',
    'requests_oauthlib>=0.8.0,<0.9',
    'simpleflake',
    'pytz',
    'urllib3',
]

KAFKA_REQUIREMENTS = [
    'rpm-confluent-schemaregistry',
    'confluent-kafka[avro]>=0.11.4',
    'avro==1.8.2-jangl',
    'fastavro>=0.14.7',
]

DEV_REQUIREMENTS = [
    'bumpversion',
    'fabric',
    'pytest-django'
]


setup(
    name='jangl-utils',
    version='0.13.11',
    packages=find_packages(),
    package_data={'jangl_utils': ['templates/bootstrap/*']},
    install_requires=INSTALL_REQUIREMENTS,
    extras_require={
        'kafka': KAFKA_REQUIREMENTS,
        'dev': DEV_REQUIREMENTS,
    },
    scripts=['bin/chronos-sync.rb'],
    url='https://github.com/revpoint/jangl-utils',
    author='RevPoint Media LLC',
    author_email='jangl@revpointmedia.com',
    description='Common utilities shared among Jangl services.',
)
