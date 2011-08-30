#
# Copyright (c) 2006-2011, Prometheus Research, LLC
# See `LICENSE` for license information, `AUTHORS` for the list of authors.
#


from htsql.context import context
from htsql.tr.encode import EncodeSegment
from htsql.tr.flow import OrderedFlow


class AutolimitEncodeSegment(EncodeSegment):

    def __call__(self):
        code = super(AutolimitEncodeSegment, self).__call__()
        limit = context.app.tweak.autolimit.limit
        if limit is None:
            return code
        flow = code.flow
        while isinstance(flow, OrderedFlow):
            if flow.limit is not None and flow.limit < limit:
                return code
            flow = flow.base
        flow = OrderedFlow(code.flow, [], limit, None, code.binding)
        return code.clone(flow=flow)


