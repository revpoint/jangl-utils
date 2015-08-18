from setuptools import setup, find_packages

setup(
    name='jangl-utils',
    version='0.1.19',
    packages=find_packages(),
    package_data={'jangl_utils': ['templates/bootstrap/*.html']},
    include_package_data=True,
    install_requires=[
        'boto',
        'bumpversion',
        'django-storages',
        'djangorestframework',
        'prettyconf',
        'requests',
        'simpleflake',
    ],
    url='https://github.com/revpoint/jangl-utils',
    author='RevPoint Media LLC',
    author_email='jangl@revpointmedia.com',
    description='Common utilities shared among Jangl services.',
)
