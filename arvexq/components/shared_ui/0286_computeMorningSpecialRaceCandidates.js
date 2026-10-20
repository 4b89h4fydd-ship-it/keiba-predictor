function computeMorningSpecialRaceCandidates(){
 if(!window.ARVEXQSpecialSelection)throw Error('special selection module missing');
 return window.ARVEXQSpecialSelection.select(state.races||[]);
}
