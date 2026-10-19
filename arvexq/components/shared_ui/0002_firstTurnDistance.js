function firstTurnDistance(r){r=r||{};var direct=n(r.firstTurnDistance||r.startToFirstTurn||r.firstCornerDistance||r.firstCornerMeters,0);return direct>0?direct:n(courseProfile(r).firstTurn,300)}
