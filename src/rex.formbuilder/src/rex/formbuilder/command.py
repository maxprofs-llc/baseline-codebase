import simplejson

from rexrunner.response import BadRequestError
from rexrunner.registry import register_command

#from rex.forms.command import RoadsCommand
from rexrunner.command import Command
from webob import Response

class FormBuilderBaseCommand(Command):

    def __init__(self, parent):
        super(FormBuilderBaseCommand, self).__init__(parent)
        self.handler = self.parent.app.handler_by_name['rex.formbuilder']

@register_command
class FormList(FormBuilderBaseCommand):

    name = '/instrument_list'

    def render(self, req):
        # self.set_handler()
        res = self.handler.get_list_of_forms()
        return Response(body=simplejson.dumps(res))


@register_command
class LoadForm(FormBuilderBaseCommand):

    name = '/load_instrument'

    def render(self, req):
        # self.set_handler()
        code = req.GET.get('code')
        if not code:
            return Response(status='401', body='Code not provided')
        form, _ = self.handler.get_latest_instrument(code)
        if not form:
            return Response(body='Form not found')
        return Response(body=form)

@register_command
class RoadsBuilder(FormBuilderBaseCommand):

    name = '/builder'

    def render(self, req):
        # self.set_handler()

        instrument = req.GET.get('instrument')
        if not instrument:
            return Response(status='401', body='Instrument ID is not provided')
        (code, _) = self.handler.get_latest_instrument(instrument)
        code = simplejson.loads(code)
        # if not form:
        #    return Response(body='Form not found')

        args = {
            'instrument': instrument,
            'code': code,
            'req': req,
            'manual_edit_conditions': self.app.config.manual_edit_conditions
        }

        return self.render_to_response('/roadsbuilder.html', **args)
