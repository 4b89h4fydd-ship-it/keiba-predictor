function horseBodyWeightText(h){var w=currentBodyWeight(h);if(!w)return'';var ch=currentBodyWeightChange(h),s=w+'kg';if(ch!=null)s+=ch>0?' (+'+ch+')':' ('+ch+')';return s}
