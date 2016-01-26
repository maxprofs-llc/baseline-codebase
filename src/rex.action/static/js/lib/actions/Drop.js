/**
 * @copyright 2015, Prometheus Research, LL);
 */

import React from 'react';

import {VBox, HBox} from 'rex-widget/layout';
import {forceRefreshData} from 'rex-widget/data';
import * as Stylesheet from 'rex-widget/stylesheet';
import * as ui from 'rex-widget/ui';
import * as CSS from 'rex-widget/css';

import Title from './Title';
import {command, Types} from '../execution/Command';
import {getEntityTitle} from '../Entity';

let stylesheet = Stylesheet.create({
  Root: {
    Component: VBox,
    flex: 1,
    background: CSS.rgba(255, 226, 226, 0.4),
    color: CSS.rgb(68, 22, 22),
  },

  Header: {
    Component: HBox,
    padding: 10,
  },

  Content: {
    Component: VBox,
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 10,
  },

  Title: {
    Component: VBox,
    flex: 1,
  },

  MessageBottom: {
    marginTop: 10,
    fontSize: '90%',
  },

  Message: {
    fontSize: '90%',
  }
});

export default class Drop extends React.Component {

  static defaultProps = {
    width: 400,
    icon: 'remove',
    confirmDelay: 3,
    kind: 'danger',
  };

  constructor(props) {
    super(props);
    this.state = {
      confirmDelay: this.props.confirmDelay
    };
  }

  render() {
    let {width, message, entity, onClose, context} = this.props;
    let {confirmDelay} = this.state;
    let title = this.constructor.renderTitle(this.props, context);
    return (
      <stylesheet.Root>
        {title &&
          <stylesheet.Header>
            <stylesheet.Title>
              <h4>
                {title}
              </h4>
            </stylesheet.Title>
            {onClose &&
              <ui.QuietButton
                icon="remove"
                onClick={onClose}
                />}
          </stylesheet.Header>}
        <stylesheet.Content>
          <stylesheet.Message>
            <div dangerouslySetInnerHTML={{__html: message}} />
          </stylesheet.Message>
          <ui.DangerButton
            onClick={this.drop}
            disabled={confirmDelay > 0}
            icon="remove">
            Drop
          </ui.DangerButton>
          <stylesheet.MessageBottom>
            {confirmDelay > 0 ?
              <p>
                Wait {confirmDelay} seconds
              </p> :
              <p>
                Press button above to drop {entity.name}
              </p>}
          </stylesheet.MessageBottom>
        </stylesheet.Content>
      </stylesheet.Root>
    );
  }

  componentDidMount() {
    this._countdown = setInterval(this.countdown, 1000);
  }

  componentWillUnmount() {
    clearTimeout(this._countdown);
  }

  drop = () => {
    let {entity: {name, type}, context, onCommand, onClose} = this.props;
    let entity = context[name];
    this.props.data.delete({[type.name]: {id: entity.id}}).then(() => {
      this.props.onEntityUpdate(entity, null);
      forceRefreshData();
    });
  }

  countdown = () => {
    let confirmDelay = this.state.confirmDelay - 1;
    if (confirmDelay === 0) {
      clearTimeout(this._countdown);
    }
    this.setState({confirmDelay});
  }

  static renderTitle({entity, title = `Drop ${entity.name}`}, context) {
    return <Title title={title} context={context} entity={entity} />;
  }

  static getTitle(props) {
    return props.title || `Drop ${props.entity.name}`;
  }
}
