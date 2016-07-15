from fabric.api import *
import os
import sys

VIRTUAL_ENV = os.environ.get('VIRTUAL_ENV')
ACTIVATE = 'source {0}/bin/activate && '.format(VIRTUAL_ENV) if VIRTUAL_ENV else ''


def venv_local(command, *args, **kwargs):
    return local(ACTIVATE + command, *args, **kwargs)


@task
def bump(version='patch'):
    # Version should be either: major, minor, patch
    venv_local('bumpversion {0} --list'.format(version))
    local('git push')


@task
def check_pypirc():
    conf = os.path.expanduser('~/.pypirc')
    open(conf, 'a').close()
    with open(conf) as pypirc:
        if '[jangl]' not in pypirc.read():
            print '\n[jangl] does not exist in ~/.pypirc\n'
            sys.exit(1)


@task
def push_to_pypi():
    check_pypirc()
    local('python setup.py sdist upload -r jangl')

@task
def push():
    push_to_pypi()
