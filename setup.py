from setuptools import setup, find_packages

setup(
    name='jangl-utils',
    version='0.1.5',
    packages=find_packages(),
    install_requires=[
        'boto',
        'django-storages',
        'prettyconf',
        'requests',
        'simpleflake',
    ],
    url='https://github.com/revpoint/jangl-utils',
    author='RevPoint Media LLC',
    author_email='jangl@revpointmedia.com',
    description='Common utilities shared among Jangl services.',
)
