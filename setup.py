from setuptools import setup

setup(
    name='jangl-utils',
    version='0.1',
    packages=['jangl_utils'],
    install_requires=[
        'prettyconf',
        'simpleflake',
    ],
    zip_safe=True,
    url='https://github.com/revpoint/jangl-utils',
    author='RevPoint Media LLC',
    author_email='jangl@revpointmedia.com',
    description='Common utilities shared among Jangl services.',
)
