########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

import errno
import logging
import os
import subprocess
from contextlib import contextmanager

import click
import yaml

from . import get_plugin_name_from_repo


@contextmanager
def pushd(newdir):
    """
    Context Manager for temporarily moving to a new directory.
    Has stack-like behaviour for nested contexts.
    Named after shell `pushd`/`popd` commands.
    """
    prevdir = os.path.abspath(os.getcwd())
    os.chdir(newdir)
    yield
    os.chdir(prevdir)


def build_component(name, component, out_dir):
    dirname = get_plugin_name_from_repo(name)

    if not os.path.isdir(dirname):
        subprocess.check_call([
            'git', 'clone',
            component['repo'],
            dirname,
            ])

    # There's no need to fetch or pull anything because SCV always builds
    # branches & tags straight from the remote

    with pushd(os.path.join(dirname)):
        print('build dir ', os.getcwd())
        subprocess.check_call([
                'sphinx-versioning',
                'build', 'docs', os.path.join(out_dir, dirname),
                '--root-ref', component['branch'],
                '--banner-main-ref', component['branch'],
                '--show-banner',
                ])


@click.command()
@click.option(
    '--config', default='sphinxify.yaml',
    help='Path to the sphinxify config file',
    type=click.File(),
    )
@click.option(
    '-b', '--build', default='_build',
    help='build DIR. git repos will be cloned here',
    type=click.Path(
        file_okay=False,
        )
    )
@click.option(
    '-o', '--out', default='out',
    help='Output DIR for docs site',
    type=click.Path(
        file_okay=False,
        )
    )
def main(config, build, out):
    config = yaml.load(config)

    # populate missing repo fields
    for name, component in config['components'].items():
        component['name'] = name
        component.setdefault(
            'repo',
            'https://github.com/cloudify-cosmo/{}.git'.format(name))

    out = os.path.abspath(out)
    build = os.path.abspath(build)

    for dir in out, build:
        try:
            os.makedirs(dir)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise

    failures = []

    for name, component in config['components'].items():
        try:
            with pushd(build):
                build_component(name, component, out)
        except Exception as e:
            logging.error(str(e))
            failures.append((name, str(e)))

    if failures:
        logging.error('These components failed: {}'.format(failures))
        exit(1)


if __name__ == '__main__':
    main()
