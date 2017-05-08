/**
 * @copyright 2017, Prometheus Research, LLC
 */

import React from 'react';

import HtsqlDataGrid from './HtsqlDataGrid';


export default class PreviewPanel extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      changeId: 0,
    };
  }

  componentWillReceiveProps() {
    this.setState({changeId: this.state.changeId + 1});
  }

  dataRetriever(limit, offset) {
    if (this.props.previewRecordLimit) {
      if ((limit == null) || (limit > this.props.previewRecordLimit)) {
        limit = this.props.previewRecordLimit;
      }
    }
    return this.props.retriever('x-htsql/raw', limit, offset);
  }

  activeColumnIndexes() {
    return this.props.columnState.map((col, idx) => {
      return col ? idx : null;
    }).filter((col) => col != null);
  }

  _realToShown(sortState) {
    let activeIndexes = this.activeColumnIndexes();
    return sortState.map((sort) => {
      let shownIndex = activeIndexes.length === 0 ? sort.id : activeIndexes.indexOf(sort.id);
      return {
        ...sort,
        id: shownIndex,
      };
    });
  }

  onHeaderClick(columnIndex, additive) {
    let realColumnIndex = this.activeColumnIndexes()[columnIndex];
    if (realColumnIndex == undefined) {
      realColumnIndex = columnIndex;
    }

    let found = false;
    let newState = this.props.sortState.filter((sort) => {
      if (sort.id === realColumnIndex) {
        found = true;
      }
      return additive || sort.id === realColumnIndex;
    }).map((sort) => {
      if (sort.id === realColumnIndex) {
        return {
          ...sort,
          dir: sort.dir === 'asc' ? 'desc' : 'asc',
        }
      } else {
        return sort;
      }
    });
    if (!found) {
      newState.push({
        id: realColumnIndex,
        dir: 'asc',
      });
    }

    this.props.onSortChange(newState);
  }

  render() {
    return (
      <HtsqlDataGrid
        key={this.state.changeId}
        rowGetter={this.dataRetriever.bind(this)}
        sortState={this._realToShown(this.props.sortState)}
        onHeaderClick={this.onHeaderClick.bind(this)}
        />
    );
  }
}

