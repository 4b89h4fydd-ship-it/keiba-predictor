function actualCornerLabel(i,count){if(count===1)return"4角";if(count===2)return i===0?"3角":"4角";if(count===3)return["2角","3角","4角"][i];if(count===4)return["1角","2角","3角","4角"][i];return(i+1)+"角"}
