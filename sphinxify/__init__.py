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

import os
import logging
from abc import ABCMeta, abstractproperty
from contextlib import contextmanager
from urllib2 import urlopen, URLError
from StringIO import StringIO

import yaml

from docutils import nodes
from docutils.statemachine import ViewList
from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType, Index
from sphinx.roles import XRefRole
from sphinx.util.docstrings import prepare_docstring
from sphinx.util.nodes import make_refnode


PLUGIN_VERSIONS_YAML = (
        'https://github.com/cloudify-cosmo/cloudify-versions/raw'
        '/master/versions.yaml'
        )

PLUGIN_DOC_URL_TEMPLATE = '../{}/'

ROOT_TYPES = [
    'cloudify.nodes.Root',
    'cloudify.relationships.depends_on',
    ]


types = {}


def merge_dicts(a, b):
    """
    Recursively add the contents of b to a.
    """
    for k, v in b.items():
        if isinstance(v, dict):
            merge_dicts(a.setdefault(k, {}), v)
        else:
            a[k] = v


class node(nodes.Element):
    pass


def check_all_types_documented(app):
    for section in [
            'node_types',
            'data_types',
            'relationships',
            ]:
        for item in types.get(section, []):
            # TODO: make this a hard failure
            if item not in app.env.domains['cfy'].data[section]:
                app.warn(
                    '{item} from {section} '
                    'has not been documented!'.format(
                        item=item,
                        section=section,
                    )
                )


def build_finished(app, exception):
    if exception is not None:
        # Don't mask an already raised exception
        raise exception
    check_all_types_documented(app)


def get_doc(type, prop):
    """
    temporary helper to find doc snippets from the existing docs site repo

    TODO: delete this function.
    """
    with open(os.path.join(
            os.path.dirname(__file__),
            '../../docs.getcloudify.org/content/plugins/openstack.md'),
            'U') as f:
        type_line = '## {}'.format(type)
        print(type_line)
        for line in f:
            if line.startswith(type_line):
                break
        else:
            raise ValueError("didn't find the type")
        start = '* `{}'.format(prop)
        print(start)
        for line in f:
            if line.strip().startswith(start):
                return line.strip().replace(start, '')
        else:
            raise ValueError("didn't find the property")


class CfyDirective(ObjectDescription):
    __metaclass__ = ABCMeta

    def __init__(self, *args, **kwargs):
        super(CfyDirective, self).__init__(*args, **kwargs)

        self.ent_name = self.arguments[0].strip()
        self.data = types[self.section].pop(self.ent_name)

    def handle_signature(self, sig, signode):
        signode.append(addnodes.desc_name(sig, sig))
        return sig, sig.split('.')[:-2]

    def add_target_and_index(self, name, sig, signode):
        if sig not in self.state.document.ids:
            signode['names'].append(sig)
            signode['ids'].append(sig)
            signode['first'] = (not self.names)
            self.state.document.note_explicit_target(signode)
            objects = self.env.domaindata['cfy'][self.section]
            objects[sig] = self.data
            objects[sig]['sphinx_link'] = (self.env.docname, self.objtype)

    def generate_properties(self, node, properties):
        """
        Add the properties to the node
        """
        for name, property in properties.items():
            default = property.get('default')
            type = property.get('type')

            info = '**type:** :cfy:datatype:`{}`'.format(type) if type else ''

            if default is not None:
                if default != '':
                    info += ' **default:** ``{}``'.format(property['default'])
            elif property.get('required', True):
                info += ' **required**'

            try:
                description = property['description']
            except KeyError:
                if type in {
                        'string',
                        'boolean',
                        'list',
                        'integer',
                        None,
                        }:
                    # only custom defined types are allowed to not have a
                    # description
                    print('{type} property {name} has no description'.format(
                        type=self.arguments[0],
                        name=name,
                        ))
                    print(get_doc(self.arguments[0].strip(), name))

                    raise
                else:
                    description = ''

            lines = ViewList(prepare_docstring(
                info + '\n\n' + description + '\n\n'))

            term = nodes.term('', name)
            definition = nodes.definition()
            self.state.nested_parse(
                    lines,
                    self.content_offset + 4,
                    definition,
                    )

            if type not in [
                    'string',
                    'boolean',
                    'list',
                    'integer',
                    ]:
                # Try tp get the nested properties of the type
                data_type = types.get('data_types', {}).get(type)
                if data_type:
                    sub_props = nodes.definition_list()
                    definition.append(sub_props)
                    self.generate_properties(
                            sub_props,
                            data_type['properties']
                            )

            node.append(nodes.definition_list_item(
                '',
                term,
                definition,
                ))

    def after_contentnode(self, node):
        # derived_from:
        if (
                self.ent_name not in ROOT_TYPES and
                self.section != 'data_types'
                ):
            deriv = self.data['derived_from']
            xref_node = addnodes.pending_xref(
                    '', refdomain='cfy', reftype=self.kind,
                    reftarget=deriv,
                    modname=None, classname=None,
                    )
            xref_node += nodes.Text(deriv, deriv)
            node.append(nodes.paragraph(
                'Derived from: ', 'Derived from: ',
                xref_node,
                ))

        if 'properties' in self.data:
            node.append(nodes.rubric('', 'Properties:'))

            props = nodes.definition_list()
            node.append(props)

            self.generate_properties(props, self.data['properties'])

    def run(self):
        indexnode, node = super(CfyDirective, self).run()

        self.after_contentnode(node.children[-1])

        return [indexnode, node]

    @abstractproperty
    def section():
        """
        Name of the section in `plugin.yaml` for this type.
        """

    @abstractproperty
    def kind():
        """
        The kind of object. Used for Sphinx internals & referencing.
        """


class CfyXRefRole(XRefRole):
    pass


class Node(CfyDirective):
    section = 'node_types'
    kind = 'node'


class DataType(CfyDirective):
    section = 'data_types'
    kind = 'datatype'


class Relationship(CfyDirective):
    section = 'relationships'
    kind = 'relationship'


class CfyIndex(Index):

    name = 'cfyindex'
    localname = 'Cloudify Types Index'
    shortname = 'cfyindex'

    def generate(self, docnames=None):
        content = {}

        for kind in self.domain.initial_data:
            items = sorted(self.domain.data[kind].items())

            for type, data in items:
                docname = data['sphinx_link'][0]
                if docnames and docname not in docnames:
                    continue

                content.setdefault(type.split('.')[-1][0].lower(), []).append([
                    type,  # name
                    0,  # subtype (0 == normal entry)
                    docname,  # docname
                    type,  # anchor
                    '',  # extra info
                    '',  # qualifier
                    '',  # description
                    ])

        return sorted(content.items()), False


TYPE_MAP = {
        'node': 'node_types',
        'datatype': 'data_types',
        'rel': 'relationships',
        }


class CfyDomain(Domain):

    name = 'cfy'
    description = 'Cloudify DSL'

    object_types = {
            'node': ObjType('node', 'node'),
            'datatype': ObjType('datatypes', 'rel'),
            'rel': ObjType('relationship', 'rel'),
            }

    directives = {
            'node': Node,
            'datatype': DataType,
            'rel': Relationship,
            }

    roles = {
            'node': CfyXRefRole(),
            'datatype': CfyXRefRole(),
            'rel': CfyXRefRole(),
            }

    indices = [
            CfyIndex,
            ]

    initial_data = {v: {} for v in TYPE_MAP.values()}

    def __init__(self, *args, **kwargs):
        super(CfyDomain, self).__init__(*args, **kwargs)

        for file in self.env.config.cfy_blueprint_paths:
            with self.load_file(file) as f:
                blueprint = yaml.load(f)
                merge_dicts(types, blueprint)

        with self.load_file(PLUGIN_VERSIONS_YAML) as f:
            self.cloudify_versions = yaml.load(f)

    @contextmanager
    def load_file(self, location):
        """
        load a file from a local path or URL
        """
        try:
            f = urlopen(location)
        except ValueError:
            # raised by urlopen for non-url-looking inputs
            f = open(os.path.join(self.env.srcdir, location))
        except URLError as e:
            logging.warn('Unable to load {}:'.format(location), e)
            f = StringIO('components: []')
        yield f
        f.close()

    def resolve_xref(
            self, env, fromdocname, builder, type, target, node, contnode):
        try:
            obj = self.data[TYPE_MAP[type]][target]['sphinx_link']
        except KeyError:
            pass
        else:
            return make_refnode(
                    builder, fromdocname, obj[0], target, contnode, target)

    def get_objects(self):
        for type in (
                'node_types',
                'data_types',
                'relationships',
                ):
            for name, obj in self.data[type].items():
                yield (
                        name,
                        name,
                        type,
                        obj['sphinx_link'][0],
                        name,
                        1,
                        )


def get_plugin_name_from_repo(repo_name):
    """
    Strip off preceding org & -plugin
    """
    return '-'.join(repo_name.split('-')[1:-1])


def html_page_context(app, pagename, templatename, context, doctree):
    """
    Hook to inject extra details into the template
    """
    plugins = context['plugin_links'] = [
            ]
    for plugin in app.env.domains['cfy'].cloudify_versions['components']:
        if plugin.endswith('-plugin'):
            thing = get_plugin_name_from_repo(plugin)
            plugins.append({
                'text': thing,
                'target': PLUGIN_DOC_URL_TEMPLATE.format(thing),
                })


def setup(app):
    app.add_config_value(
            'cfy_blueprint_paths',
            default=['../plugin.yaml'],
            rebuild='env',
            )

    app.add_domain(CfyDomain)

    app.connect('html-page-context', html_page_context)
    app.connect('build-finished', build_finished)

    return {'version': '0.1'}


def get_theme():
    return os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            'themes',
            )
