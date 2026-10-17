/* 112/126: Production view model has no approved predictive engine. */
(function(root){
  'use strict';
  function build(race){
    return {rows:((race&&race.horses)||[]).filter(function(h){return h&&Number(h.horseNumber)>0}).map(function(h){
      return {horse:h,predMark:'',predRank:999,winProbability:null,p1Probability:null,p2Probability:null,p3Probability:null,overallGrade:'',coverage:0};
    }),scenarios:[],plans:{},plan:null,suit:{},occ:[],pressure:0,arrangement:[],profile:{},coverage:0};
  }
  root.ARVEXQProductionPrediction=Object.freeze({build:build});
})(typeof window!=='undefined'?window:globalThis);
