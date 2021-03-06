

from rex.web import HandleError as BaseHandleError
from rex.widget import Widget, Field, render_widget
from rex.core import StrVal, UIntVal, get_settings
from webob import Response


class Error(Widget):

    name = 'Error'
    js_type = 'rex-widget-chrome', 'Error'

    code = Field(UIntVal())
    title = Field(StrVal())
    explanation = Field(StrVal())
    url = Field(StrVal())



class HandleError(BaseHandleError):

    code = '*'

    def widget(self, req):
        explanation = '%s\n\n%s' % (self.error.explanation,
                                    self.error.message or '')
        return Error(code=self.error.code,
                     title=self.error.title,
                     explanation=explanation,
                     url=req.url)

    def __call__(self, req):
        accept = req.headers.get('Accept')
        if accept == 'application/json' and self.error.json:
            return self.error
        response = render_widget(self.widget(req), req)
        response.status = self.error.code
        return response



