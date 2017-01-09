/**
 * @flow
 */

import type {QueryNavigation, Context} from '../model';
import type {SearchCallback} from './Search';

import React from 'react';
import {VBox, Element} from 'react-stylesheet';
import * as ReactUI from '@prometheusresearch/react-ui';

import * as qn from '../model/QueryNavigation';
import {dummySearch, runSearch} from './Search';
import LoadingIndicator from './LoadingIndicator';

type NavigationMenuProps = {
  context: Context;
  onSearch: SearchCallback;
  children?: React.Element<*>;
};

export default class NavigationMenu extends React.Component<*, NavigationMenuProps, *> {

  static defaultProps = {
    onSearch: dummySearch,
  };

  state: {
    searchTerm: ?string;
    searchInProgress: boolean;
    navigation: Map<string, QueryNavigation>;
  };

  mounted: boolean;

  constructor(props: NavigationMenuProps) {
    super(props);
    let {context} = props;
    this.state = {
      searchTerm: null,
      searchInProgress: false,
      navigation: qn.getNavigation(context),
    };
    this.mounted = false;
  }

  componentWillMount() {
    this.mounted = true;
  }

  componentWillUnmount() {
    this.mounted = false;
  }

  componentWillReceiveProps(nextProps: NavigationMenuProps) {
    if (nextProps.context !== this.props.context) {
      this.setState({
        searchTerm: null,
        searchInProgress: false,
        navigation: qn.getNavigation(nextProps.context),
      });
    }
  }

  onSearchTerm = (e: UIEvent) => {
    let target: {value: string} = (e.target: any);
    let searchTerm = target.value === '' ? null : target.value;
    let navigation = qn.getNavigation(this.props.context);
    if (searchTerm != null) {
      runSearch(this.props.onSearch, {searchTerm, navigation})
        .then(this.onSearchComplete, this.onSearchError);
      this.setState({searchTerm, searchInProgress: true});
    } else {
      this.setState({searchTerm, navigation, searchInProgress: false});
    }
  };

  onSearchComplete = (navigation: Map<string, QueryNavigation>) => {
    if (!this.mounted || !this.state.searchInProgress) {
      return;
    }
    this.setState({navigation, searchInProgress: false});
  };

  onSearchError = (err: Error) => {
    console.error('Error while search:', err);
    this.setState({searchInProgress: false});
  };

  render() {
    let {children} = this.props;
    let {searchTerm, searchInProgress, navigation} = this.state;
    if (children) {
      children = React.cloneElement(children, {navigation});
    }
    let loadingIndicator = null;
    if (searchInProgress) {
      loadingIndicator = (
        <Element
          position="absolute"
          top={0}
          width="100%"
          padding={5}
          background="#fff"
          borderBottom={{style: 'solid', width: 1, color: '#ccc'}}
          opacity={0.9}
          zIndex={1}>
          <LoadingIndicator />
        </Element>
      );
    }
    return (
      <VBox>
        <VBox padding={10}>
          <ReactUI.Input
            placeholder="Search…"
            value={searchTerm === null ? '' : searchTerm}
            onChange={this.onSearchTerm}
            />
        </VBox>
        <VBox>
          {loadingIndicator}
          {children}
        </VBox>
      </VBox>
    );
  }
}
