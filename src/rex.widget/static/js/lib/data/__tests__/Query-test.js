/**
 * @copyright 2015, Prometheus Research, LLC
 */

import Sinon from 'sinon';
import {Query as BaseQuery} from '../Query';
import PromiseMock from './PromiseMock';


describe('Query', function() {

  beforeEach(function() {
    this.Query = class extends BaseQuery {
      static fetch(path, params) {
        return new PromiseMock();
      }
    }
    Sinon.spy(this.Query, 'fetch');
  });

  it('fetches collection', function() {
    let port = new this.Query('path', {a: 1});
    let promise = port.produce();
    assert(this.Query.fetch.callCount === 1);
    assert(this.Query.fetch.firstCall.args[0] === 'path');
    assert.deepEqual(this.Query.fetch.firstCall.args[1], {a: 1});
  });

  it('allows to set parameters via .params()', function() {
    let port = new this.Query('path');
    let promise = port.params({a: 1}).produce();
    assert(this.Query.fetch.callCount === 1);
    assert(this.Query.fetch.firstCall.args[0] === 'path');
    assert.deepEqual(this.Query.fetch.firstCall.args[1], {a: 1});
  });

});

