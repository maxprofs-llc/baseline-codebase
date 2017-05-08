/**
 * @copyright 2017, Prometheus Research, LLC
 */

import React from 'react';

import {LoadingIndicator} from 'rex-query/src/ui';

import DataGrid from './DataGrid';


export default class HtsqlDataGrid extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      loading: true,
      columns: [],
      data: [],
    };
  }

  onHeaderClick(columnIndex, event) {
    if (this.props.onHeaderClick) {
      this.props.onHeaderClick(columnIndex, event.shiftKey);
    }
  }

  componentWillMount() {
    this.props.rowGetter()
      .then((response) => {
        return response.json();
      })
      .then((data) => {
        let columns = data.meta.domain.item.domain.fields.map((field, idx) => {
          let sort = this.props.sortState.filter((sort) => sort.id === idx);
          return {
            title: field.header,
            type: field.domain.type,
            onClick: this.onHeaderClick.bind(this, idx),
            sort: sort.length > 0 ? sort[0].dir : null,
          };
        });

        this.setState({
          columns,
          data: data.data,
          loading: false,
        });
      });
  }

  render() {
    if (this.state.loading) {
      return (
        <div
          style={{
            flexGrow: 1,
            display: 'flex',
            alignItems: 'center',
          }}>
          <LoadingIndicator />
        </div>
      );
    } else {
      return (
        <DataGrid
          columns={this.state.columns}
          rows={this.state.data}
          />
      );
    }
  }
}

