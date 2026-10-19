function visiblePaceStages(plan){var wanted={start:1,turn3:1,turn4:1,straight:1};return ((plan&&plan.stages)||[]).filter(function(s){return !!wanted[String(s&&s.key||'')]})}
