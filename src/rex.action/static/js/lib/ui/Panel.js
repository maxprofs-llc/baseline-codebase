/**
 * @copyright 2015, Prometheus Research, LLC
 */

import {VBox}     from '@prometheusresearch/react-box';
import * as Theme from './Theme';

export default VBox.style({
  background: Theme.color.primary.background,
  boxShadow: Theme.shadow.light(),
  padding: Theme.margin.medium,
  noPadding: {
    padding: 0
  }
});
