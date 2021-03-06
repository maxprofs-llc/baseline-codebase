import React from 'react';
import {Action} from 'rex-action';
import {VBox} from '@prometheusresearch/react-box';
import {DataSet} from 'rex-widget/data';
import {DataTableBase} from 'rex-widget/datatable';
import {SearchInput} from 'rex-widget/form';

export default class PickTable extends React.Component {

  render() {
    let {title, tables, context} = this.props;
    let {filter = ''} = this.props.actionState;
    let data = DataSet.fromData(tables.filter(
      (table) => table.title.indexOf(filter || '') != -1
    ));
    let search = (
      <SearchInput
        debounce={500}
        onChange={this.onChangeFilter}
        value={filter}
      />
    );
    return (
      <Action 
        title={title}
        extraToolbar={search}
        noContentWrapper>
        <DataTableBase
          flex={1}
          columns={[
            {valueKey: ['title'], label: 'Table'},
          ]}
          data={data}
          selected={context.table}
          onSelect={this.onSelect}
          />
      </Action>
    );
  }

  onSelect = (id) => {
    this.props.onContext({
      table: id
    });
  }

  onChangeFilter = (value) => {
    this.props.setActionState({filter: value});
  }

  static renderTitle(props, context) {
    let {title} = props;
    return (
      <VBox>
        {title}
        {context.table && <small>{context.table}</small>}
      </VBox>
    );
  }
}
