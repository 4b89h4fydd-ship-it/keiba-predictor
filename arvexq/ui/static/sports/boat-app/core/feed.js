// SMALL: one data source. No fallback websites, fabricated racecards or dynamic scraping.
import {parseDay} from "./contract.js";
export async function loadDay(day){
  const controller=new AbortController();
  // The producer will publish one date-scoped, reviewed snapshot, not many routes.
  const url="/sports/boat-data/"+encodeURIComponent(day)+".json";
  try{
    const response=await fetch(url,{cache:"no-store",signal:controller.signal});
    if(!response.ok)throw Error("HTTP "+response.status);
    return parseDay(await response.json(),day);
  }finally{controller.abort()}
}
