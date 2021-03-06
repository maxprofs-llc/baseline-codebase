/**
 * @copyright 2016, Prometheus Research, LLC
 */

import * as React from "react";
import * as ReactForms from "react-forms/reactive";
import * as ReactUI from "@prometheusresearch/react-ui-0.21";
import { style } from "@prometheusresearch/react-ui-0.21/stylesheet";
import { primitiveValueStrategy } from "@prometheusresearch/react-ui-0.21/src/CheckboxGroupBase";
import { map } from "lodash";

import Widget from "../Widget";
import * as FormContext from "../FormContext";
import OptionLabel from "../OptionLabel";
import Help from "../Help";
import * as Hotkey from "./HotKey";

let CheckboxInput = style(ReactUI.Checkbox, {
  Label: {
    fontSize: null,
    disabled: {
      color: "#aaa",
    },
  },
  LabelWrapper: {
    maxWidth: "90%",
  },
});

let CheckboxGroupInput = style(ReactUI.CheckboxGroup, {
  Checkbox: props => <CheckboxInput {...props} />,
});

let valueStrategy = {
  ...primitiveValueStrategy,

  update(value, option, checked) {
    let nextValue = primitiveValueStrategy.update(value, option, checked);
    if (nextValue.length === 0) {
      nextValue = null;
    }
    return nextValue;
  },
};

export default ReactForms.reactive(
  class CheckGroup extends React.Component {
    static contextTypes = {
      ...FormContext.contextTypes,
    };

    render() {
      let {
        formValue,
        options: { orientation = "vertical" },
        instrument: { type },
        form: { eventKey },
        question: { fieldId, enumerations },
        editable,
        onCommitEdit,
        onCancelEdit,
        ...props
      } = this.props;
      let { event } = this.context;

      let options;
      if (enumerations) {
        options = map(enumerations, enumeration => ({
          value: enumeration.id,
          label: (
            <OptionLabel text={enumeration.text} audio={enumeration.audio} />
          ),
          hint: enumeration.help && <Help>{enumeration.help}</Help>,
        }));
      } else {
        options = Object.keys(type.enumerations)
          .sort()
          .map(enumeration => {
            return {
              value: enumeration,
              label: enumeration,
            };
          });
      }

      if (event) {
        let hidden = event.hiddenEnumerations(eventKey);
        options = options.filter(
          enumeration => hidden.indexOf(enumeration.value) === -1,
        );
      }

      let keys = {};
      if (options.length <= 10) {
        let hotkeys = Hotkey.hotkeysFromOptions(options, this.props.options);
        keys = {
          ...Hotkey.configureHotkeys(hotkeys),
          Tab: "Tab",
        };

        if (hotkeys) {
          options = options.map(option => {
            if (hotkeys[option.value]) {
              let label = (
                <span>
                  <ReactUI.LabelText style={{ unicodeBidi: "isolate" }}>
                    [{hotkeys[option.value]}]
                  </ReactUI.LabelText>{" "}
                  {option.label}
                </span>
              );
              return {
                ...option,
                label,
              };
            } else {
              return option;
            }
          });
        }
      }

      return (
        <Hotkey.EditHotKeyHandler
          editable={editable}
          onCommitEdit={onCommitEdit}
          onCancelEdit={onCancelEdit}
        >
          <Hotkey.HotkeyHandler keys={keys} onKey={this.onKey}>
            <Widget {...props} formValue={formValue} padding="x-small">
              <CheckboxGroupInput
                layout={orientation}
                valueStrategy={valueStrategy}
                options={options}
              />
            </Widget>
          </Hotkey.HotkeyHandler>
        </Hotkey.EditHotKeyHandler>
      );
    }

    onKey = key => {
      let value = this.props.formValue.value || [];
      value = value.slice(0);
      let idx = value.indexOf(key.value);
      if (idx === -1) {
        value.push(key.value);
      } else {
        value.splice(idx, 1);
      }
      if (value.length === 0) {
        value = null;
      }
      this.props.formValue.update(value);
    };
  },
);
