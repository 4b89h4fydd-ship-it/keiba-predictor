function courseProfile(r){
  r=r||{};
  return COURSE[r.track]||{lap:1400,straight:300,dir:-1,shape:"wide",turn:"右",firstTurn:300}
}
