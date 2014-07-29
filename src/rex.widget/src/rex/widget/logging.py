"""

    rex.widget.state.graph
    ======================

    :copyright: 2014, Prometheus Research, LLC

"""

from __future__ import absolute_import

import logging

def getLogger(name):
    """ Get logger which has class:`logging.NullHandler` added."""
    log = logging.getLogger(name)
    log.addHandler(logging.NullHandler())
    return log
