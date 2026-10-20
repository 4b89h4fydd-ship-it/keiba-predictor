function isScratchHorse(h){var s=String(h&&h.status||'');return !!(h&&(h.scratched===true||h.withdrawn===true||/欠場|出走取消|取消|競走除外|除外/.test(s)))}
