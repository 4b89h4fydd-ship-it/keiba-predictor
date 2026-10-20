function latestAuthorizedMarkRevision(r){
  var official=latestOfficialMarkRevision(r),model=latestUserApprovedModelMarkRevision(r);
  if(!official)return model;
  if(!model)return official;
  return Date.parse(String(model.revisedAt||''))>Date.parse(String(official.revisedAt||''))?model:official
}
