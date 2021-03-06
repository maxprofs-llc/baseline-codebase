/**
 * @flow
 */

import * as React from "react";
import { style, HBox, VBox } from "react-stylesheet";
import Label from "../ui/Label";
import * as Icon from "../ui/Icon";

type QueryVisButtonHeaderStylesheet = {
  Root: React.ComponentType<*>,
  Button: React.ComponentType<*>
};

type QueryVisButtonHeaderProps = {
  stylesheet: QueryVisButtonHeaderStylesheet,
  closeIcon?: React.Node,

  label?: React.Node,

  selected?: boolean,
  selectable?: boolean,

  invalid?: boolean,

  toggleable?: boolean,
  closeable?: boolean,

  first?: boolean,

  closeTitle?: string,

  onSelect?: () => void,
  onClose?: () => void
};

type QueryVisButtonHeaderState = {
  active: boolean,
  hover: boolean
};

export default class QueryVisButtonHeader extends React.Component<
  QueryVisButtonHeaderProps,
  QueryVisButtonHeaderState
> {
  state = {
    active: true,
    hover: false
  };

  static defaultProps = {
    closeIcon: <Icon.IconRemove />
  };

  onMouseEnter = () => {
    this.setState({ hover: true });
  };

  onMouseLeave = () => {
    this.setState({ hover: false });
  };

  toggleActive = (e: UIEvent) => {
    e.stopPropagation();
    let active = !this.state.active;
    this.setState({ active });
  };

  onSelect = (e: UIEvent) => {
    e.stopPropagation();
    if (this.props.onSelect != null) {
      this.props.onSelect();
    }
  };

  onClose = (e: UIEvent) => {
    e.stopPropagation();
    if (this.props.onClose != null) {
      this.props.onClose();
    }
  };

  render() {
    let {
      label,
      selected,
      invalid,
      selectable,
      toggleable,
      closeable,
      closeIcon,
      closeTitle,
      first,
      stylesheet: { Root, Button }
    } = this.props;
    let { active, hover } = this.state;

    let buttonLabel = (
      <QueryVisButtonLabel>
        <HBox flexGrow={1} flexShrink={1} alignItems="center">
          <VBox
            paddingRight={5}
            style={{
              visibility:
                toggleable && (!active || selected || hover)
                  ? "visible"
                  : "hidden"
            }}
          >
            <Button disableActive onClick={toggleable && this.toggleActive}>
              {active ? <Icon.IconCircle /> : <Icon.IconCircleO />}
            </Button>
          </VBox>
          <HBox flexGrow={1} flexShrink={1}>
            <Label label={label} />
          </HBox>
          {closeable && (
            <HBox
              style={{ visibility: selected || hover ? "visible" : "hidden" }}
            >
              <Button onClick={this.onClose} title={closeTitle}>
                {closeIcon}
              </Button>
            </HBox>
          )}
        </HBox>
      </QueryVisButtonLabel>
    );

    return (
      <Root
        first={first}
        variant={{ selected, invalid }}
        onClick={selectable && this.onSelect}
        onMouseOver={this.onMouseEnter}
        onMouseLeave={this.onMouseLeave}
      >
        {buttonLabel}
      </Root>
    );
  }
}

export let QueryVisButtonLabel = style(HBox, {
  displayName: "QueryVisButtonLabel",
  base: {
    //textTransform: 'capitalize',
    userSelect: "none",
    cursor: "default",
    fontSize: "9pt",
    fontWeight: 400,
    padding: 6,
    width: "100%",
    height: 32
  }
});
