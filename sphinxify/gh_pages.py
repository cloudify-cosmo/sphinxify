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

"""
Deploy all versions of the current repo's docs to github pages.
Uses sphinxcontrib-versioning to build all available versions.
"""

import os
from contextlib import contextmanager
from functools import partial
from subprocess import check_call, CalledProcessError


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


def run(command, *args):
    cmdline = [command]
    cmdline.extend(args)
    return check_call(cmdline)


git = partial(run, 'git')


def main():
    # Check the gh-pages branch exists & create if not
    try:
        git('rev-parse', '--verify', 'origin/gh-pages')
    except CalledProcessError:
        git('checkout', '--orphan', 'gh-pages')
        git('add', 'README*')
        git('push', 'origin', 'gh-pages')

    # Build all the docs
    run('sphinx-versioning', '-r', 'master',
        'push', 'docs', 'gh-pages', '.')


if __name__ == '__main__':
    main()
