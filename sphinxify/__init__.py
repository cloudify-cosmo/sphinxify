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
from abc import ABCMeta, abstractproperty

import yaml

from docutils import nodes
from docutils.statemachine import ViewList
from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.roles import XRefRole
from sphinx.util.docstrings import prepare_docstring
from sphinx.util.nodes import make_refnode


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
            'relationships',
            ]:
        for item in types.get(section, []):
            # TODO: make this a hard failure
            app.warn('{item} from {section} has not been documented!'.format(
                item=item,
                section=section,
                ))


def build_finished(app, exception):
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

        self.data = types[self.section].pop(
                self.arguments[0].strip())

    def handle_signature(self, sig, signode):
        signode.append(addnodes.desc_name(sig, sig))
        return sig, sig.split('.')[:-2]

    def add_target_and_index(self, name, sig, signode):
        if sig not in self.state.document.ids:
            signode['names'].append(sig)
            signode['ids'].append(sig)
            signode['first'] = (not self.names)
            self.state.document.note_explicit_target(signode)
            objects = self.env.domaindata['cfy'][self.kind]
            objects[sig] = (self.env.docname, self.objtype)

    def after_contentnode(self, node):
        # derived_from:
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

            for name, property in self.data['properties'].items():
                try:
                    desc = property['description']
                except KeyError:
                    print('{type} property {name} has no description'.format(
                        type=self.arguments[0],
                        name=name,
                        ))
                    print(get_doc(self.arguments[0].strip(), name))

                    raise

                info = ''

                default = property.get('default', None)
                if default is not None:
                    if default != '':
                        info += ' **default:** {}'.format(property['default'])
                elif property.get('required', True):
                    info += ' **required**'

                term = nodes.term('', name)
                lines = ViewList(prepare_docstring(
                    info + '\n\n' + desc + '\n\n'))
                definition = nodes.definition()
                self.state.nested_parse(
                        lines,
                        self.content_offset + 4,
                        definition,
                        )

                props.append(nodes.definition_list_item(
                    '',
                    term,
                    definition,
                    ))

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


class Relationship(CfyDirective):
    section = 'relationships'
    kind = 'relationship'


class CfyDomain(Domain):

    def __init__(self, *args, **kwargs):
        super(CfyDomain, self).__init__(*args, **kwargs)

        for file in self.env.config.cfy_blueprint_paths:
            with open(file) as f:
                blueprint = yaml.load(f)
                merge_dicts(types, blueprint)

    name = 'cfy'
    description = 'Cloudify DSL'

    object_types = {
            'node': ObjType('node', 'node'),
            'rel': ObjType('relationship', 'rel'),
            }

    directives = {
            'node': Node,
            'rel': Relationship,
            }

    roles = {
            'node': CfyXRefRole(),
            'rel': CfyXRefRole(),
            }

    initial_data = {
            'node': {},
            'relationship': {},
            }

    def resolve_xref(
            self, env, fromdocname, builder, type, target, node, contnode):
        try:
            obj = self.data[type][target]
        except KeyError:
            pass
        else:
            return make_refnode(
                    builder, fromdocname, obj[0], target, contnode, target)

    def get_objects(self):
        for type in ['node', 'relationship']:
            for name, obj in self.data[type].items():
                yield (
                        name,
                        name,
                        type,
                        obj[0],
                        name,
                        1,
                        )


def setup(app):
    app.add_config_value(
            'cfy_blueprint_paths',
            default=['../plugin.yaml'],
            rebuild='env',
            )

    app.add_domain(CfyDomain)

    app.connect('build-finished', build_finished)

    return {'version': '0.1'}


def get_theme():
    return os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            'themes',
            )
