""" The various actions supported. """

__author__ = "Brian Allen Vanderburg II"
__copyright__ = "Copyright (C) 2013-2018 Brian Allen Vanderburg II"
__license__ = "MIT License"

__all__ = ["ACTIONS"]


# Import submodules
def _import_actions():
    import pkgutil
    import importlib

    actions = {}
    for (_, name, _) in pkgutil.iter_modules(__path__):
        pkg_name = __package__ + "." + name
        module = importlib.import_module(pkg_name)

        module_actions = getattr(module, "ACTIONS", None)
        if module_actions is None:
            continue

        for action in module_actions:
            assert action.ACTION_NAME not in actions, "Duplicate Action {0}".format(action_name)
            actions[action.ACTION_NAME] = action

    return actions


# Load them
ACTIONS = _import_actions()
del _import_actions

