""" Create a dependency map using blockdiag. """
# pylint: disable=too-many-lines,missing-docstring,too-many-branches

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2019 Brian Allen Vanderburg II"
__license__ = "MIT License"


__all__ = ["ACTIONS"]


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

                if minversion is not None and CMA._checkdeps_compare(version, minversion) < 0:
                    continue

                if maxversion is not None and CMA._checkdeps_compare(version, maxversion) > 0:
                    continue

                # This node satifies the dependency
                dep_diag_node.satisfy_ids.append(info.node_diag_nodes[node].id)

        # Now we have our links, generate the output
        diag = self.__build_diag(info)
        self.__save_diag(diag)


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

            interesting = True

            info_package_list = info.provided_packages.setdefault(name, [])
            info_package_list.append((node, version))

        # For each dependency, create a dependency diagram node if one does not
        # already exist and remember the dependency diagram nodes for this item
        for depends in node.getmeta("depends"):
            key = (
                depends.get("name"),
                depends.get("minversion"),
                depends.get("maxversion")
            )
            if key[0] is None:
                continue

            interesting = True

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
    def __build_diag(info):
        """ Build the blockdiag code. """

        lines = ["blockdiag {"]

        # First our labels
        for collection_node in info.node_diag_nodes:
            diag_node = info.node_diag_nodes[collection_node]
            lines.append(
                "{0} [label=\"{1}\"];".format(
                    diag_node.id,
                    collection_node.prettypath
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

            lines.append(
                "{0} [label=\"{1}\", color=\"{2}\"];".format(
                    dep_diag_node.id,
                    label,
                    color
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

    def __save_diag(self, diag):
        print(diag)

ACTIONS = [DepMapAction]
