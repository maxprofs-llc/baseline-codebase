/**
 * @copyright 2016, Prometheus Research, LLC
 */

import React from "react";

import { Action, TitleBase as Title } from "rex-action";
import * as rexui from "rex-ui";
import { withFetch } from "rex-widget/data";
import * as form from "rex-widget/conf-form";
import martFromContext from "./martFromContext";

export default withFetch(
  class DictionaryViewTable extends React.Component {
    static defaultProps = {
      icon: "file"
    };

    render() {
      let { fields, title, context, onClose, fetched } = this.props;
      return (
        <Action title={title} onClose={onClose}>
          {!fetched.entity.updating ? (
            <form.ConfEntityForm
              key={fetched.entity.data.id}
              disableValidation
              readOnly
              entity={context.mart_table}
              value={fetched.entity.data}
              fields={fields}
            />
          ) : (
            <rexui.PreloaderScreen />
          )}
        </Action>
      );
    }

    static renderTitle({ title }, { mart_table }) {
      return <Title title={title} subtitle={mart_table} />;
    }
  },
  function({ data, context, contextTypes }) {
    data = data.params({
      "*": context.mart_table,
      mart: martFromContext(context)
    });
    return {
      entity: data.getSingleEntity()
    };
  }
);
