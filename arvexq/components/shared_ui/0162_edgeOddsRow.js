function edgeOddsRow(z){
  z=z||{};return {
    horseNumber:n(z.horseNumber!=null?z.horseNumber:z.horse_no,0),
    winOdds:z.winOdds!=null?z.winOdds:z.win_odds,
    popularity:z.popularity,
    bodyWeight:z.bodyWeight!=null?z.bodyWeight:z.body_weight,
    bodyWeightChange:z.bodyWeightChange!=null?z.bodyWeightChange:z.body_weight_change,
    status:z.status!=null?z.status:z.horse_status,
    scratched:z.scratched===true||z.withdrawn===true||/欠場|出走取消|取消|競走除外|除外/.test(String(z.status!=null?z.status:z.horse_status||'')),
    updatedAt:z.updatedAt!=null?z.updatedAt:z.updated_at
  }
}
