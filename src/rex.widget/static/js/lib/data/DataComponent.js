/**
 * @copyright 2015, Prometheus Research, LLC
 */

import autobind         from 'autobind-decorator';
import invariant        from 'invariant';
import ReactUpdates     from 'react/lib/ReactUpdates';
import DataFetchTracker from './DataFetchTracker';
import DataSet          from './DataSet';

const EMPTY_DATASET = new DataSet(null, null, false);
const EMPTY_UPDATING_DATASET = new DataSet(null, null, true);

export default function DataComponent(Component) {

  return class extends Component {

    constructor(props) {
      super(props);
      invariant(
        typeof this.fetch === 'function',
        'DataComponent should define fetch() method'
      );
      this.__dataSpec = null;
      this.__dataFetch = null;
      this.dataSet = {};
      this.data = {};
    }

    componentWillMount() {
      this.__dataSpec = this.fetch();
      this.__dataFetch = {};
      for (let key in this.__dataSpec) {
        if (this.__dataSpec.hasOwnProperty(key)) {
          this.dataSet[key] = EMPTY_UPDATING_DATASET;
          this.data[key] = null;
        }
      }
      if (super.componentWillMount) {
        super.componentWillMount();
      }
    }

    componentDidMount() {
      for (let key in this.__dataSpec) {
        if (this.__dataSpec.hasOwnProperty(key)) {
          let task = this.__dataSpec[key];
          this._fetch(key, task);
        }
      }

      if (super.componentDidMount) {
        super.componentDidMount();
      }
    }

    componentWillUpdate(nextProps, nextState) {
      if (super.componentWillUpdate) {
        super.componentWillUpdate(nextState, nextProps);
      }
      let prevProps = this.props;
      let prevState = this.state;
      this.props = nextProps;
      this.state = nextState;
      let nextDataSpec = this.fetch();
      this.props = prevProps;
      this.state = prevState;

      for (let key in nextDataSpec) {
        if (nextDataSpec.hasOwnProperty(key)) {
          let task = nextDataSpec[key];
          let prevTask = this.__dataSpec[key];
          if (prevTask && prevTask.equals(task)) {
            continue;
          }
          this._cancel(key);
          this._fetch(key, task);
        }
      }

      for (let key in this.__dataSpec) {
        if (this.__dataSpec.hasOwnProperty(key) && !nextDataSpec.hasOwnProperty(key)) {
          this._cancel(key);
          this._purge(key);
        }
      }

      this.__dataSpec = nextDataSpec;
    }

    componentWillUnmount() {
      if (super.componentWillUnmount) {
        super.componentWillUnmount();
      }
      this._cancelAll();
      this.__dataSpec = null;
      this.__dataFetch = null;
      this.dataSet = {};
      this.data = {};
    }

    _fetch(key, dataSpec) {
      let dataSet = this.dataSet[key] || EMPTY_DATASET;
      this.dataSet[key] = new DataSet(dataSet.data, dataSet.error, true);
      this.data[key] = dataSet.data;
      this.__dataFetch[key] = new DataFetchTracker(
        key,
        dataSpec.produce(),
        this._onDataFetchComplete,
        this._onDataFetchError,
      );
    }

    @autobind
    _onDataFetchComplete(key, data) {
      ReactUpdates.batchedUpdates(() => {
        this.__dataFetch[key] = null;
        if (typeof this.onData === 'function') {
          data = this.onData(key, data, this.data[key]);
        }
        this.dataSet[key] = new DataSet(data, null, false);
        this.data[key] = data;
        this.forceUpdate();
      });
    }

    @autobind
    _onDataFetchError(key, error) {
      this.__dataFetch[key] = null;
      this.dataSet[key] = new DataSet(this.data[key], error, false);
      this.data[key] = null;
      this.forceUpdate();
    }

    _purge(key) {
      delete this.data[key];
      delete this.dataSet[key];
      delete this.__dataFetch[key];
    }

    _cancel(key) {
      if (this.__dataFetch[key]) {
        this.__dataFetch[key].cancel();
      }
    }

    _cancelAll() {
      for (let key in this.__dataFetch) {
        if (this.__dataFetch.hasOwnProperty(key) && this.__dataFetch[key]) {
          this.__dataFetch[key].cancel();
        }
      }
    }

  };
}

