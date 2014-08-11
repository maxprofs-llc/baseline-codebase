#
# Copyright (c) 2014, Prometheus Research, LLC
#


from rex.core import Extension, get_settings

from ..mixins import Comparable, Displayable, Dictable
from ..util import to_unicode


__all__ = (
    'User',
)


class User(Extension, Comparable, Displayable, Dictable):
    """
    Represents the person who is engaging with the application in order to
    provide responses for Instruments. The User may or may not be the Subject
    of an Instrument.
    """

    dict_properties = (
        'login',
    )

    @classmethod
    def get_by_uid(cls, uid, user=None):
        """
        Retrieves a User from the datastore using its UID.

        Must be implemented by concrete classes.

        :param uid: the UID of the User to retrieve
        :type uid: string
        :param user: the User who should have access to the desired User
        :type user: User
        :raises:
            DataStoreError if there was an error reading from the datastore
        :returns:
            the specified User; None if the specified UID does not exist
        :rtype: User
        """

        raise NotImplementedError()

    @classmethod
    def get_by_login(cls, login, user=None):
        """
        Retrieves a User from the datastore using its login username.

        Must be implemented by concrete classes.

        :param login: the login username of the User to retrieve
        :type login: string
        :param user: the User who should have access to the desired User
        :type user: User
        :raises:
            DataStoreError if there was an error reading from the datastore
        :returns:
            the specified User; None if the specified login does not exist
        :rtype: User
        """

        raise NotImplementedError()

    @classmethod
    def find(cls, offset=0, limit=100, user=None, **search_criteria):
        """
        Returns Users that match the specified criteria.

        Must be implemented by concrete classes.

        :param offset:
            the offset in the list of Users to start the return set from
            (useful for pagination purposes)
        :type offset: int
        :param limit:
            the maximum number of Users to return (useful for pagination
            purposes)
        :type limit: int
        :param user: the User who should have access to the desired Users
        :type user: User
        :raises:
            DataStoreError if there was an error reading from the datastore
        :rtype: list of Users
        """

        raise NotImplementedError()

    def __init__(self, uid, login):
        self._uid = to_unicode(uid)
        self._login = to_unicode(login)

    @property
    def uid(self):
        """
        The Unique Identifier that represents this User in the datastore.
        Read only.

        :rtype: unicode
        """

        return self._uid

    @property
    def login(self):
        """
        The (unique) login username that is assigned to this user. Read only.

        :rtype: unicode
        """

        return self._login

    def _get_implementation(self, package_name, object_name):
        setting = getattr(
            get_settings(),
            '%s_implementation' % package_name.lower(),
        )
        impl = getattr(setting, object_name.lower())
        return impl

    def get_object_by_uid(self, uid, object_name, package_name='instrument'):
        """
        Retrieves an interface object using its UID, if this User has access to
        it. Essentially acts as a proxy to the object's get_by_uid() method.

        :param uid: the UID of the object to retrieve
        :type uid: string
        :param object_name:
            the name of the interface object to retrieve (e.g., "subject",
            "instrument", "instrumentversion", "assessment", etc)
        :type object_name: string
        :param package_name:
            the package alias the interface object is defined in; if not
            specified, defaults to "instrument"
        :type package_name: string
        :raises:
            DataStoreError if there was an error reading from the datastore
        :returns:
            the object matching the UID if this User has access to it;
            otherwise None
        """

        impl = self._get_implementation(package_name, object_name)
        return impl.get_by_uid(uid, user=self)

    def find_objects(self, object_name, package_name='instrument', **kwargs):
        """
        Retrieves interface objects that match the specified criteria that this
        User has access to. Essentially acts as a proxy to the object's find()
        method.

        :param object_name:
            the name of the interface object to retrieve (e.g., "subject",
            "instrument", "instrumentversion", "assessment", etc)
        :type object_name: string
        :param package_name:
            the package alias the interface object is defined in; if not
            specified, defaults to "instrument"
        :type package_name: string
        :raises:
            DataStoreError if there was an error reading from the datastore
        :returns: list of interface objects
        """

        impl = self._get_implementation(package_name, object_name)
        return impl.find(user=self, **kwargs)

    def get_display_name(self):
        """
        Returns a unicode string that represents this object, suitable for use
        in human-visible places.

        :rtype: unicode
        """

        return self.login

    def __repr__(self):
        return '%s(%r, %r)' % (
            self.__class__.__name__,
            self.uid,
            self.login,
        )

