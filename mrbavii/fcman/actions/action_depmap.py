""" Create a dependency map using blockdiag. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2019 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


import os

from .. import collection
from .base import ActionBase
from .action_checkmeta import CheckMetaAction as CMA

# Relevant code
#    from blockdiag import parser, builder, drawer
#
#    tree = parser.parse_string(source)
#    diagram = builder.ScreenNodeBuilder.build(tree)
#    draw = drawer.DiagramDraw('PNG', diagram, filename="foo.png")
#    draw.draw()
#    draw.save()


class _DiagNode:
    """ Helper node to keep track of ID value """
    _counter = 0

    @classmethod
    def next_id(cls):
        _DiagNode._counter += 1
        return "N{0}".format(cls._counter)

class _NodeDiagNode(_DiagNode):
    def __init__(self, node, deps):
        self.id = self.next_id()
        self.node = node
        self.deps_ids = list(deps)

class _DepDiagNode(_DiagNode):
    def __init__(self, name, minver, maxver):
        self.name = name
        self.minver = minver
        self.maxver = maxver
        self.id = self.next_id()
        self.satisfy_ids = [] # ID of file diag nodes that satisfy this

class _Info:
    def __init__(self):
        self.dep_diag_nodes = {} # (name, minver, maxver): node
        self.node_diag_nodes = {} # collection node: node
        self.provided_packages = {} # package name: [(collection node, version)]


class DepMapAction(ActionBase):
    """ Create a map of the dependencies. """

    ACTION_NAME = "depmap"
    ACTION_DESC = "Create dependency map"""

    @classmethod
    def add_arguments(cls, parser):
        """ Add the arguments. """
        super(DepMapAction, cls).add_arguments(parser)

        parser.add_argument(
            "-t", "--type",
            dest="type",
            default="jpg",
            help="Specify the output type (jpg, png, svg)"
        )

    def run(self):
        """ Run the action """

        # First scan the nodes for useful information
        info = _Info()
        self.__scan_nodes(self.program.collection.rootnode, info)

        # Once child nodes are scanned, we have our first link:
        # Node diagram node -> dependency diagram node
        # Now we need to create our dependency diagram node to node diagram
        # nodes:

        for key in info.dep_diag_nodes:
            (name, minversion, maxversion) = key
            dep_diag_node = info.dep_diag_nodes[key]

            package_nodes = info.provided_packages.get(name)
            if package_nodes is None:
                continue

            for (node, version) in package_nodes:

                # if package doesn't have a version but we need a version then it fails
                if version is None and (minversion is not None or maxversion is not None):
                    continue

                if minversion is not None and CMA._checkdeps_compare(version, minversion) < 0:
                    continue

                if maxversion is not None and CMA._checkdeps_compare(version, maxversion) > 0:
                    continue

                # This node satifies the dependency
                dep_diag_node.satisfy_ids.append(info.node_diag_nodes[node].id)

        # Now we have our links, generate the output
        diag = self.__build_diag(info)
        return self.__save_diag(diag)


    def __scan_nodes(self, node, info):
        """ Determine if a node is of interest for the dependency map. """

        # For each interesting item, if interesting:
        # keep a map of any packages provided to the items that provide the package
        # for each dependency, ensure a dependency node exists
        # for the item, create an item node and go ahead and link it to the dependency nodes
        interesting = False

        dep_diag_nodes_ids = []

        # For each provides name, add to the info provides list
        for package in node.getmeta("provides"):
            name = package.get("name", None)
            if name is None:
                continue

            version = package.get("version", None)
            if version == "":
                version = None

            interesting = True

            info_package_list = info.provided_packages.setdefault(name, [])
            info_package_list.append((node, version))

        # For each dependency, create a dependency diagram node if one does not
        # already exist and remember the dependency diagram nodes for this item
        for depends in node.getmeta("depends"):
            key = [
                depends.get("name"),
                depends.get("minversion"),
                depends.get("maxversion")
            ]
            if key[0] is None:
                continue

            interesting = True

            # Make min/max None for easy checking 
            if key[1] == "":
                key[1] = None
            if key[2] == "":
                key[2] = None

            key = tuple(key)


            dep_diag_node = info.dep_diag_nodes.get(key, None)
            if dep_diag_node is None:
                dep_diag_node = info.dep_diag_nodes[key] = _DepDiagNode(key[0], key[1], key[2])

            dep_diag_nodes_ids.append(dep_diag_node.id)

        # If this node was interesting, add to our node diagram nodes
        if interesting:
            # since we already know the node -> dependency diag node lists, we can attach here
            info.node_diag_nodes[node] = _NodeDiagNode(node, dep_diag_nodes_ids)

        # Handle children if needed
        if isinstance(node, collection.Directory):
            for child in sorted(node.children):
                self.__scan_nodes(node.children[child], info)

    @staticmethod
    def __calc_labels(labels):
        """ Calculate the width/height needed for the labels. """
        lines = len(labels)
        chars = max(len(label) for label in labels)

        width = chars * 10
        height = lines * 22

        return (width, height)

    @classmethod
    def __build_diag(cls, info):
        """ Build the blockdiag code. """

        lines = ["blockdiag {"]

        # First our labels
        for collection_node in info.node_diag_nodes:
            diag_node = info.node_diag_nodes[collection_node]
            label_parts = [collection_node.prettypath]
            for package in collection_node.getmeta("provides"):
                (name, version) = (
                    package.get("name"),
                    package.get("version")
                )

                if name in (None, ""):
                    continue
    
                if version not in (None, ""):
                    label_parts.append(
                        "Package: {0}:{1}".format(name, version)
                    )
                else:
                    label_parts.append(
                        "Package: {0}".format(name)
                    )

            (w, h) = cls.__calc_labels(label_parts)

            lines.append(
                "{0} [label=\"{1}\",width={2},height={3}];".format(
                    diag_node.id,
                    "\\n".join(label_parts),
                    w,
                    h
                )
            )

        for key in info.dep_diag_nodes:
            (name, minver, maxver) = key
            dep_diag_node = info.dep_diag_nodes[key]
            label = "DEP: {0}".format(name)
            if minver is not None:
                label = "{0} >= {1}".format(label, minver)
            if maxver is not None:
                label = "{0} <= {1}".format(label, maxver)

            if len(dep_diag_node.satisfy_ids):
                color = "lightgreen"
            else:
                color = "pink"

            (w, h) = cls.__calc_labels([label])

            lines.append(
                "{0} [label=\"{1}\",color=\"{2}\",width={3},height={4}];".format(
                    dep_diag_node.id,
                    label,
                    color,
                    w,
                    h
                )
            )

        # Now the links
        for collection_node in info.node_diag_nodes:
            diag_node = info.node_diag_nodes[collection_node]
            for dep_node_id in diag_node.deps_ids:
                lines.append(
                    "{0} -> {1};".format(
                        diag_node.id,
                        dep_node_id
                    )
                )
        for key in info.dep_diag_nodes:
            diag_node = info.dep_diag_nodes[key]
            for satisfy_id in diag_node.satisfy_ids:
                lines.append(
                    "{0} -> {1};".format(
                        diag_node.id,
                        satisfy_id
                    )
                )

        # End the diagram
        lines.append("}")

        return "\n".join(lines)

    def __save_diag(self, source):
        try:
            from blockdiag import parser, builder, drawer
        except ImportError:
            self.writer.stderr.status("", "Python blockdiag not installed.")
            return False

        if not os.path.isdir(self.program.collection.exportdir):
            os.makedirs(self.program.collection.exportdir)

        diagfile = os.path.join(
            self.program.collection.exportdir,
            "depmap"
        )

        opt_type = self.program.options.type.lower()
        if opt_type in ("jpg", "jpeg"):
            type = "JPEG"
            diagfile += ".jpg"
        elif opt_type == "png":
            type = "PNG"
            diagfile += ".png"
        elif opt_type == "svg":
            type = "SVG"
            diagfile += ".svg"

        tree = parser.parse_string(source)
        diagram = builder.ScreenNodeBuilder.build(tree)
        draw = drawer.DiagramDraw(type, diagram, filename=diagfile)
        draw.draw()
        draw.save()

ACTIONS = [DepMapAction]
