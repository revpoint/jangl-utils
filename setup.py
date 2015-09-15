from setuptools import setup, find_packages

setup(
    name='jangl-utils',
    version='0.2.13',
    packages=find_packages(),
    package_data={'jangl_utils': ['templates/bootstrap/*.html']},
    include_package_data=True,
    install_requires=[
        'boto',
        'bumpversion',
        'confluent-schemaregistry',
        'django-storages',
        'djangorestframework',
        'prettyconf',
        'pykafka',
        'requests',
        'simpleflake',
        'pytz',
    ],
    dependency_links = [
        'https://github.com/verisign/python-confluent-schemaregistry/archive/v0.1.0.zip#egg=confluent-schemaregistry',
        'git+https://github.com/revpoint/pykafka@676b3119ff9f4cd2a5bebf1ee0e3e52071cd65af#egg=pykafka',
    ],
    scripts=['bin/chronos-sync.rb'],
    url='https://github.com/revpoint/jangl-utils',
    author='RevPoint Media LLC',
    author_email='jangl@revpointmedia.com',
    description='Common utilities shared among Jangl services.',
)
