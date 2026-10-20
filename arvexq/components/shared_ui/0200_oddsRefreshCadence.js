function oddsRefreshCadence(r){var start=mins(r&&r.startTime),now=nowMins();if(start>=9999)return 60000;var remain=start-now;if(remain<=0)return 0;return remain<=30?30000:60000}
