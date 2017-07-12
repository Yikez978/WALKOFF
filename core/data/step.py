from xml.etree import ElementTree
from collections import namedtuple
from collections import namedtuple
from core.executionelement import ExecutionElement
from core.helpers import (get_app_action_api, InvalidElementConstructed, inputs_xml_to_dict, inputs_to_xml)
from core import nextstep
from core.validator import validate_app_action_parameters
from apps import get_app_action
from core.data.nextStep import NextStepData
_Widget = namedtuple('Widget', ['app', 'widget'])

class StepData(ExecutionElement):
    def __init__(self, xml=None, name='', action='', app='', device='', inputs=None, next_steps=None, parent_name='',
                 position=None, ancestry=None, widgets=None, risk=0):
        ExecutionElement.__init__(self, name=name, parent_name=parent_name, ancestry=ancestry)
        if xml is not None:
            self._from_xml(xml, parent_name=parent_name, ancestry=ancestry)
        else:
            if action == '' or app == '':
                raise InvalidElementConstructed('Either both action and app or xml must be '
                                                'specified in step constructor')
            self.action = action
            self.app = app
            self.run, self.input_api = get_app_action_api(self.app, self.action)
            get_app_action(self.app, self.run)
            inputs = inputs if inputs is not None else {}
            self.input = validate_app_action_parameters(self.input_api, inputs, self.app, self.action)
            self.device = device
            self.risk = risk
            self.conditionals = next_steps if next_steps is not None else []
            self.position = position if position is not None else {}
            self.widgets = [_Widget(widget_app, widget_name)
                            for (widget_app, widget_name) in widgets] if widgets is not None else []
            self.raw_xml = self.to_xml()
            self.templated = False
        self.output = None
        self.next_up = None

    def _from_xml(self, step_xml, parent_name='', ancestry=None):
        self.raw_xml = step_xml
        name = step_xml.get('id')
        ExecutionElement.__init__(self, name=name, parent_name=parent_name, ancestry=ancestry)

        self.action = step_xml.find('action').text
        self.app = step_xml.find('app').text
        self.run, self.input_api = get_app_action_api(self.app, self.action)
        is_templated_xml = step_xml.find('templated')
        self.templated = is_templated_xml is not None and bool(is_templated_xml.text)
        get_app_action(self.app, self.run)
        input_xml = step_xml.find('inputs')
        if input_xml is not None:
            inputs = inputs_xml_to_dict(input_xml) or {}
            if not self.templated:
                self.input = validate_app_action_parameters(self.input_api, inputs, self.app, self.action)
            else:
                self.input = inputs
        else:
            self.input = validate_app_action_parameters(self.input_api, {}, self.app, self.action)
        device_field = step_xml.find('device')
        self.device = device_field.text if device_field is not None else ''
        risk_field = step_xml.find('risk')
        self.risk = risk_field.text if risk_field is not None else 0
        self.conditionals = [nextstep.NextStep(xml=next_step_element, parent_name=self.name, ancestry=self.ancestry)
                             for next_step_element in step_xml.findall('next')]
        self.widgets = [_Widget(widget.get('app'), widget.text) for widget in step_xml.findall('widgets/*')]
        position = step_xml.find('position')
        if position is None:
            self.position = {}
        else:
            x_position = position.find('x')
            y_position = position.find('y')
            if x_position is not None and y_position is not None:
                self.position = {'x': x_position.text, 'y': y_position.text}
            else:
                self.position = {}

    def _update_xml(self, step_xml):
        self.action = step_xml.find('action').text
        self.app = step_xml.find('app').text
        device_field = step_xml.find('device')
        self.device = device_field.text if device_field is not None else ''
        risk_field = step_xml.find('risk')
        self.risk = risk_field.text if risk_field is not None else 0
        input_xml = step_xml.find('inputs')
        if input_xml is not None:
            inputs = inputs_xml_to_dict(input_xml) or {}
            if not self.templated:
                self.input = validate_app_action_parameters(self.input_api, inputs, self.app, self.action)
            else:
                self.input = inputs
        else:
            self.input = validate_app_action_parameters(self.input_api, {}, self.app, self.action)
        self.conditionals = [nextstep.NextStep(xml=next_step_element, parent_name=self.name, ancestry=self.ancestry)
                             for next_step_element in step_xml.findall('next')]

    def to_xml(self, *args):
        """Converts the Step object to XML format.

        Returns:
            The XML representation of the Step object.
        """
        step = ElementTree.Element('step')
        step.set("id", self.name)

        element_id = ElementTree.SubElement(step, 'name')
        element_id.text = self.name

        app = ElementTree.SubElement(step, 'app')
        app.text = self.app

        action = ElementTree.SubElement(step, 'action')
        action.text = self.action

        if self.risk:
            risk = ElementTree.SubElement(step, 'risk')
            risk.text = self.risk

        if self.device:
            device = ElementTree.SubElement(step, 'device')
            device.text = self.device

        if self.position and 'x' in self.position and 'y' in self.position:
            position = ElementTree.SubElement(step, 'position')
            x_position = ElementTree.SubElement(position, 'x')
            x_position.text = str(self.position['x'])
            y_position = ElementTree.SubElement(position, 'y')
            y_position.text = str(self.position['y'])

        if self.input:
            args = inputs_to_xml(self.input)
            step.append(args)

        if self.widgets:
            widgets = ElementTree.SubElement(step, 'widgets')
            for widget in self.widgets:
                widget_xml = ElementTree.SubElement(widgets, 'widget')
                widget_xml.text = widget.widget
                widget_xml.set('app', widget.app)

        for next_step in self.conditionals:
            next_xml = next_step.to_xml()
            if next_xml is not None:
                step.append(next_step.to_xml())

        return step

    def as_json(self, with_children=True):
        """Gets the JSON representation of a Step object.

        Args:
            with_children (bool, optional): A boolean to determine whether or not the children elements of the Step
                object should be included in the output.

        Returns:
            The JSON representation of a Step object.
        """
        output = {"name": str(self.name),
                  "action": str(self.action),
                  "app": str(self.app),
                  "device": str(self.device),
                  "risk": self.risk,
                  "input": self.input,
                  'widgets': [{'app': widget.app, 'name': widget.widget} for widget in self.widgets],
                  "position": self.position}
        if self.output:
            output["output"] = str(self.output)
        if with_children:
            output["next"] = [next_step.as_json() for next_step in self.conditionals if next_step.name is not None]
        else:
            output["next"] = [next_step.name for next_step in self.conditionals if next_step.name is not None]
        return output

    @staticmethod
    def from_json(json_in, position, parent_name='', ancestry=None):
        """Forms a Step object from the provided JSON object.

        Args:
            json_in (dict): The JSON object to convert from.
            position (dict): position of the step node of the form {'x': <x position>, 'y': <y position>}
            parent_name (str, optional): The name of the parent for ancestry purposes. Defaults to an empty string.
            ancestry (list[str], optional): The ancestry for the new Step object. Defaults to None.

        Returns:
            The Step object parsed from the JSON object.
        """
        device = json_in['device'] if ('device' in json_in
                                       and json_in['device'] is not None
                                       and json_in['device'] != 'None') else ''
        risk = json_in['risk'] if 'risk' in json_in else 0
        widgets = []
        if 'widgets' in json_in:
            widgets = [(widget['app'], widget['name'])
                       for widget in json_in['widgets'] if ('app' in widget and 'name' in widget)]
        step = StepData(name=json_in['name'],
                    action=json_in['action'],
                    app=json_in['app'],
                    device=device,
                    risk=risk,
                    inputs=json_in['input'],
                    parent_name=parent_name,
                    position={key: str(value) for key, value in position.items()},
                    widgets=widgets,
                    ancestry=ancestry)
        if json_in['next']:
            step.conditionals = [NextStepData.from_json(next_step, parent_name=step.name, ancestry=step.ancestry)
                                 for next_step in json_in['next'] if next_step]
        return step