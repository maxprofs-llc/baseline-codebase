/**
 * @copyright 2014 Quri, Loïc CHOLLIER
 * @copyright 2016-present Prometheus Research, LLC
 * @flow
 */

import type Moment from "moment";
import * as React from "react";
import { DayView, type RenderDay } from "./DayView";
import { MonthView, type RenderMonth } from "./MonthView";
import { YearView } from "./YearView";
import * as Common from "./Common";

export type DatePickerMode = "days" | "months" | "years";

type DatePickerProps = {|
  mode: DatePickerMode,
  onMode: DatePickerMode => void,
  viewDate: Moment,
  onViewDate: Moment => void,
  selectedDate: ?Moment,
  onSelectedDate: (?Moment) => void,
  showToday?: boolean,
  renderDay?: RenderDay,
  renderMonth?: RenderMonth,
  onFocus?: UIEvent => void,
  onBlur?: UIEvent => void
|};

export let DatePicker = (props: DatePickerProps) => {
  let {
    mode,
    onMode,
    selectedDate,
    onSelectedDate,
    viewDate,
    onViewDate,
    renderDay,
    renderMonth,
    showToday,
    onFocus,
    onBlur
  } = props;

  let showMonths = () => {
    onMode("months");
  };

  let showYears = () => {
    onMode("years");
  };

  let showDays = () => {
    onMode("days");
  };

  return (
    <div tabIndex="0" onFocus={onFocus} onBlur={onBlur}>
      {mode === "days" && (
        <DayView
          selectedDate={selectedDate}
          onSelectedDate={onSelectedDate}
          viewDate={viewDate}
          onViewDate={onViewDate}
          renderDay={renderDay}
          showToday={showToday}
          showMonths={showMonths}
        />
      )}
      {mode === "months" && (
        <MonthView
          selectedDate={selectedDate}
          viewDate={viewDate}
          onViewDate={onViewDate}
          renderMonth={renderMonth}
          showYears={showYears}
          onClose={showDays}
        />
      )}
      {mode === "years" && (
        <YearView
          selectedDate={selectedDate}
          viewDate={viewDate}
          onViewDate={onViewDate}
          onClose={showMonths}
        />
      )}
    </div>
  );
};