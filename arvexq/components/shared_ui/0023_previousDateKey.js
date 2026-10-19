function previousDateKey(iso){var p=String(iso||today()).split('-'),y=n(p[0]),m=n(p[1]),d=n(p[2]);if(!y||!m||!d)return'';return new Date(Date.UTC(y,m-1,d)-86400000).toISOString().slice(0,10)}
