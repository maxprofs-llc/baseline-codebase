#
# Copyright (c) 2016, Prometheus Research, LLC
#

import json

from webob.exc import HTTPBadRequest

from rex.action import typing
from rex.core import BoolVal
from rex.forms.util import preview_calculation_results
from rex.instrument import Entry, InstrumentError, CalculationSet, ResultSet
from rex.widget import Field, responder, RequestURL

from .assessment_base import AssessmentAction


__all__ = (
    'EditAssessmentAction',
)


class EditAssessmentAction(AssessmentAction):
    name = 'assessment-edit'
    js_type = 'rex-acquire-actions', 'EditAssessment'

    entity = Field(
        typing.RowTypeVal(),
        doc='The record containing the Assessment.',
    )

    show_calculations = Field(
        BoolVal(),
        default=True,
        doc='Whether or not to allow calculation previews.',
    )

    def context(self):
        return (
            self.domain.record(self.entity),
            self.domain.record(),
        )

    @responder(url_type=RequestURL)
    def save_assessment(self, request):
        assessment_id = request.json.get('assessment_id')
        assessment_data = request.json.get('data')
        if not assessment_id or not assessment_data:
            raise HTTPBadRequest(
                'Must specify both assessment_id and data',
            )

        user = self.get_user(request)
        assessment = user.get_object_by_uid(assessment_id, 'assessment')
        if not assessment:
            raise HTTPBadRequest(
                'Specified assessment_id does not exist'
            )

        # Validate the data
        entry_impl = Entry.get_implementation()
        try:
            entry_impl.validate_data(
                assessment_data,
                instrument_definition=assessment.instrument_version.definition,
            )
        except InstrumentError as exc:
            raise HTTPBadRequest(exc.message)

        # Create the Entry
        entry = entry_impl.create(
            assessment,
            entry_impl.TYPE_REVISION,
            user.login,
            data=assessment_data,
            status=entry_impl.STATUS_COMPLETE,
        )

        # Update the Assessment
        assessment.data = entry.data
        assessment.set_application_token('rex.acquire_actions')

        # Execute the CalculationSet
        calculationset = CalculationSet.get_implementation().find(
            instrument_version=assessment.instrument_version.uid,
            limit=1
        )
        if calculationset:
            results = calculationset[0].execute(assessment=assessment)
            assessment.set_meta('calculations', results)
            ResultSet.get_implementation().create(assessment, results)

        assessment.save()

        response = {
            'status': 'SUCCESS',
        }

        return self.response_as_json(response)

    @responder(url_type=RequestURL)
    def execute_calculations(self, request):
        assessment_id = request.GET.get('assessment_id')
        assessment_data = request.POST.get('data')
        if not assessment_id or not assessment_data:
            raise HTTPBadRequest(
                'Must specify both assessment_id and data',
            )

        user = self.get_user(request)
        assessment = user.get_object_by_uid(assessment_id, 'assessment')
        if not assessment:
            raise HTTPBadRequest(
                'Specified assessment_id does not exist'
            )

        try:
            assessment_data = json.loads(assessment_data)
        except ValueError as exc:
            raise HTTPBadRequest(exc.message)

        data = {}
        data['results'] = preview_calculation_results(
            assessment.instrument_version,
            assessment.instrument_version.calculation_set,
            assessment_data,
            assessment=assessment,
        )

        return self.response_as_json(data)

