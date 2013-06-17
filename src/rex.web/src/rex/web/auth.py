#
# Copyright (c) 2013, Prometheus Research, LLC
#


from rex.core import Extension, cached


class Authenticate(Extension):
    """
    Authentication interface.

    Authentication is a mechanism for finding the user who initiated the HTTP
    request.  The default implementation returns the value of CGI variable
    ``REMOTE_USER``, but most applications are expected to provide a custom
    implementation.
    """

    def __call__(self, req):
        """
        Returns the user who performed the request or ``None``.

        Implementations should override this method.
        """
        return req.remote_user


class Authorize(Extension):
    """
    Authorization interface.

    Authorization is mechanism for checking whether the request has enough
    permission to execute some action.

    The following permissions are predefined:

    *authenticated*
        Granted when the request is authenticated.
    *anybody*
        Always granted.
    *nobody*
        Never granted.

    An application can define additional permissions by implementing this
    interface.
    """

    #: Permission name.
    access = None

    @classmethod
    @cached
    def map_all(cls):
        """
        Returns a dictionary mapping the permission name to the respective
        :class:`Authorize` subclass.
        """
        mapping = {}
        for extension in cls.all():
            assert extension.access not in mapping, \
                    "duplicate permission: %r" % extension.access
            mapping[extension.access] = extension
        return mapping

    @classmethod
    def enabled(cls):
        # Whether it is a complete implementation.
        return (cls.access is not None)

    def __call__(self, req):
        """
        Returns ``True`` if the request has the respective permission;
        ``False`` otherwise.

        Implementations must override this method.
        """
        raise NotImplementedError("%s.__call__()" % self.__class__.__name__)


class AuthorizeAuthenticated(Authorize):
    # This permission is granted if the request is authenticated.

    access = 'authenticated'

    def __call__(self, req):
        return (authenticate(req) is not None)


class AuthorizeAnybody(Authorize):
    # This permission is always granted.

    access = 'anybody'

    def __call__(self, req):
        return True


class AuthorizeNobody(Authorize):
    # This permission is never granted.

    access = 'nobody'

    def __call__(self, req):
        return False


def authenticate(req):
    """
    Returns the user who performed the request or ``None``.
    """
    # Since authentication could be expensive (e.g. database access),
    # we cache the result in `environ['rex.user']`.
    if 'rex.user' not in req.environ:
        auth_type = Authenticate.top()
        req.environ['rex.user'] = auth_type()(req)
    return req.environ['rex.user']


def authorize(req, access):
    """
    Returns whether the request has the given permission.
    """
    # Since authorization could be expensive (e.g. database access),
    # we cache the result in `environ['rex.access']`.
    if 'rex.access' not in req.environ:
        req.environ['rex.access'] = {}
    if access not in req.environ['rex.access']:
        auth_type_map = Authorize.map_all()
        assert access in auth_type_map, "undefined permission %r" % access
        auth_type = auth_type_map[access]
        req.environ['rex.access'][access] = auth_type()(req)
    return req.environ['rex.access'][access]


