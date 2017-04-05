
Cloudify Sphinx Extension & Theme
=================================

This repo contains the Cloudify Sphinx Extension,
which is useful for building the docs for plugins,
and the Cloudify docs Sphinx theme.


Extension Usage
---------------

Make sure your dependencies include
``https://github.com/cloudify-cosmo/sphinxify``
and your Sphinx ``conf.py`` includes
``'cloudify_sphinx'`` in the ``extensions`` list.

Document Node Types and Relationships using the::

    .. cfy:node:: <name>

and::

    .. cfy:rel:: <name>

directives.


Blueprint Locations
~~~~~~~~~~~~~~~~~~~

The sphinxify extension loads Nodes and Relationships from blueprints listed in the ``cfy_blueprint_paths`` conf.py option::

    cfy_blueprint_paths = [
        'your blueprint.yaml,
        ]

By default it looks at ``'../plugin.yaml'`` so if you are documenting a plugin it can be left as-is.

If you don't want to document any Nodes or Relationships then set the option to an empty list::

    cfy_blueprint_paths = []


Theme Usage
-----------
Make sure your dependencies include
``https://github.com/cloudify-cosmo/sphinxify``
and set ``html_theme = 'sphinxify'`` in ``conf.py``.
