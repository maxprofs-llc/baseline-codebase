/**
 * @copyright 2015, Prometheus Research, LLC
 */
'use strict';

var React                   = require('react');
window.React                = React;
var {Column, Table}         = require('fixed-data-table/dist/fixed-data-table');
var {Box, LayoutAwareMixin} = require('./layout');


var DataTable = React.createClass({
  mixins: [LayoutAwareMixin],

  render() {
    var {data, columns, selectable, ...props} = this.props;
    var {width, height} = this.state;
    columns = columns.map(column =>
      <Column
        cellDataGetter={this._cellDataGetter}
        key={column.key}
        resizable={column.resizable}
        dataKey={column.key}
        label={column.name}
        width={column.width || 100}
        flexGrow={1}
        />
    );
    if (width === null || height === null) {
      return <Box size={1} />;
    } else {
      return (
        <Box size={1}>
          <Table
            {...props}
            onRowClick={selectable && this._onRowClick}
            height={height}
            width={width}
            rowGetter={this._rowGetter}
            rowClassNameGetter={this._rowClassNameGetter}
            onScrollEnd={this._checkNeedPagination}
            rowsCount={data.data.length}>
            {columns}
          </Table>
        </Box>
      );
    }
  },

  getDefaultProps() {
    return {
      rowHeight: 35,
      headerHeight: 35
    };
  },

  getInitialState() {
    return {
      width: null,
      height: null
    };
  },

  componentDidMount() {
    this._recomputeGeometry();
    this._checkNeedPagination();
  },

  onLayoutChange() {
    this._recomputeGeometry();
  },

  _checkNeedPagination() {
    var {updating, hasMore, data} = this.props.data;
    if (
      Array.isArray(data)
      && data.length - this._lastRowIndex < 10
      && !updating
      && hasMore
    ) {
      var {top, skip} = this.props.dataPagination;
      this.props.onDataPagination({top, skip: skip + top});
    }
  },

  _recomputeGeometry() {
    var {height, width} = this.getDOMNode().getBoundingClientRect();
    this.setState({height, width});
  },

  _cellDataGetter(key, row) {
    return getByKeyPath(row, key);
  },

  _rowGetter(rowIndex) {
    if (this._lastRowIndex === undefined || rowIndex > this._lastRowIndex) {
      this._lastRowIndex = rowIndex;
    }
    return this.props.data.data[rowIndex];
  },

  _rowClassNameGetter(rowIndex) {
    var {selectable, selected} = this.props;
    if (selectable && this._rowGetter(rowIndex).id == selected) {
      return 'DataTable__row--selected';
    }
  },

  _onRowClick(e, rowIndex, row) {
    var {selectable, selected, onSelected, onSelect} = this.props;
    if (selectable && row.id != selected) {
      onSelected(row.id);
    }
    if (onSelect) {
      onSelect();
    }
  }
});

function getByKeyPath(row, keyPath) {
  if (!Array.isArray(keyPath)) {
    return row[keyPath];
  }
  switch (keyPath.length) {
    case 0:
      return row;
    case 1:
      return row[keyPath[0]];
    case 2:
      return row[keyPath[0]][keyPath[1]];
    case 3:
      return row[keyPath[0]][keyPath[1]][keyPath[2]];
    default:
      for (var i = 0, len = row.length; i < len; i++) {
        if (row == null) {
          return row;
        }
        row = row[keyPath[i]];
      }
      return row;
  }
}

module.exports = DataTable;
