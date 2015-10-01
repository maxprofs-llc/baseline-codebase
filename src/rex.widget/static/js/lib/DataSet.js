/**
 * @copyright 2015, Prometheus Research, LLC
 */
'use strict';

/**
 * Object which represents dataset along with data lifecycle oriented metadata.
 */
class DataSet {

  constructor(data, loading, error) {
    this.data = data || null;
    this.loading = loading || false;
    this.error = error || null;
  }

  get length() {
    return Array.isArray(this.data) ?
      this.data.length :
      0;
  }

  get loaded() {
    return !this.loading && this.data != null;
  }

  findByID(id) {
    if (id == null || this.data == null) {
      return null;
    }
    for (let i = 0, len = this.data.length; i < len; i++) {
      let item = this.data[i];
      if (item.id == id) { // eslint-disable-line eqeqeq
        return item;
      }
    }
    return null;
  }

}

// Constant value for empty dataset
DataSet.EMPTY_DATASET = new DataSet(null, false, null);

// Constant value for empty dataset which is loading
DataSet.EMPTY_UPDATING_DATASET = new DataSet(null, true, null);

module.exports = DataSet;
