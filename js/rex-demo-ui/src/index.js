// @flow

import invariant from "invariant";
import * as React from "react";
import * as ReactDOM from "react-dom";
import * as RexGraphQL from "rex-graphql";
import { Pick, ComponentLoading } from "rex-ui/rapid";
import { Show } from "rex-ui/rapid/show";
import Button from "@material-ui/core/Button";
import CssBaseline from "@material-ui/core/CssBaseline";

const endpoint = RexGraphQL.configure("/_api/graphql");

function App() {
  const [componentToShow, setComponentToShow] = React.useState<"pick" | "show">(
    "pick"
  );
  const [selectedRow, setSelectedRow] = React.useState<?any>(null);

  const onRowClick = (row: any) => {
    setComponentToShow("show");
    setSelectedRow(row);
  };

  const resetState = () => {
    setComponentToShow("pick");
    setSelectedRow(null);
  };

  const defaultView = (
    <Pick
      endpoint={endpoint}
      fetch={"user.paginated"}
      isRowClickable={true}
      onRowClick={onRowClick}
      fields={[
        "id",
        {
          key: "remote_user",
          require: ["remote_user", "expires"]
        }
      ]}
      title={"Example data"}
      description={"Description text goes here"}
    />
  );

  switch (componentToShow) {
    case "show": {
      if (selectedRow != null) {
        return (
          <div>
            <div>
              <Button onClick={resetState}>Reset</Button>
            </div>
            <Show
              endpoint={endpoint}
              fetch={"user.get"}
              args={{ id: selectedRow.id }}
            />
          </div>
        );
      }

      return defaultView;
    }

    default: {
      return defaultView;
    }
  }
}

let root = document.getElementById("root");
invariant(root != null, "DOM is not avaialble: missing #root");

ReactDOM.render(
  <React.Suspense fallback={ComponentLoading}>
    <CssBaseline />
    <App />
  </React.Suspense>,
  root
);
