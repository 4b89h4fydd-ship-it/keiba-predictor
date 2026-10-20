function venueRows(){return state.races.filter(function(x){return x.circuit===state.circuit&&x.track===state.track}).sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)})}
