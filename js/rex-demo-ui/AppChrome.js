// @flow

import * as React from "react";
import classNames from "classnames";
import * as mui from "@material-ui/core";
import { makeStyles, ThemeProvider } from "@material-ui/styles";
import MenuIcon from "@material-ui/icons/Menu";
import ClearIcon from "@material-ui/icons/Clear";
import { DARK_THEME, DEFAULT_THEME } from "rex-ui/rapid/themes";
import * as Screen from "./Screen.js";
import * as Router from "rex-ui/Router";
import { isEmptyObject } from "rex-ui/rapid/helpers";

let drawerWidth = 240;
let appBarHeight = 64;

export type MenuItem = {|
  title?: ?string,
  route: Router.Route<Screen.Screen>,
|};

export type Menu = MenuItem[];

const useStyles = makeStyles(theme => {
  if (isEmptyObject(theme)) {
    theme = DEFAULT_THEME;
  }

  return {
    appBar: {
      height: appBarHeight,
      backgroundColor: "#FFFFFF",
    },
    appBarShift: {
      width: `calc(100% - ${drawerWidth}px)`,
      marginLeft: drawerWidth,
    },
    content: {
      display: "flex",
      flexDirection: "column",
      flexWrap: "nowrap",
      flexGrow: 1,
      backgroundColor: theme.palette.background.default,
      minWidth: 0, // So the Typography noWrap works
      height: "100vh",
      maxHeight: "100vh",
      paddingTop: appBarHeight,
      marginLeft: 0,
    },
    contentShift: {
      marginLeft: `${drawerWidth}px !important`,
    },
    menuButton: {
      marginLeft: 0,
      marginRight: 12,
    },
  };
});

type AppChromeProps = {|
  router: Router.Router<Screen.Screen>,
  menu: Menu,
  title: string,
  children: React.Node,
|};

export default function AppChrome({
  title,
  children,
  router,
  menu,
}: AppChromeProps) {
  let [drawerOpen, setDrawerOpen] = React.useState(false);
  let [appTheme, setAppTheme] = React.useState<"default" | "custom">("default");
  let toggleDrawerOpen = () => {
    setDrawerOpen(open => !open);
  };
  let classes = useStyles();

  let theme = React.useMemo(() => {
    switch (appTheme) {
      case "custom": {
        return DARK_THEME;
      }
      case "default":
      default: {
        return DEFAULT_THEME;
      }
    }
  }, [appTheme]);

  return (
    <ThemeProvider theme={theme}>
      <mui.AppBar
        position="fixed"
        className={classNames(classes.appBar, {
          [classes.appBarShift]: drawerOpen,
        })}
      >
        <mui.Toolbar>
          {!drawerOpen && (
            <mui.IconButton
              aria-label="Open drawer"
              onClick={toggleDrawerOpen}
              className={classNames(classes.menuButton)}
            >
              <MenuIcon color="primary" />
            </mui.IconButton>
          )}
          <mui.Typography variant="h6" color="primary" noWrap>
            {title}
          </mui.Typography>
        </mui.Toolbar>
      </mui.AppBar>
      <AppDrawer
        open={drawerOpen}
        onClose={toggleDrawerOpen}
        menu={menu}
        router={router}
        theme={appTheme}
        onTheme={setAppTheme}
      />
      <main
        className={classNames(classes.content, {
          [classes.contentShift]: drawerOpen,
        })}
      >
        {children}
      </main>
    </ThemeProvider>
  );
}

let useAppDrawerStyles = makeStyles(theme => ({
  root: {
    width: drawerWidth,
    flexShrink: 0,
  },
  paper: {
    width: drawerWidth,
  },
  wrapper: {
    flex: "1 1 auto",
  },
  toolbar: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-end",
    padding: theme.spacing.unit,
    ...theme.mixins.toolbar,
  },
}));

type AppDrawerProps = {|
  open: boolean,
  onClose: () => void,
  menu: Menu,
  theme: any,
  onTheme: any => void,
  router: Router.Router<Screen.Screen>,
|};

function AppDrawer({
  router,
  open,
  onClose,
  menu,
  theme,
  onTheme,
}: AppDrawerProps) {
  let classes = useAppDrawerStyles();
  return (
    <mui.Drawer
      variant="persistent"
      anchor="left"
      open={open}
      transitionDuration={0}
      className={classes.root}
      classes={{ paper: classes.paper }}
    >
      <div className={classes.wrapper}>
        <div className={classes.toolbar}>
          <mui.IconButton
            color="inherit"
            aria-label="Close drawer"
            onClick={onClose}
          >
            <ClearIcon color="primary" />
          </mui.IconButton>
        </div>
        <AppMenu router={router} menu={menu} />
      </div>
      <AppTheme onChange={onTheme} theme={theme} />
    </mui.Drawer>
  );
}

type AppMenuProps = {|
  router: Router.Router<Screen.Screen>,
  menu: Menu,
|};

function AppMenu({ router, menu }: AppMenuProps) {
  let items = menu.map((item, index) => {
    let key = item.route.path;
    let title =
      item.title != null
        ? item.title
        : item.route.screen != null
        ? item.route.screen.title
        : "Page";
    let selected = router.isActive(item.route);
    let onClick = () => router.replace(item.route);
    return (
      <mui.ListItem
        key={key}
        button={true}
        selected={selected}
        onClick={onClick}
      >
        <mui.ListItemText primary={title} />
      </mui.ListItem>
    );
  });
  return <mui.List>{items}</mui.List>;
}

function AppTheme({
  onChange,
  theme,
}: {
  onChange: (newTheme: "default" | "custom") => void,
  theme: "default" | "custom",
}) {
  return (
    <mui.List>
      <mui.ListSubheader>Themes</mui.ListSubheader>
      <mui.ListItem
        button={true}
        selected={theme === "default"}
        onClick={() => onChange("default")}
      >
        <mui.ListItemText primary={"Default"} />
      </mui.ListItem>

      <mui.ListItem
        button={true}
        selected={theme === "custom"}
        onClick={() => onChange("custom")}
      >
        <mui.ListItemText primary={"Custom"} />
      </mui.ListItem>
    </mui.List>
  );
}
