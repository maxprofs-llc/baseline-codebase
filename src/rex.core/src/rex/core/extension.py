#
# Copyright (c) 2013-2014, Prometheus Research, LLC
#


from .cache import cached
from .package import get_packages, Package


class Extension(object):
    """
    Provides extension mechanism for RexDB applications.

    To create a new extensible interface, declare a subclass of
    :class:`Extension`.

    To create an implementation of the interface, declare a subclass of the
    interface class.

    Use methods :meth:`all()`, :meth:`top()`, :meth:`mapped()`,
    :meth:`ordered()` to find implementations for the given interface.
    """

    class __metaclass__(type):

        def __new__(mcls, name, bases, members):
            # Call `sanitize()` when a new implementation is defined.
            cls = type.__new__(mcls, name, bases, members)
            try:
                cls.sanitize()
            except:
                # Make sure the implementation can never be used.
                cls.__module__ = None
                raise
            return cls

        def __repr__(cls):
            return "%s.%s" % (cls.__module__, cls.__name__)

    @classmethod
    def sanitize(cls):
        """
        This method is called when a new interface or implementation class is
        created.  Specific interfaces may override this method to check that
        implementations satisfy the constraints imposed by the interface.
        """

    @classmethod
    def enabled(cls):
        """
        Returns ``True`` for complete implementations; ``False`` for abstract
        and mixin classes.  Specific interfaces and implementations may
        override this method.
        """
        return (cls is not Extension)

    @classmethod
    @cached
    def package(cls):
        """
        Returns the package in which the extension was declared.
        """
        packages = get_packages()
        return packages.modules.get(cls.__module__)

    @classmethod
    @cached
    def all(cls, package=None):
        """
        Returns a list of all implementations for the given interface.

        `package`: :class:`Package`, ``str`` or ``None``
            If provided, the function returns implementations defined
            in the given package.
        """
        # Determine modules that may contain extensions.
        if package is None:
            package = get_packages()
        elif not isinstance(package, Package):
            package = get_packages()[package]
        modules = package.modules
        # Find all subclasses of `cls`.
        subclasses = [cls]
        # Used to weed out duplicates (due to diamond inheritance).
        seen = set([cls])
        idx = 0
        while idx < len(subclasses):
            for subclass in subclasses[idx].__subclasses__():
                if subclass not in seen:
                    subclasses.append(subclass)
                    seen.add(subclass)
            idx += 1
        # Filter out abstract classes and implementations not included
        # with the active application; return the rest.
        return [subclass for subclass in subclasses
                         if subclass.__module__ in modules and
                            subclass.enabled()]

    @classmethod
    @cached
    def top(cls, package=None):
        """
        Returns the most specific implementation for the given interface.

        The most specific implementation must be a subclass of all the other
        implementations of the same interface.

        `package`: :class:`Package`, ``str`` or ``None``
            If provided, consider only implementations defined in
            the given package.
        """
        extensions = cls.all(package)
        # Find all the leaves in the inheritance tree.
        candidates = []
        for extension in extensions:
            if not any(issubclass(candidate, extension)
                       for candidate in candidates):
                candidates = [candidate for candidate in candidates
                                        if not issubclass(extension, candidate)]
                candidates.append(extension)
        # Ensure there is no more than one leaf and return it.
        assert len(candidates) <= 1, "too many implementations found: %s" \
                % ", ".join(repr(candidate) for candidate in candidates)
        if candidates:
            return candidates[0]

    @classmethod
    def by_package(cls, package):
        # Deprecated.
        return cls.all(package)

    @classmethod
    def signature(cls):
        """
        Returns a (unique) identifier of the implementation.
        """
        raise NotImplementedError("%s.signature()" % cls)

    @classmethod
    @cached
    def mapped(cls, package=None):
        """
        Returns a dictionary mapping extension signatures to extensions.
        """
        mapping = {}
        for extension in cls.all(package):
            signature = extension.signature()
            assert signature not in mapping, \
                    "%s and %s have identical signatures: %r" \
                    % (mapping[signature], extension, signature)
            mapping[signature] = extension
        return mapping

    #: Sorting weight or signature of the implementation.
    priority = None
    #: Signature of implementation that should follow the given implementation.
    after = None
    #: Signature of implementation that should preceed the given implementation.
    before = None

    @classmethod
    @cached
    def ordered(cls, package=None):
        """
        Returns implementations in the order that respects ``priority``,
        ``after`` and ``before`` attributes.
        """
        extensions = cls.all(package)
        # Extract signatures and weights from `priority`.
        signatures = {}
        weights = {}
        for extension in extensions:
            priority = extension.priority
            if priority:
                if not isinstance(priority, list):
                    priority = [priority]
                for signature_or_weight in priority:
                    if isinstance(signature_or_weight, (int, float)):
                        weights[extension] = signature_or_weight
                    else:
                        signatures[signature_or_weight] = extension
        # Generate a partial order relationship from weights.
        order = {}
        for extension in extensions:
            order[extension] = []
            weight = weights.get(extension, None)
            if weight is not None:
                order[extension] = [other for other in extensions
                                    if other in weights and
                                       weights[other] < weight]
        # Add `after` and `before` conditions.
        for extension in extensions:
            for others in (extension.after, extension.before):
                if not others:
                    continue
                for other in (others if isinstance(others, list) else [others]):
                    if isinstance(other, str):
                        other = signatures.get(other)
                    if other in extensions:
                        if others is extension.after:
                            order[extension].append(other)
                        else:
                            order[other].append(extension)
        # Sort the extensions.
        return toposort(extensions, order)


def toposort(elements, order):
    # Sorts elements with respect to the given order.

    # The sorted list.
    ordered = []
    # The set of nodes which the DFS has already processed.
    visited = set()
    # The set of nodes currently being processed by the DFS.
    active = set()
    # The path to the current node.  Note that `set(path) == active`.
    path = []

    # Implements the depth-first search.
    def dfs(node):
        # Check if the node has already been processed.
        if node in visited:
            return

        # Update the path; check for cycles.
        path.append(node)
        assert node not in active, \
                "order has cycles: %s" % path[path.index(node):]
        active.add(node)

        # Visit the adjacent nodes.
        adjacents = order[node]
        for adjacent in adjacents:
            dfs(adjacent)

        # Check that the order is total.
        assert not ordered or ordered[-1] in adjacents, \
                "order is not total: %s" % [ordered[-1], node]

        # Add the node to the sorted list.
        ordered.append(node)

        # Remove the node from the path; add it to the set of processed nodes.
        path.pop()
        active.remove(node)
        visited.add(node)

    # Apply the DFS to the whole DAG.
    for element in elements:
        dfs(element)

    # Break the cycle created by a recursive nested function.
    dfs = None

    return ordered


